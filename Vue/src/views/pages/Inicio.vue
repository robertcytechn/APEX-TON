<script setup>
import { useSesionStore } from '@/stores/sesion';
import { computed } from 'vue';
import InicioAdministrador from './InicioAdministrador.vue';
import InicioDirector from './InicioDirector.vue';
import InicioOperativo from './InicioOperativo.vue';

const sesionStore = useSesionStore();

const esAdministrador = computed(() => sesionStore.cumpleAlgunoRoles(['ADMINISTRADOR', 'SUPERUSUARIO']));
const esDirector = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR']));
const esContadorOGerente = computed(() => sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE']));

const componenteInicio = computed(() => {
    if (esAdministrador.value) {
        return InicioAdministrador;
    }
    if (esDirector.value) {
        return InicioDirector;
    }
    if (esContadorOGerente.value) {
        return InicioOperativo;
    }
    return null;
});
</script>

<template>
    <component :is="componenteInicio" v-if="componenteInicio" />

    <section v-else class="card border border-dashed border-surface-300 dark:border-surface-700 min-h-[45vh] flex items-center justify-center">
        <div class="text-center max-w-xl px-4">
            <i class="pi pi-exclamation-triangle text-4xl text-amber-500 mb-3"></i>
            <h1 class="text-2xl font-semibold mb-2">No fue posible determinar tu panel de inicio</h1>
            <p class="text-surface-600 dark:text-surface-300">
                Tu perfil no tiene un tablero asignado. Solicita al administrador revisar tu rol y permisos.
            </p>
        </div>
    </section>
</template>
