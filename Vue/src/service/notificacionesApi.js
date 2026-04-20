const METODOS_MUTACION = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CLAVES_NO_VALIDACION = new Set(['status', 'message', 'mensaje', 'detail', 'error', 'data', 'errors']);
const REGLAS_LISTA_BLANCA_NOTIFICACIONES = [
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/cabina-arquitectura\//,
    },
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/categorias(?:\/|$)/,
    },
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/conceptos(?:\/|$)/,
    },
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/detalles-parametrizados(?:\/|$)/,
    },
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/fondos-fijos(?:\/|$)/,
    },
    {
        metodos: new Set(['POST', 'PUT', 'PATCH', 'DELETE']),
        patron: /^\/sucursales-fondos-fijos(?:\/|$)/,
    },
    {
        metodos: new Set(['POST']),
        patron: /^\/reportes-diarios\/saldo-inicial-categoria\/manual\/?$/,
    },
    {
        metodos: new Set(['POST']),
        patron: /^\/reportes-diarios\/cerrar-actual\/?$/,
    },
    {
        metodos: new Set(['DELETE']),
        patron: /^\/movimientos-diarios\/\d+\/?$/,
    },
    {
        metodos: new Set(['PATCH']),
        patron: /^\/usuarios\/perfil-propio\/?$/,
    },
];

let instanciaToast = null;

function textoLimpio(valor) {
    if (typeof valor === 'string') {
        return valor.trim();
    }

    if (typeof valor === 'number' || typeof valor === 'boolean') {
        return String(valor);
    }

    return '';
}

function formatearCampo(campo) {
    const clave = String(campo || '').trim();
    if (!clave || clave === 'non_field_errors') {
        return '';
    }

    return clave.replace(/_/g, ' ');
}

function deduplicarMensajes(mensajes) {
    return [...new Set((mensajes || []).filter(Boolean))];
}

function recolectarMensajes(valor, campo = '') {
    if (valor === null || valor === undefined) {
        return [];
    }

    if (Array.isArray(valor)) {
        return valor.flatMap((item) => recolectarMensajes(item, campo));
    }

    if (typeof valor === 'object') {
        return Object.entries(valor).flatMap(([clave, contenido]) => recolectarMensajes(contenido, formatearCampo(clave)));
    }

    const texto = textoLimpio(valor);
    if (!texto) {
        return [];
    }

    return campo ? [`${campo}: ${texto}`] : [texto];
}

function extraerMensajeExito(payload) {
    return (
        textoLimpio(payload?.message)
        || textoLimpio(payload?.mensaje)
        || textoLimpio(payload?.detail)
    );
}

function extraerMensajesValidacion(payload) {
    const mensajes = [];

    mensajes.push(...recolectarMensajes(payload?.data));
    mensajes.push(...recolectarMensajes(payload?.errors));

    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
        const erroresDirectos = Object.fromEntries(
            Object.entries(payload).filter(([clave]) => !CLAVES_NO_VALIDACION.has(clave))
        );
        mensajes.push(...recolectarMensajes(erroresDirectos));
    }

    return deduplicarMensajes(mensajes);
}

function extraerMensajeError(error) {
    const payload = error?.response?.data;
    const codigo = Number(error?.response?.status || 0);
    const codigoError = String(error?.code || '').toUpperCase();
    const mensajeMotor = String(error?.message || '').toLowerCase();

    if (codigoError === 'ECONNABORTED' || mensajeMotor.includes('timeout')) {
        return 'La solicitud superó el tiempo de espera. Verifique su conexión e inténtelo nuevamente.';
    }

    const mensajePrincipal = (
        textoLimpio(payload?.message)
        || textoLimpio(payload?.mensaje)
        || textoLimpio(payload?.detail)
        || textoLimpio(payload?.error)
    );

    const mensajesValidacion = extraerMensajesValidacion(payload);
    if (mensajesValidacion.length > 0) {
        if (mensajePrincipal) {
            return `${mensajePrincipal} ${mensajesValidacion.join(' | ')}`;
        }
        return mensajesValidacion.join(' | ');
    }

    if (mensajePrincipal) {
        return mensajePrincipal;
    }

    if (!error?.response) {
        return 'No se recibió respuesta del servidor. Verifique su conexión a la red.';
    }

    if (codigo >= 500) {
        return 'Ocurrió un error interno en el servidor. Inténtelo nuevamente o contacte soporte.';
    }

    if (codigo > 0) {
        return `La solicitud no pudo completarse (HTTP ${codigo}).`;
    }

    return 'La solicitud no pudo completarse. Contacte al equipo de soporte si el problema persiste.';
}

