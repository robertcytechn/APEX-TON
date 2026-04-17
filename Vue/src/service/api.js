import axios from 'axios';
import router from '@/router';

// Configuración de la URL base para la API, se puede configurar mediante una variable de entorno.
// Por defecto usa /api para desarrollo local.
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';
let redireccionandoLogin = false;
const CLAVE_SESION = 'binsurmx_sesion';

function haySesionPersistidaLocal() {
    return !!localStorage.getItem(CLAVE_SESION);
}

function limpiarSesionPersistidaLocal() {
    localStorage.removeItem(CLAVE_SESION);
}

const api = axios.create({
    baseURL,
    withCredentials: true,
    xsrfCookieName: 'csrftoken',
    xsrfHeaderName: 'X-CSRFToken'
});

api.interceptors.response.use(
    (response) => response,
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

        return Promise.reject(error);
    }
);

export default api;
