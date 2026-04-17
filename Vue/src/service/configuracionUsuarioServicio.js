import api from '@/service/api';

function obtenerConfiguracionNotificacionSilenciosa() {
    return {
        notificacionToast: {
            exito: false,
            error: false
        }
    };
}

// 1) Para qué sirve: consultar la configuración visual del usuario autenticado.
// 2) Cómo funciona: hace GET al endpoint de autoservicio de configuración.
// 3) Qué hace: devuelve preferencias persistidas para rehidratar la UI.
// 4) Cómo editarla: ajusta endpoint o agrega params si backend expande la consulta.
export function obtenerMiConfiguracionUsuario() {
    return api.get('/configuracion-usuario/mi-configuracion/');
}

// 1) Para qué sirve: persistir cambios parciales de preferencias del usuario.
// 2) Cómo funciona: envía PATCH con payload visual al endpoint de autoservicio.
// 3) Qué hace: actualiza configuración sin reemplazar campos no enviados.
// 4) Cómo editarla: agrega transformación del payload si backend exige formato distinto.
export function actualizarMiConfiguracionUsuario(payload) {
    return api.patch('/configuracion-usuario/mi-configuracion/', payload, obtenerConfiguracionNotificacionSilenciosa());
}
