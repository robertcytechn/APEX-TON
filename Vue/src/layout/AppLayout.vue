<script setup>
import { useLayout } from '@/layout/composables/layout';
import { usePreferenciasUsuarioStore } from '@/stores/preferenciasUsuario';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted } from 'vue';
import AppFooter from './AppFooter.vue';
import AppSidebar from './AppSidebar.vue';
import AppTopbar from './AppTopbar.vue';

const { layoutConfig, layoutState, hideMobileMenu } = useLayout();
const preferenciasUsuarioStore = usePreferenciasUsuarioStore();
const sesionStore = useSesionStore();

const containerClass = computed(() => {
    return {
        'layout-overlay': layoutConfig.menuMode === 'overlay',
        'layout-static': layoutConfig.menuMode === 'static',
        'layout-overlay-active': layoutState.overlayMenuActive,
        'layout-mobile-active': layoutState.mobileMenuActive,
        'layout-static-inactive': layoutState.staticMenuInactive
    };
});

onMounted(async () => {
    if (sesionStore.estaAutenticado) {
        await preferenciasUsuarioStore.cargarConfiguracionUsuario(layoutConfig);
    }
});
</script>

<template>
    <div class="layout-wrapper" :class="containerClass">
        <AppTopbar />
        <AppSidebar />
        <div class="layout-main-container">
            <div class="layout-main">
                <router-view />
            </div>
            <AppFooter />
        </div>
        <div class="layout-mask animate-fadein" @click="hideMobileMenu" />
    </div>
</template>
