import { computed, reactive } from 'vue';

const layoutConfig = reactive({
    preset: 'Aura',
    primary: 'emerald',
    surface: null,
    darkTheme: false,
    menuMode: 'static'
});

const layoutState = reactive({
    staticMenuInactive: false,
    overlayMenuActive: false,
    profileSidebarVisible: false,
    configSidebarVisible: false,
    sidebarExpanded: false,
    menuHoverActive: false,
    activeMenuItem: null,
    activePath: null
});

export function useLayout() {
    // 1) Para qué sirve: alternar el tema claro/oscuro de la aplicación.
    // 2) Cómo funciona: usa View Transitions si está disponible y ejecuta el cambio real en helper.
    // 3) Qué hace: invierte el modo visual sin recargar la vista.
    // 4) Cómo editarla: ajusta la estrategia de transición si deseas otra animación de cambio.
    const toggleDarkMode = () => {
        if (!document.startViewTransition) {
            executeDarkModeToggle();

            return;
        }

        document.startViewTransition(() => executeDarkModeToggle(event));
    };

    // 1) Para qué sirve: aplicar el cambio real de modo oscuro en estado y DOM.
    // 2) Cómo funciona: invierte `layoutConfig.darkTheme` y alterna clase raíz.
    // 3) Qué hace: sincroniza configuración reactiva con estilo global.
    // 4) Cómo editarla: cambia la clase CSS si la hoja global usa otro selector.
    const executeDarkModeToggle = () => {
        layoutConfig.darkTheme = !layoutConfig.darkTheme;
        document.documentElement.classList.toggle('app-dark');
    };

    // 1) Para qué sirve: abrir/cerrar menú según contexto desktop o móvil.
    // 2) Cómo funciona: evalúa ancho y modo de menú para activar bandera correspondiente.
    // 3) Qué hace: controla visibilidad de navegación lateral y overlay.
    // 4) Cómo editarla: modifica condiciones si cambias breakpoints o tipos de menú.
    const toggleMenu = () => {
        if (isDesktop()) {
            if (layoutConfig.menuMode === 'static') {
                layoutState.staticMenuInactive = !layoutState.staticMenuInactive;
            }

            if (layoutConfig.menuMode === 'overlay') {
                layoutState.overlayMenuActive = !layoutState.overlayMenuActive;
            }
        } else {
            layoutState.mobileMenuActive = !layoutState.mobileMenuActive;
        }
    };

    // 1) Para qué sirve: mostrar u ocultar panel de configuración visual.
    // 2) Cómo funciona: invierte bandera `configSidebarVisible`.
    // 3) Qué hace: habilita acceso al configurador de tema/layout.
    // 4) Cómo editarla: enlaza side effects aquí si agregas métricas o tracking.
    const toggleConfigSidebar = () => {
        layoutState.configSidebarVisible = !layoutState.configSidebarVisible;
    };

    // 1) Para qué sirve: cerrar menú móvil después de navegar.
    // 2) Cómo funciona: fuerza `mobileMenuActive` a falso.
    // 3) Qué hace: evita que el panel siga abierto tras una acción.
    // 4) Cómo editarla: agrega limpieza extra si sumas overlays adicionales.
    const hideMobileMenu = () => {
        layoutState.mobileMenuActive = false;
    };

    // 1) Para qué sirve: cambiar modo de menú desde selector de UI.
    // 2) Cómo funciona: actualiza modo y reinicia banderas de navegación relacionadas.
    // 3) Qué hace: aplica nuevo comportamiento del sidebar de forma limpia.
    // 4) Cómo editarla: integra persistencia si quieres recordar preferencia del usuario.
    const changeMenuMode = (event) => {
        layoutConfig.menuMode = event.value;
        layoutState.staticMenuInactive = false;
        layoutState.mobileMenuActive = false;
        layoutState.sidebarExpanded = false;
        layoutState.menuHoverActive = false;
        layoutState.anchored = false;
    };

    // 1) Para qué sirve: exponer estado reactivo de tema oscuro para vistas consumidoras.
    // 2) Cómo funciona: computed sobre `layoutConfig.darkTheme`.
    // 3) Qué hace: permite renderizado condicional de íconos/estilos.
    // 4) Cómo editarla: reemplaza fuente si centralizas tema en otro store.
    const isDarkTheme = computed(() => layoutConfig.darkTheme);

    // 1) Para qué sirve: identificar si el viewport actual es desktop.
    // 2) Cómo funciona: compara ancho de ventana con breakpoint.
    // 3) Qué hace: direcciona lógica de menú entre desktop y móvil.
    // 4) Cómo editarla: actualiza el breakpoint cuando cambie la guía responsive.
    const isDesktop = () => window.innerWidth > 991;

    // 1) Para qué sirve: informar si existe overlay abierto.
    // 2) Cómo funciona: computed basado en `overlayMenuActive`.
    // 3) Qué hace: permite bloquear scroll o disparar cierres externos.
    // 4) Cómo editarla: amplía condición si agregas más overlays globales.
    const hasOpenOverlay = computed(() => layoutState.overlayMenuActive);

    return {
        layoutConfig,
        layoutState,
        isDarkTheme,
        toggleDarkMode,
        toggleConfigSidebar,
        toggleMenu,
        hideMobileMenu,
        changeMenuMode,
        isDesktop,
        hasOpenOverlay
    };
}
