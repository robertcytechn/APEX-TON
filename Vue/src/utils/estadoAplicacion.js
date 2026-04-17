import { reactive } from 'vue';

const URL_BASE_API_PREDETERMINADA = import.meta.env.PROD ? '/apex/api/' : '/api/';

function normalizarUrlBaseApi(urlBase) {
    const texto = String(urlBase || '').trim();
    if (!texto) {
        return '/api/';
    }

    if (/^https?:\/\//i.test(texto) || texto.startsWith('//')) {
        return texto.endsWith('/') ? texto : `${texto}/`;
    }

    const textoSinPuntoInicial = texto.startsWith('./') ? texto.slice(1) : texto;
    const conSlashInicial = textoSinPuntoInicial.startsWith('/') ? textoSinPuntoInicial : `/${textoSinPuntoInicial}`;
    return conSlashInicial.endsWith('/') ? conSlashInicial : `${conSlashInicial}/`;
}

const URL_BASE_API = normalizarUrlBaseApi(import.meta.env.VITE_API_BASE_URL || URL_BASE_API_PREDETERMINADA).replace(/\/$/, '');

const CLAVE_BYPASS_MANTENIMIENTO = 'binsurmx_bypass_mantenimiento_hasta';
const DURACION_BYPASS_MS = 60 * 60 * 1000;
const VENTANA_ATAJO_SEGUNDO_PASO_MS = 1000;
const INTERVALO_MINIMO_SINCRONIZACION_MS = 30000;
const INTERVALO_REINTENTO_SINCRONIZACION_ERROR_MS = 5000;
const RUTAS_API_CONFIGURACION_MANTENIMIENTO = [
    '/configuraciones-globales/publicas/mantenimiento/',
    '/configuraciones-globales/configuraciones/'
];

const CONFIG_KEYS = {
    estadoAplicacion: ['ESTADO_APLICACION', 'ESTADO_APPLICACION'],
    tituloActualizacion: ['TITULO_ESTADO_APLICACION_POR_ACTUALIZACION'],
    mensajeActualizacion: ['MENSAJE_APLICACION_POR_ACTUALIZACION'],
    etiquetaActualizacion: ['ETIQUETA_POR_ACTUALIZACION'],
    iconoActualizacion: ['ICONO_ACTUALIZACION'],
    decoradoresActualizacion: ['DECORADORES_ACTUALIZACION'],
    recomendacionesActualizacion: ['RECOMENDACIONES_ACTUALIZACION'],
    inicioActualizacion: ['INICIO_ACTUALIZACION'],
    finActualizacion: ['FIN_ACTUALIZACION']
};

