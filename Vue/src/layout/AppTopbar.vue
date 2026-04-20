<script setup>
import { useLayout } from '@/layout/composables/layout';
import { usePreferenciasUsuarioStore } from '@/stores/preferenciasUsuario';
import { useSesionStore } from '@/stores/sesion';
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppConfigurator from './AppConfigurator.vue';

const { layoutConfig, toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();
const sesionStore = useSesionStore();
const preferenciasUsuarioStore = usePreferenciasUsuarioStore();
const enrutador = useRouter();

const menuPerfilRef = ref(null);

const nombreMostradoUsuario = computed(() => {
    if (!sesionStore.usuario) {
        return 'Perfil';
    }
    return sesionStore.usuario.nombre || sesionStore.usuario.username || 'Perfil';
});

const rutaFotoPerfilUsuario = computed(() => sesionStore.usuario?.foto_perfil_url || '');

const inicialesUsuario = computed(() => {
    const base = (sesionStore.usuario?.nombre || sesionStore.usuario?.username || '').trim();
    if (!base) {
        return 'US';
    }
    const partes = base.split(/\s+/).filter(Boolean).slice(0, 2);
    return partes.map((parte) => parte[0]?.toUpperCase() || '').join('') || 'US';
});

// 1) Para qué sirve: alternar tema claro/oscuro desde la barra superior.
// 2) Cómo funciona: ejecuta toggleDarkMode y agenda persistencia de preferencia.
// 3) Qué hace: actualiza apariencia global de la app con feedback inmediato.
// 4) Cómo editarla: agrega notificación visual si quieres confirmar el cambio.
const alternarModoOscuro = () => {
    toggleDarkMode();
    if (sesionStore.estaAutenticado) {
        preferenciasUsuarioStore.programarGuardadoVisual(layoutConfig);
    }
};

// 1) Para qué sirve: abrir/cerrar menú contextual del perfil.
// 2) Cómo funciona: delega toggle al componente Menu vía ref.
// 3) Qué hace: permite acceder a acciones de perfil y sesión.
// 4) Cómo editarla: sustituye por otro overlay si cambias componente de menú.
const abrirMenuPerfil = (event) => {
    menuPerfilRef.value?.toggle(event);
};

// 1) Para qué sirve: navegar a vista de perfil del usuario.
// 2) Cómo funciona: hace push al router con ruta destino.
// 3) Qué hace: redirige a pantalla de datos personales.
// 4) Cómo editarla: actualiza ruta cuando exista módulo de perfil definitivo.
const irAPerfil = async () => {
    await enrutador.push('/pages/perfil');
};

// 1) Para qué sirve: navegar a sección de preferencias del usuario.
// 2) Cómo funciona: realiza push a ruta principal configurada.
// 3) Qué hace: abre flujo para ajustar apariencia y opciones.
// 4) Cómo editarla: cambia destino cuando exista pantalla dedicada de preferencias.
const irAPreferencias = async () => {
    await enrutador.push('/pages/perfil#seguridad');
};

// 1) Para qué sirve: cerrar sesión del usuario actual desde topbar.
// 2) Cómo funciona: ejecuta acción de store y redirige a login.
// 3) Qué hace: limpia sesión local/remota y protege rutas privadas.
// 4) Cómo editarla: agrega confirmación previa si negocio lo solicita.
const cerrarSesionUsuario = async () => {
    await sesionStore.cerrarSesion();
    await enrutador.replace('/auth/login');
};

const opcionesPerfil = ref([
    {
        label: 'Mi perfil',
        icon: 'pi pi-id-card',
        command: irAPerfil
    },
    {
        label: 'Seguridad y contraseña',
        icon: 'pi pi-lock',
        command: irAPreferencias
    },
    {
        separator: true
    },
    {
        label: 'Cerrar sesión',
        icon: 'pi pi-sign-out',
        command: cerrarSesionUsuario
    }
]);
</script>

<template>
    <div class="layout-topbar">
        <div class="layout-topbar-logo-container">
            <button class="layout-menu-button layout-topbar-action" @click="toggleMenu">
                <i class="pi pi-bars"></i>
            </button>
            <router-link to="/" class="layout-topbar-logo">
                <img
                    v-if="rutaFotoPerfilUsuario"
                    :src="rutaFotoPerfilUsuario"
                    alt="Imagen del usuario"
                    class="topbar-logo-avatar"
                />
                <svg v-else viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <circle cx="32" cy="32" r="29" fill="var(--primary-color)" opacity="0.14" />
                    <rect x="15" y="19" width="34" height="26" rx="6" fill="var(--primary-color)" />
                    <path d="M15 30H49" stroke="white" stroke-width="2" stroke-linecap="round" />
                    <path d="M24 24H27" stroke="white" stroke-width="2" stroke-linecap="round" />
                    <path d="M24 36H40" stroke="white" stroke-width="2" stroke-linecap="round" />
                    <path d="M40 24L44 28L40 32" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>

                <span class="hidden sm:flex flex-col leading-tight">
                    <span class="text-sm font-semibold">BinsurMX</span>
                    <small class="text-xs text-surface-500">Tesorería operativa</small>
                </span>
            </router-link>
        </div>

        <div class="layout-topbar-actions">
            <div class="layout-config-menu">
                <button type="button" class="layout-topbar-action" @click="alternarModoOscuro">
                    <i :class="['pi', { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }]"></i>
                </button>
                <div class="relative">
                    <button
                        v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'p-anchored-overlay-enter-active', leaveToClass: 'hidden', leaveActiveClass: 'p-anchored-overlay-leave-active', hideOnOutsideClick: true }"
                        type="button"
                        class="layout-topbar-action layout-topbar-action-highlight"
                    >
                        <i class="pi pi-palette"></i>
                    </button>
                    <AppConfigurator />
                </div>
            </div>

            <div class="relative">
                <button type="button" class="layout-topbar-action boton-perfil-topbar" @click="abrirMenuPerfil">
                    <img v-if="rutaFotoPerfilUsuario" :src="rutaFotoPerfilUsuario" alt="Avatar usuario" class="avatar-perfil-topbar" />
                    <span v-else class="avatar-perfil-fallback">{{ inicialesUsuario }}</span>
                    <span class="hidden sm:inline max-w-[12rem] truncate">{{ nombreMostradoUsuario }}</span>
                    <i class="pi pi-angle-down text-xs"></i>
                </button>
                <Menu ref="menuPerfilRef" :model="opcionesPerfil" popup />
            </div>
        </div>
    </div>
</template>

<style scoped>
.topbar-logo-avatar {
    width: 2.65rem;
    height: 2.65rem;
    border-radius: 0.9rem;
    object-fit: cover;
    border: 1px solid color-mix(in srgb, var(--surface-border) 80%, transparent);
    box-shadow: 0 8px 24px color-mix(in srgb, var(--primary-color) 18%, transparent);
}

.boton-perfil-topbar {
    width: auto !important;
    height: 2.6rem !important;
    border-radius: 9999px !important;
    padding: 0.2rem 0.65rem 0.2rem 0.25rem;
    gap: 0.5rem;
}

.avatar-perfil-topbar {
    width: 2rem;
    height: 2rem;
    border-radius: 9999px;
    object-fit: cover;
    border: 1px solid color-mix(in srgb, var(--surface-border) 80%, transparent);
}

.avatar-perfil-fallback {
    width: 2rem;
    height: 2rem;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--primary-color) 88%, black 6%);
    color: var(--primary-contrast-color);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
}
</style>
