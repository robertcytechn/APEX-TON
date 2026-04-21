import AppLayout from '@/layout/AppLayout.vue';
import { useCategoriasOperativasStore } from '@/stores/categoriasOperativas';
import { useSesionStore } from '@/stores/sesion';
import { pinia } from '@/stores/pinia';
import {
    ESTADO_APLICACION,
    estaBypassMantenimientoActivo,
    inicializarListenerBypassMantenimiento,
    sincronizarEstadoAplicacion
} from '@/utils/estadoAplicacion';
import { createRouter, createWebHistory } from 'vue-router';

const CLAVE_SESION = 'binsurmx_sesion';

inicializarListenerBypassMantenimiento();

function haySesionPersistidaLocal() {
    return !!localStorage.getItem(CLAVE_SESION);
}

// 1) Para qué sirve: resolver automáticamente la primera ruta operativa habilitada.
// 2) Cómo funciona: carga categorías activas del store y toma la primera ruta construida.
// 3) Qué hace: redirige al contador/gerente a su primera pestaña de captura disponible.
// 4) Cómo editarla: cambia el criterio de selección (por orden, preferencia o rol) dentro de esta función.
async function obtenerPrimeraRutaOperativa() {
    const categoriasStore = useCategoriasOperativasStore(pinia);
    await categoriasStore.cargarCategoriasActivas();
    return categoriasStore.rutasCapturaOperativa[0]?.ruta || null;
}

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'layout-principal',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'inicio',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/pages/Inicio.vue')
                },
                {
                    path: 'pages',
                    redirect: '/pages/perfil'
                },
                {
                    path: 'pages/perfil',
                    name: 'perfil-usuario',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/pages/PerfilUsuario.vue')
                },
                {
                    path: 'pages/soporte-tecnico',
                    name: 'soporte-tecnico',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/pages/SoporteTecnico.vue')
                },
                {
                    path: 'reportes/estado-resultados',
                    name: 'reportes-estado-resultados',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/reportes/EstadoResultados.vue')
                },
                {
                    path: 'reportes/reporte-diario',
                    name: 'reportes-reporte-diario',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/reportes/ReporteDiario.vue')
                },
                {
                    path: 'reportes/dias-contables',
                    name: 'reportes-dias-contables',
                    meta: { requiereSesion: true },
                    component: () => import('@/views/reportes/DiasContables.vue')
                },
                {
                    path: 'reportes/estadisticas',
                    name: 'reportes-estadisticas',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO'] },
                    component: () => import('@/views/reportes/Estadisticas.vue')
                },
                {
                    path: 'admin',
                    redirect: '/admin/usuarios'
                },
                {
                    path: 'director',
                    redirect: '/director/sucursales'
                },
                {
                    path: 'director/sucursales',
                    name: 'director-sucursales',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR'] },
                    component: () => import('@/views/director/SucursalesDirector.vue')
                },
                {
                    path: 'director/usuarios',
                    name: 'director-usuarios',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR'] },
                    component: () => import('@/views/director/UsuariosDirector.vue')
                },
                {
                    path: 'director/configuraciones-globales',
                    name: 'director-configuraciones-globales',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR'] },
                    component: () => import('@/views/director/ConfiguracionesGlobalesDirector.vue')
                },
                {
                    path: 'director/rubros-contables',
                    name: 'director-rubros-contables',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR'] },
                    component: () => import('@/views/director/RubrosContablesDirector.vue')
                },
                {
                    path: 'director/catalogo-operativo',
                    name: 'director-catalogo-operativo',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR'] },
                    component: () => import('@/views/director/CatalogoOperativoDirector.vue')
                },
                {
                    path: 'director/consulta-captura-operativa',
                    name: 'director-consulta-captura-operativa',
                    meta: { requiereSesion: true, requiereRoles: ['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO'] },
                    component: () => import('@/views/director/ConsultaCapturaOperativaDirector.vue')
                },
                {
                    path: 'admin/usuarios',
                    name: 'admin-usuarios',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/UsuariosAdmin.vue')
                },
                {
                    path: 'admin/roles',
                    name: 'admin-roles',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/RolesAdmin.vue')
                },
                {
                    path: 'admin/sucursales',
                    name: 'admin-sucursales',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/SucursalesAdmin.vue')
                },
                {
                    path: 'admin/configuraciones-globales',
                    name: 'admin-configuraciones-globales',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/ConfiguracionesGlobalesAdmin.vue')
                },
                {
                    path: 'admin/rubros-contables',
                    name: 'admin-rubros-contables',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/RubrosContablesAdmin.vue')
                },
                {
                    path: 'admin/padres-rubros-contables',
                    name: 'admin-padres-rubros-contables',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/PadresRubrosContablesAdmin.vue')
                },
                {
                    path: 'admin/catalogo-operativo',
                    name: 'admin-catalogo-operativo',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/CatalogoOperativoAdmin.vue')
                },
                {
                    path: 'admin/centro-control',
                    name: 'admin-centro-control',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/CentroControlAdmin.vue')
                },
                {
                    path: 'admin/soporte-tecnico',
                    name: 'admin-soporte-tecnico',
                    meta: { requiereSesion: true, requiereAdmin: true },
                    component: () => import('@/views/admin/SoporteTecnicoAdmin.vue')
                },
                {
                    path: 'admin/categorias-operativas',
                    redirect: '/admin/catalogo-operativo'
                },
                {
                    path: 'admin/conceptos',
                    redirect: '/admin/catalogo-operativo'
                },
                {
                    path: 'admin/detalles-parametrizados',
                    redirect: '/admin/catalogo-operativo'
                },
                {
                    path: 'operativo',
                    name: 'operativo-captura',
                    meta: { requiereSesion: true, requiereRoles: ['CONTADOR', 'GERENTE'] },
                    component: () => import('@/views/contador/CapturaOperativaCategoria.vue')
                },
                {
                    path: 'operativo/:categoriaId(\\d+)',
                    name: 'operativo-categoria',
                    meta: { requiereSesion: true, requiereRoles: ['CONTADOR', 'GERENTE'] },
                    component: () => import('@/views/contador/CapturaOperativaCategoria.vue')
                }
            ]
        },
        {
            path: '/pages/notfound',
            name: 'noencontrado',
            meta: { publica: true },
            component: () => import('@/views/pages/NotFound.vue')
        },
        {
            path: '/mantenimiento',
            name: 'mantenimiento',
            meta: { publica: true },
            component: () => import('@/views/pages/Mantenimiento.vue')
        },
        {
            path: '/auth/login',
            name: 'login',
            meta: { publica: true },
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/auth/access',
            name: 'sinacceso',
            meta: { publica: true },
            component: () => import('@/views/pages/auth/Access.vue')
        },
        {
            path: '/auth/error',
            name: 'error',
            meta: { publica: true },
            component: () => import('@/views/pages/auth/Error.vue')
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/pages/notfound'
        }
    ]
});