const ESTADO_APLICACION_BASE = {
    modoMantenimiento: false,
    estadoActual: 'actualizacion_software',
    estadosDisponibles: {
        mantenimiento_general: {
            titulo: 'Mantenimiento general del sistema',
            mensaje: 'Estamos aplicando ajustes preventivos para mejorar estabilidad y rendimiento.',
            etiqueta: 'Intervencion preventiva',
            icono: 'pi pi-wrench',
            decoradores: ['Ajustes de rendimiento', 'Reinicio de servicios', 'Validacion final'],
            recomendaciones: ['Espera la reactivacion programada.', 'Evita recargas continuas durante la intervencion.']
        },
        actualizacion_software: {
            titulo: 'Actualizacion de software en progreso',
            mensaje: 'Se estan desplegando nuevas funciones y correcciones de seguridad en el sistema, estamos trabajando para minimizar el tiempo de inactividad.',
            etiqueta: 'Actualizacion programada de software',
            icono: 'pi pi-cloud-upload',
            decoradores: [
                'Actualizacion de UX',
                'Mejoras de rendimiento',
                'Parches de seguridad',
                'Optimizacion de consultas',
                'Refactorizacion de codigo',
                'Implementacion de nuevas vistas',
                'Integracion de nuevas APIs',
                'Pruebas de regresion',
                'Monitoreo post-despliegue'
            ],
            recomendaciones: [
                'Por seguridad el sistema estara fuera de linea durante la actualizacion.',
                'Espera el tiempo determinado para la reactivacion.',
                'Si el mantenimiento se extiende, consulta con soporte para mas informacion.',
                'Si crees que es un error, reportalo a soporte para investigacion.'
            ]
        },
        mantenimiento_infraestructura: {
            titulo: 'Mantenimiento de infraestructura',
            mensaje: 'Se estan optimizando recursos de red y servidores para mantener la continuidad operativa.',
            etiqueta: 'Operacion de plataforma',
            icono: 'pi pi-server',
            decoradores: ['Ajuste de red', 'Balanceo de carga', 'Monitoreo de nodos'],
            recomendaciones: ['Los servicios pueden responder de forma intermitente.', 'Reintenta acceso al finalizar la ventana.']
        },
        migracion_datos: {
            titulo: 'Migracion de datos en ejecucion',
            mensaje: 'Estamos migrando informacion para mejorar consistencia, trazabilidad y tiempos de consulta.',
            etiqueta: 'Proceso critico de datos',
            icono: 'pi pi-database',
            decoradores: ['Respaldo incremental', 'Validacion de integridad', 'Sincronizacion de tablas'],
            recomendaciones: ['No intentes modificar registros durante la migracion.', 'Consulta con soporte antes de reintentar operaciones.']
        },
        contingencia_operativa: {
            titulo: 'Contingencia operativa temporal',
            mensaje: 'Se detecto una incidencia tecnica y estamos aplicando acciones de estabilizacion.',
            etiqueta: 'Atencion prioritaria',
            icono: 'pi pi-exclamation-triangle',
            decoradores: ['Diagnostico activo', 'Mitigacion de impacto', 'Recuperacion de servicio'],
            recomendaciones: ['Mantente atento al tiempo estimado de recuperacion.', 'Si el incidente persiste, escalar a administracion.']
        }
    },
    temporizadorReactivacion: {
        habilitar: false,
        fecha: '',
        hora: '',
        fechaInicio: '',
        horaInicio: ''
    }
};

// 1) Para que sirve: estado reactivo global de disponibilidad del frontend.
// 2) Como funciona: se alimenta desde ConfiguracionesGlobales y aplica fallback local.
// 3) Que hace: bloquea o libera rutas segun estado y tiempo de fin de actualizacion.
// 4) Como editarla: ajusta claves de CONFIG_KEYS y plantillas de ESTADO_APLICACION_BASE.
export const ESTADO_APLICACION = reactive(clonarObjeto(ESTADO_APLICACION_BASE));

let ultimaSincronizacionExitosaMs = 0;
let ultimaSincronizacionErrorMs = 0;
let promesaSincronizacion = null;
let listenerBypassRegistrado = false;
let marcaPasoUnoAtajoMs = 0;

function clonarObjeto(valor) {
    return JSON.parse(JSON.stringify(valor));
}

function normalizarClave(valor) {
    return String(valor || '')
        .trim()
        .toUpperCase()
        .replace(/\s+/g, '_');
}

function normalizarClaveEstado(valor) {
    return String(valor || '')
        .trim()
        .toLowerCase()
        .replace(/\s+/g, '_');
}

function dividirListaTexto(valor) {
    const texto = String(valor || '').trim();
    if (!texto) {
        return [];
    }
    return texto
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
}

function darFormatoDos(valor) {
    return String(valor).padStart(2, '0');
}

function convertirFechaHoraATextos(fechaHora) {
    if (!(fechaHora instanceof Date) || Number.isNaN(fechaHora.getTime())) {
        return { fecha: '', hora: '' };
    }

    return {
        fecha: `${fechaHora.getFullYear()}-${darFormatoDos(fechaHora.getMonth() + 1)}-${darFormatoDos(fechaHora.getDate())}`,
        hora: `${darFormatoDos(fechaHora.getHours())}:${darFormatoDos(fechaHora.getMinutes())}:${darFormatoDos(fechaHora.getSeconds())}`
    };
}

