<script setup>
import { computed } from 'vue';

const props = defineProps({
    monto: {
        type: [Number, String],
        default: 0
    },
    moneda: {
        type: String,
        default: '$'
    }
});

const coloresGrupos = ['text-primary-600', 'text-cyan-600', 'text-orange-600', 'text-violet-600', 'text-rose-600'];

const partes = computed(() => {
    const numero = Number(props.monto ?? 0);
    const valorSeguro = Number.isFinite(numero) ? numero : 0;
    const signo = valorSeguro < 0 ? '-' : '';
    const valorFormateado = Math.abs(valorSeguro).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    const [entero, decimales] = valorFormateado.split('.');
    return {
        signo,
        grupos: entero.split(','),
        decimales: decimales || '00'
    };
});
</script>

<template>
    <span class="inline-flex items-baseline font-semibold tracking-tight">
        <span class="text-surface-500 mr-1">{{ moneda }}</span>
        <span v-if="partes.signo" class="text-red-600 mr-1">{{ partes.signo }}</span>
        <template v-for="(grupo, indice) in partes.grupos" :key="`${grupo}-${indice}`">
            <span :class="coloresGrupos[indice % coloresGrupos.length]">{{ grupo }}</span>
            <span v-if="indice < partes.grupos.length - 1" class="text-surface-500">,</span>
        </template>
        <span class="text-emerald-600">.{{ partes.decimales }}</span>
    </span>
</template>