// 1) Para qué sirve: aplicar bloqueo/desbloqueo inmediato al alternar bypass de mantenimiento.
// 2) Cómo funciona: escucha un evento global y reevalúa estado de mantenimiento forzando sincronización.
// 3) Qué hace: redirige a /mantenimiento al desactivar bypass y libera a / al activarlo.
// 4) Cómo editarla: cambia rutas objetivo si la pantalla de bloqueo cambia de nombre.
async function manejarCambioBypassMantenimiento(event) {
    try {
        const bypassActivo = typeof event?.detail?.activo === 'boolean'
            ? event.detail.activo
            : estaBypassMantenimientoActivo();

        await sincronizarEstadoAplicacion({ forzar: true });

        const modoMantenimientoActivo = ESTADO_APLICACION.modoMantenimiento === true;
        const rutaActual = router.currentRoute.value;
        const vaRutaMantenimiento = rutaActual?.name === 'mantenimiento';

        if (modoMantenimientoActivo && !bypassActivo && !vaRutaMantenimiento) {
            await router.replace({ name: 'mantenimiento' });
            return;
        }

        if ((!modoMantenimientoActivo || bypassActivo) && vaRutaMantenimiento) {
            await router.replace('/');
        }
    } catch {
        // Ignorar errores para no romper la navegacion principal.
    }
}

if (typeof window !== 'undefined') {
    window.addEventListener('binsur:bypass-mantenimiento-cambiado', manejarCambioBypassMantenimiento);
}

// 1) Para qué sirve: proteger navegación por sesión, rol y privilegios administrativos.
// 2) Cómo funciona: verifica sesión local/remota y evalúa meta campos de cada ruta.
// 3) Qué hace: redirige a login, acceso denegado o primera captura según contexto.
// 4) Cómo editarla: agrega nuevas reglas de autorización dentro de este guard global.
router.beforeEach(async (to) => {
    await sincronizarEstadoAplicacion();

    const modoMantenimientoActivo = ESTADO_APLICACION.modoMantenimiento === true;
    const bypassMantenimientoActivo = estaBypassMantenimientoActivo();
    const vaRutaMantenimiento = to.name === 'mantenimiento';

    if (modoMantenimientoActivo && !bypassMantenimientoActivo && !vaRutaMantenimiento) {
        return {
            name: 'mantenimiento'
        };
    }

    if ((!modoMantenimientoActivo || bypassMantenimientoActivo) && vaRutaMantenimiento) {
        return '/';
    }

    const sesionStore = useSesionStore(pinia);
    const esPublica = to.matched.some((ruta) => ruta.meta.publica);
    const requiereAdmin = to.matched.some((ruta) => ruta.meta.requiereAdmin);
    const requiereRoles = to.matched.flatMap((ruta) => ruta.meta.requiereRoles || []);
    const haySesionLocal = haySesionPersistidaLocal();
    const debeVerificarSesion = !sesionStore.sesionVerificada && (!esPublica || haySesionLocal);

    if (debeVerificarSesion) {
        await sesionStore.verificarSesionActual();
    } else if (!sesionStore.sesionVerificada && esPublica && !haySesionLocal) {
        sesionStore.sesionVerificada = true;
        sesionStore.limpiarSesionLocal();
    }

    if (to.path === '/auth/login' && sesionStore.estaAutenticado) {
        if (sesionStore.requiereCambioPassword) {
            return {
                path: '/pages/perfil',
                hash: '#seguridad',
                query: { forzarCambioPassword: '1' }
            };
        }
        return '/';
    }

    if (!esPublica && !sesionStore.estaAutenticado) {
        return {
            path: '/auth/login',
            query: { redirect: to.fullPath }
        };
    }

    if (sesionStore.estaAutenticado && sesionStore.requiereCambioPassword && to.name !== 'perfil-usuario') {
        return {
            path: '/pages/perfil',
            hash: '#seguridad',
            query: { forzarCambioPassword: '1' }
        };
    }

    if (requiereAdmin && !sesionStore.esAdministrador) {
        return '/auth/access';
    }

    if (requiereRoles.length) {
        const autorizado = sesionStore.cumpleAlgunoRoles(requiereRoles);
        if (!autorizado) {
            return '/auth/access';
        }
    }

    if (to.name === 'operativo-captura' && sesionStore.esContadorOGerente) {
        try {
            const primeraRuta = await obtenerPrimeraRutaOperativa();
            if (primeraRuta) {
                return primeraRuta;
            }
        } catch {
            return true;
        }
    }

    return true;
});

export default router;