function parsearFechaHora(valor) {
    const texto = String(valor || '').trim();
    if (!texto) {
        return null;
    }
    const fecha = new Date(texto);
    return Number.isNaN(fecha.getTime()) ? null : fecha;
}

function obtenerMapaConfiguraciones(configuraciones) {
    const mapa = new Map();
    for (const configuracion of configuraciones || []) {
        const clave = normalizarClave(configuracion?.clave);
        if (!clave) {
            continue;
        }
        mapa.set(clave, configuracion);
    }
    return mapa;
}

function obtenerValorConfiguracion(mapa, aliases, valorDefecto = '') {
    for (const alias of aliases || []) {
        const configuracion = mapa.get(normalizarClave(alias));
        if (configuracion && configuracion.valor !== null && configuracion.valor !== undefined) {
            return String(configuracion.valor);
        }
    }
    return valorDefecto;
}

function esEstadoProduccion(claveEstado) {
    return ['PRODUCCION', 'PRODUCCION_TOTAL', 'OPERACION', 'OPERATIVO', 'ACTIVO', 'NORMAL'].includes(normalizarClave(claveEstado));
}

function construirEstadoDesdeConfiguraciones(configuraciones) {
    const base = clonarObjeto(ESTADO_APLICACION_BASE);
    const mapa = obtenerMapaConfiguraciones(configuraciones);

    const tituloActualizacion = obtenerValorConfiguracion(mapa, CONFIG_KEYS.tituloActualizacion, base.estadosDisponibles.actualizacion_software.titulo);
    const mensajeActualizacion = obtenerValorConfiguracion(mapa, CONFIG_KEYS.mensajeActualizacion, base.estadosDisponibles.actualizacion_software.mensaje);
    const etiquetaActualizacion = obtenerValorConfiguracion(mapa, CONFIG_KEYS.etiquetaActualizacion, base.estadosDisponibles.actualizacion_software.etiqueta);
    const iconoActualizacion = obtenerValorConfiguracion(mapa, CONFIG_KEYS.iconoActualizacion, base.estadosDisponibles.actualizacion_software.icono);

    const decoradoresActualizacion = dividirListaTexto(
        obtenerValorConfiguracion(
            mapa,
            CONFIG_KEYS.decoradoresActualizacion,
            base.estadosDisponibles.actualizacion_software.decoradores.join(',')
        )
    );
    const recomendacionesActualizacion = dividirListaTexto(
        obtenerValorConfiguracion(
            mapa,
            CONFIG_KEYS.recomendacionesActualizacion,
            base.estadosDisponibles.actualizacion_software.recomendaciones.join(',')
        )
    );

    base.estadosDisponibles.actualizacion_software = {
        ...base.estadosDisponibles.actualizacion_software,
        titulo: tituloActualizacion,
        mensaje: mensajeActualizacion,
        etiqueta: etiquetaActualizacion,
        icono: iconoActualizacion,
        decoradores: decoradoresActualizacion.length ? decoradoresActualizacion : base.estadosDisponibles.actualizacion_software.decoradores,
        recomendaciones: recomendacionesActualizacion.length ? recomendacionesActualizacion : base.estadosDisponibles.actualizacion_software.recomendaciones
    };

    const fechaInicioActualizacion = parsearFechaHora(obtenerValorConfiguracion(mapa, CONFIG_KEYS.inicioActualizacion, ''));
    const fechaFinActualizacion = parsearFechaHora(obtenerValorConfiguracion(mapa, CONFIG_KEYS.finActualizacion, ''));

    const { fecha: fechaInicio, hora: horaInicio } = convertirFechaHoraATextos(fechaInicioActualizacion);
    const { fecha: fechaFin, hora: horaFin } = convertirFechaHoraATextos(fechaFinActualizacion);

    base.temporizadorReactivacion = {
        habilitar: Boolean(fechaFinActualizacion),
        fecha: fechaFin,
        hora: horaFin,
        fechaInicio,
        horaInicio
    };

    const valorEstadoAplicacion = obtenerValorConfiguracion(mapa, CONFIG_KEYS.estadoAplicacion, 'PRODUCCION');
    const estadoNormalizado = normalizarClaveEstado(valorEstadoAplicacion);
    const estadoExiste = !!base.estadosDisponibles[estadoNormalizado];

    const finalizacionAlcanzada = Boolean(
        fechaFinActualizacion
        && Date.now() >= fechaFinActualizacion.getTime()
        && estadoNormalizado === 'actualizacion_software'
    );

    if (esEstadoProduccion(estadoNormalizado) || !estadoExiste || finalizacionAlcanzada) {
        base.modoMantenimiento = false;
        base.estadoActual = 'actualizacion_software';
    } else {
        base.modoMantenimiento = true;
        base.estadoActual = estadoNormalizado;
    }

    return base;
}

