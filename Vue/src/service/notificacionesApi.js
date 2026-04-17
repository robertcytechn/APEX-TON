const METODOS_MUTACION = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CLAVES_NO_VALIDACION = new Set(['status', 'message', 'mensaje', 'detail', 'error', 'data', 'errors']);

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
        return 'No se recibio respuesta del servidor. Verifica tu conexion.';
    }

    if (codigo >= 500) {
        return 'Ocurrio un error interno en el servidor. Intenta nuevamente.';
    }

    if (codigo > 0) {
        return `La solicitud no pudo completarse (HTTP ${codigo}).`;
    }

    return 'No fue posible completar la solicitud.';
}

function obtenerOpcionesToast(config) {
    const opciones = config?.notificacionToast || {};

    return {
        mostrarExito: opciones.exito !== false,
        mostrarError: opciones.error !== false,
        resumenExito: textoLimpio(opciones.resumenExito) || 'Operacion exitosa',
        resumenError: textoLimpio(opciones.resumenError) || 'Error en la operacion',
        vidaExito: Number(opciones.vidaExito) > 0 ? Number(opciones.vidaExito) : 4500,
        vidaError: Number(opciones.vidaError) > 0 ? Number(opciones.vidaError) : 7000,
    };
}

function esMetodoMutacion(config) {
    const metodo = String(config?.method || '').trim().toUpperCase();
    return METODOS_MUTACION.has(metodo);
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
    if (!esMetodoMutacion(response?.config)) {
        return;
    }

    const opciones = obtenerOpcionesToast(response?.config);
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
    if (!esMetodoMutacion(error?.config)) {
        return;
    }

    const opciones = obtenerOpcionesToast(error?.config);
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
