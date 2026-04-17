import api from '@/service/api';

function obtenerConfiguracionNotificacionSilenciosa() {
    return {
        notificacionToast: {
            exito: false,
            error: false
        }
    };
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

// 1) Para qué sirve: inicializar cookie/token CSRF requerido por Django SessionAuth.
// 2) Cómo funciona: hace GET al endpoint csrf para que el navegador guarde la cookie.
// 3) Qué hace: prepara el cliente antes de enviar credenciales.
// 4) Cómo editarla: cambia la ruta si backend mueve el endpoint de CSRF.
export function obtenerCsrf() {
    return api.get('/usuarios/csrf/');
}

// 1) Para qué sirve: iniciar sesión contra backend con identificador y contraseña.
// 2) Cómo funciona: envía POST y recibe usuario/roles/permisos en respuesta estándar.
// 3) Qué hace: abre sesión Django para el cliente actual.
// 4) Cómo editarla: actualiza payload si backend agrega campos obligatorios de login.
export async function iniciarSesion(payload) {
    const respuestaCsrf = await obtenerCsrf();
    const tokenCsrf = String(respuestaCsrf?.data?.data?.csrf_token || '').trim();
    const tokenCookie = obtenerCookie('csrftoken');
    const tokenFinal = tokenCookie || tokenCsrf;

    const configuracionBase = obtenerConfiguracionNotificacionSilenciosa();

    const configuracion = tokenFinal
        ? {
            ...configuracionBase,
            headers: {
                'X-CSRFToken': tokenFinal
            }
        }
        : configuracionBase;

    return api.post('/usuarios/iniciar-sesion/', payload, configuracion);
}

// 1) Para qué sirve: cerrar sesión del usuario autenticado en backend.
// 2) Cómo funciona: ejecuta POST al endpoint de cierre.
// 3) Qué hace: invalida la sesión activa del navegador.
// 4) Cómo editarla: modifica la ruta si se versiona el endpoint de logout.
export function cerrarSesion() {
    return api.post('/usuarios/cerrar-sesion/', null, obtenerConfiguracionNotificacionSilenciosa());
}

// 1) Para qué sirve: consultar la sesión actual sin pedir credenciales nuevamente.
// 2) Cómo funciona: solicita GET y backend responde con datos de sesión o 401.
// 3) Qué hace: permite rehidratar estado al recargar la app.
// 4) Cómo editarla: añade params/cabeceras aquí si se requiere contexto adicional.
export function obtenerSesionActual() {
    return api.get('/usuarios/sesion-actual/');
}

// 1) Para qué sirve: obtener información del perfil del usuario autenticado.
// 2) Cómo funciona: consulta endpoint dedicado de perfil propio en backend.
// 3) Qué hace: hidrata formulario de cuenta con datos actuales del usuario.
// 4) Cómo editarla: agrega parámetros opcionales si el endpoint evoluciona.
export function obtenerPerfilPropio() {
    return api.get('/usuarios/perfil-propio/');
}

// 1) Para qué sirve: actualizar correo, contraseña e imagen del perfil del usuario autenticado.
// 2) Cómo funciona: envía PATCH multipart para soportar campos y archivo en una sola petición.
// 3) Qué hace: persiste cambios del perfil sin salir de la sesión actual.
// 4) Cómo editarla: añade flags extras aquí cuando backend incorpore nuevas opciones.
export function actualizarPerfilPropio(payload) {
    return api.patch('/usuarios/perfil-propio/', payload);
}