function aplicarEstadoAplicacion(estadoNuevo) {
    ESTADO_APLICACION.modoMantenimiento = Boolean(estadoNuevo?.modoMantenimiento);
    ESTADO_APLICACION.estadoActual = estadoNuevo?.estadoActual || ESTADO_APLICACION_BASE.estadoActual;
    ESTADO_APLICACION.estadosDisponibles = estadoNuevo?.estadosDisponibles || clonarObjeto(ESTADO_APLICACION_BASE.estadosDisponibles);
    ESTADO_APLICACION.temporizadorReactivacion = estadoNuevo?.temporizadorReactivacion || clonarObjeto(ESTADO_APLICACION_BASE.temporizadorReactivacion);
}

async function leerConfiguracionesDesdeRutaApi(rutaApi) {
    const respuesta = await fetch(`${URL_BASE_API}${rutaApi}`, {
        method: 'GET',
        credentials: 'include',
        cache: 'no-store',
        headers: {
            Accept: 'application/json'
        }
    });

    return respuesta;
}

async function obtenerConfiguracionesGlobalesDesdeApi() {
    let ultimoError = null;

    for (const rutaApi of RUTAS_API_CONFIGURACION_MANTENIMIENTO) {
        const respuesta = await leerConfiguracionesDesdeRutaApi(rutaApi);

        if (!respuesta.ok) {
            ultimoError = new Error(`No se pudo leer configuraciones globales. HTTP ${respuesta.status} en ${rutaApi}`);
            continue;
        }

        const payload = await respuesta.json();
        return Array.isArray(payload?.data) ? payload.data : [];
    }

    if (ultimoError) {
        throw ultimoError;
    }

    throw new Error('No se pudo leer configuraciones globales de mantenimiento.');
}

function intentarLiberacionLocalPorFin() {
    const temporizador = ESTADO_APLICACION.temporizadorReactivacion || {};
    if (!temporizador.habilitar) {
        return;
    }

    const fechaFin = parsearFechaHora(`${temporizador.fecha || ''}T${temporizador.hora || ''}`);
    if (!fechaFin) {
        return;
    }

    if (Date.now() >= fechaFin.getTime()) {
        ESTADO_APLICACION.modoMantenimiento = false;
    }
}

// 1) Para que sirve: refrescar el estado operativo desde ConfiguracionesGlobales.
// 2) Como funciona: consume API, interpreta claves de estado y actualiza el objeto reactivo global.
// 3) Que hace: activa/desactiva mantenimiento, personaliza textos y aplica liberacion por FIN_ACTUALIZACION.
// 4) Como editarla: ajusta INTERVALO_MINIMO_SINCRONIZACION_MS o agrega nuevas claves en CONFIG_KEYS.
export async function sincronizarEstadoAplicacion({ forzar = false } = {}) {
    const ahoraMs = Date.now();
    if (!forzar && (ahoraMs - ultimaSincronizacionExitosaMs) < INTERVALO_MINIMO_SINCRONIZACION_MS) {
        intentarLiberacionLocalPorFin();
        return ESTADO_APLICACION;
    }

    if (!forzar && (ahoraMs - ultimaSincronizacionErrorMs) < INTERVALO_REINTENTO_SINCRONIZACION_ERROR_MS) {
        intentarLiberacionLocalPorFin();
        return ESTADO_APLICACION;
    }

    if (promesaSincronizacion) {
        return promesaSincronizacion;
    }

    promesaSincronizacion = (async () => {
        try {
            const configuraciones = await obtenerConfiguracionesGlobalesDesdeApi();
            const estadoReconstruido = construirEstadoDesdeConfiguraciones(configuraciones);
            aplicarEstadoAplicacion(estadoReconstruido);
            ultimaSincronizacionExitosaMs = Date.now();
        } catch {
            ultimaSincronizacionErrorMs = Date.now();
            intentarLiberacionLocalPorFin();
        } finally {
            promesaSincronizacion = null;
        }

        return ESTADO_APLICACION;
    })();

    return promesaSincronizacion;
}

