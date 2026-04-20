import axios from 'axios';
import router from '@/router';
import { procesarErrorConToast, procesarRespuestaExitosaConToast } from '@/service/notificacionesApi';

// Configuracion de URL base para la API.
// Si no se define VITE_API_BASE_URL:
// - Desarrollo: /api/ (usa proxy de Vite)
// - Produccion: /apex/api/ (usa proxy inverso de Apache)
const URL_BASE_API_PREDETERMINADA = import.meta.env.PROD ? '/apex/api/' : '/api/';
const TIMEOUT_API_MS_PREDETERMINADO = 20000;

function resolverTimeoutApiMs() {
    const timeoutDefinido = Number(import.meta.env.VITE_API_TIMEOUT_MS);
    if (Number.isFinite(timeoutDefinido) && timeoutDefinido >= 5000) {
        return timeoutDefinido;
    }
    return TIMEOUT_API_MS_PREDETERMINADO;
}

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

const baseURL = normalizarUrlBaseApi(import.meta.env.VITE_API_BASE_URL || URL_BASE_API_PREDETERMINADA);
const timeoutApiMs = resolverTimeoutApiMs();
let redireccionandoLogin = false;
const CLAVE_SESION = 'binsurmx_sesion';

function haySesionPersistidaLocal() {
    return !!localStorage.getItem(CLAVE_SESION);
}

function limpiarSesionPersistidaLocal() {
    localStorage.removeItem(CLAVE_SESION);
}

function obtenerCookie(nombreCookie) {
    if (typeof document === 'undefined') {
        return '';
    }

    const cookies = document.cookie ? document.cookie.split(';') : [];
    const prefijo = `${nombreCookie}=`;

    for (const cookie of cookies) {
        const cookieLimpia = String(cookie || '').trim();
        if (cookieLimpia.startsWith(prefijo)) {
            return decodeURIComponent(cookieLimpia.slice(prefijo.length));
        }
    }

    return '';
}

const api = axios.create({
    baseURL,
    withCredentials: true,
    xsrfCookieName: 'csrftoken',
    xsrfHeaderName: 'X-CSRFToken',
    timeout: timeoutApiMs
});

api.interceptors.request.use(async (config) => {
    const metodo = String(config?.method || 'get').toUpperCase();
    const requiereCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(metodo);
    const urlSolicitud = String(config?.url || '');
    const esEndpointCsrf = urlSolicitud.includes('/usuarios/csrf/');

    if (requiereCsrf && !esEndpointCsrf && typeof window !== 'undefined') {
        const csrfActual = obtenerCookie('csrftoken');
        if (!csrfActual) {
            await api.get('/usuarios/csrf/');
        }
    }

    return config;
});

api.interceptors.response.use(
    (response) => {
        procesarRespuestaExitosaConToast(response);
        return response;
    },
    async (error) => {
        const estatus = error?.response?.status;
        const rutaActual = router.currentRoute.value.path;
        const urlSolicitud = error?.config?.url || '';
        const esLogin = urlSolicitud.includes('/usuarios/iniciar-sesion/');
        const esSesionActual = urlSolicitud.includes('/usuarios/sesion-actual/');
        const esCsrf = urlSolicitud.includes('/usuarios/csrf/');
        const haySesionLocal = haySesionPersistidaLocal();

        const noAutorizadoPorSesion = estatus === 401 || (estatus === 403 && !haySesionLocal);

        if (noAutorizadoPorSesion && !esLogin && !esSesionActual && !esCsrf && rutaActual !== '/auth/login' && !redireccionandoLogin) {
            redireccionandoLogin = true;
            limpiarSesionPersistidaLocal();
            await router.replace('/auth/login');
            redireccionandoLogin = false;
        }

        procesarErrorConToast(error);

        return Promise.reject(error);
    }
);

export default api;
