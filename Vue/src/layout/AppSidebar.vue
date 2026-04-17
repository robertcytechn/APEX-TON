<script setup>
import { useLayout } from '@/layout/composables/layout';
import { onBeforeUnmount, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import AppMenu from './AppMenu.vue';

const { layoutState, isDesktop, hasOpenOverlay } = useLayout();
const route = useRoute();
const sidebarRef = ref(null);
let outsideClickListener = null;

watch(
    () => route.path,
    (newPath) => {
        if (isDesktop()) layoutState.activePath = null;
        else layoutState.activePath = newPath;

        layoutState.overlayMenuActive = false;
        layoutState.mobileMenuActive = false;
        layoutState.menuHoverActive = false;
    },
    { immediate: true }
);

watch(hasOpenOverlay, (newVal) => {
    if (isDesktop()) {
        if (newVal) bindOutsideClickListener();
        else unbindOutsideClickListener();
    }
});

// 1) Para qué sirve: registrar listener global para cerrar menú al hacer clic fuera.
// 2) Cómo funciona: agrega handler de click sobre document cuando hay overlay abierto.
// 3) Qué hace: mejora UX cerrando sidebar automáticamente fuera de foco.
// 4) Cómo editarla: cambia el evento o estrategia si migras a pointerdown/touchstart.
const bindOutsideClickListener = () => {
    if (!outsideClickListener) {
        outsideClickListener = (event) => {
            if (isOutsideClicked(event)) {
                layoutState.overlayMenuActive = false;
            }
        };

        document.addEventListener('click', outsideClickListener);
    }
};

// 1) Para qué sirve: remover listener global de cierre externo.
// 2) Cómo funciona: elimina el handler y limpia referencia local.
// 3) Qué hace: evita fugas de memoria y cierres no deseados.
// 4) Cómo editarla: mantén este cleanup en cualquier refactor del listener.
const unbindOutsideClickListener = () => {
    if (outsideClickListener) {
        document.removeEventListener('click', outsideClickListener);
        outsideClickListener = null;
    }
};

// 1) Para qué sirve: determinar si un clic ocurrió fuera de sidebar y botón de menú.
// 2) Cómo funciona: compara target contra nodos sidebar y topbar button.
// 3) Qué hace: define condición exacta para cerrar overlay.
// 4) Cómo editarla: amplía la lista de elementos exentos si agregas nuevos disparadores.
const isOutsideClicked = (event) => {
    const topbarButtonEl = document.querySelector('.layout-menu-button');

    return !(sidebarRef.value.isSameNode(event.target) || sidebarRef.value.contains(event.target) || topbarButtonEl?.isSameNode(event.target) || topbarButtonEl?.contains(event.target));
};

// 1) Para qué sirve: limpiar listeners al desmontar el componente.
// 2) Cómo funciona: invoca unbindOutsideClickListener en onBeforeUnmount.
// 3) Qué hace: garantiza cierre correcto del ciclo de vida.
// 4) Cómo editarla: conserva este cleanup si mueves listeners a otro hook.
onBeforeUnmount(() => {
    unbindOutsideClickListener();
});
</script>

<template>
    <div ref="sidebarRef" class="layout-sidebar">
        <AppMenu />
    </div>
</template>