function obtenerOpcionesToast(config) {
    const opciones = config?.notificacionToast || {};

    return {
        mostrarExito: opciones.exito !== false,
        mostrarError: opciones.error !== false,
        forzarMostrar: opciones.forzar === true,
        resumenExito: textoLimpio(opciones.resumenExito) || 'Operación completada',
        resumenError: textoLimpio(opciones.resumenError) || 'Error en la operación',
        vidaExito: Number(opciones.vidaExito) > 0 ? Number(opciones.vidaExito) : 4500,
        vidaError: Number(opciones.vidaError) > 0 ? Number(opciones.vidaError) : 7000,
    };
}

function obtenerMetodoSolicitud(config) {
    return String(config?.method || '').trim().toUpperCase();
}

function normalizarRutaSolicitud(config) {
    const urlCruda = String(config?.url || '').trim();
    if (!urlCruda) {
        return '';
    }

    let ruta = '';

    try {
        ruta = new URL(urlCruda, 'http://binsurmx.local').pathname;
    } catch {
        ruta = urlCruda;
    }

    ruta = String(ruta || '').split('?')[0].split('#')[0].trim();
    if (!ruta) {
        return '';
    }

    if (!ruta.startsWith('/')) {
        ruta = `/${ruta}`;
    }

    if (ruta.startsWith('/apex/api/')) {
        return `/${ruta.slice('/apex/api/'.length)}`;
    }

    if (ruta.startsWith('/api/')) {
        return `/${ruta.slice('/api/'.length)}`;
    }

    return ruta;
}

function esMetodoMutacion(config) {
    const metodo = obtenerMetodoSolicitud(config);
    return METODOS_MUTACION.has(metodo);
}

function estaRutaEnListaBlanca(config) {
    const metodo = obtenerMetodoSolicitud(config);
    const ruta = normalizarRutaSolicitud(config);

    if (!metodo || !ruta) {
        return false;
    }

    return REGLAS_LISTA_BLANCA_NOTIFICACIONES.some((regla) => {
        return regla.metodos.has(metodo) && regla.patron.test(ruta);
    });
}

function esOperacionNotificable(config, opciones) {
    if (!esMetodoMutacion(config)) {
        return false;
    }

    if (opciones?.forzarMostrar) {
        return true;
    }

    return estaRutaEnListaBlanca(config);
}

function agregarToast({ severidad, resumen, detalle, vida }) {
    if (!instanciaToast) {
        return;
    }

    const detalleLimpio = textoLimpio(detalle);
    if (!detalleLimpio) {
        return;
    }

    instanciaToast.add({
        severity: severidad,
        summary: resumen,
        detail: detalleLimpio,
        life: vida,
    });
}

export function registrarInstanciaToastApi(instancia) {
    instanciaToast = instancia;
}

export function procesarRespuestaExitosaConToast(response) {
    const opciones = obtenerOpcionesToast(response?.config);
    if (!esOperacionNotificable(response?.config, opciones)) {
        return;
    }

    if (!opciones.mostrarExito) {
        return;
    }

    const mensaje = extraerMensajeExito(response?.data);
    if (!mensaje) {
        return;
    }

    agregarToast({
        severidad: 'success',
        resumen: opciones.resumenExito,
        detalle: mensaje,
        vida: opciones.vidaExito,
    });
}

export function procesarErrorConToast(error) {
    const opciones = obtenerOpcionesToast(error?.config);
    if (!esOperacionNotificable(error?.config, opciones)) {
        return;
    }

    if (!opciones.mostrarError) {
        return;
    }

    const mensaje = extraerMensajeError(error);

    agregarToast({
        severidad: 'error',
        resumen: opciones.resumenError,
        detalle: mensaje,
        vida: opciones.vidaError,
    });
}