export function estaBypassMantenimientoActivo() {
    try {
        const marcaExpiracion = Number(sessionStorage.getItem(CLAVE_BYPASS_MANTENIMIENTO) || 0);
        if (!Number.isFinite(marcaExpiracion) || marcaExpiracion <= 0) {
            return false;
        }

        if (Date.now() >= marcaExpiracion) {
            sessionStorage.removeItem(CLAVE_BYPASS_MANTENIMIENTO);
            return false;
        }

        return true;
    } catch {
        return false;
    }
}

export function activarBypassMantenimiento() {
    try {
        sessionStorage.setItem(CLAVE_BYPASS_MANTENIMIENTO, String(Date.now() + DURACION_BYPASS_MS));
        window.dispatchEvent(new CustomEvent('binsur:bypass-mantenimiento-activado'));
    } catch {
        // Ignorar errores de almacenamiento para no romper el flujo principal.
    }
}

export function limpiarBypassMantenimiento() {
    try {
        sessionStorage.removeItem(CLAVE_BYPASS_MANTENIMIENTO);
    } catch {
        // Ignorar errores de almacenamiento para no romper el flujo principal.
    }
}

function normalizarTecla(event) {
    return String(event?.key || '')
        .trim()
        .toLowerCase();
}

function esPrimerPasoAtajo(event) {
    const tecla = normalizarTecla(event);
    return event.ctrlKey && event.altKey && (tecla === 'control' || tecla === 'alt');
}

function esSegundoPasoAtajo(event) {
    return event.ctrlKey && event.altKey && normalizarTecla(event) === 'y';
}

function manejarAtajoBypassMantenimiento(event) {
    const ahoraMs = Date.now();

    if (esPrimerPasoAtajo(event)) {
        marcaPasoUnoAtajoMs = ahoraMs;
        return;
    }

    if (
        esSegundoPasoAtajo(event)
        && marcaPasoUnoAtajoMs > 0
        && (ahoraMs - marcaPasoUnoAtajoMs) <= VENTANA_ATAJO_SEGUNDO_PASO_MS
    ) {
        activarBypassMantenimiento();
        marcaPasoUnoAtajoMs = 0;
        event.preventDefault();
        event.stopPropagation();
        return;
    }

    if (marcaPasoUnoAtajoMs > 0 && (ahoraMs - marcaPasoUnoAtajoMs) > VENTANA_ATAJO_SEGUNDO_PASO_MS) {
        marcaPasoUnoAtajoMs = 0;
    }
}

// 1) Para que sirve: habilitar atajo de contingencia para saltar bloqueo de mantenimiento.
// 2) Como funciona: escucha Ctrl+Alt y luego Ctrl+Alt+Y dentro de 1 segundo.
// 3) Que hace: activa bypass temporal por 60 minutos solo en la sesion actual del navegador.
// 4) Como editarla: ajusta DURACION_BYPASS_MS o la secuencia en esPrimerPasoAtajo/esSegundoPasoAtajo.
export function inicializarListenerBypassMantenimiento() {
    if (listenerBypassRegistrado || typeof window === 'undefined') {
        return;
    }
    window.addEventListener('keydown', manejarAtajoBypassMantenimiento, true);
    listenerBypassRegistrado = true;
}
