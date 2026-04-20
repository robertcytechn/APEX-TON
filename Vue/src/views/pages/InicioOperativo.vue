<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { cerrarDiaContableActual, obtenerResumenDiaContableActual } from '@/service/reporteDiarioServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargandoResumen = ref(false);
const cerrandoDia = ref(false);
const resumenDia = ref(null);
const mensajePantalla = ref('');

const esContadorOGerente = computed(() => sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE']));
const sucursalId = computed(() => Number(sesionStore.usuario?.sucursal_id || 0));

const faltantesVisibles = computed(() => {
    return Array.isArray(resumenDia.value?.faltantes_recurrentes) ? resumenDia.value.faltantes_recurrentes.slice(0, 12) : [];
});

const puedeCerrarDia = computed(() => Boolean(resumenDia.value?.puede_cerrar_dia));

const claseResultadoNeto = computed(() => {
    const neto = Number(resumenDia.value?.resultado_neto_capturado || 0);
    if (neto > 0) return 'text-emerald-700';
    if (neto < 0) return 'text-red-700';
    return 'text-surface-700';
});

async function cargarResumenDiaContable() {
    if (!esContadorOGerente.value) {
        return;
    }

    if (!sucursalId.value) {
        mensajePantalla.value = 'Tu usuario no tiene casino asignado. Solicita apoyo al administrador.';
        resumenDia.value = null;
        return;
    }

    cargandoResumen.value = true;
    mensajePantalla.value = '';

    try {
        const { data } = await obtenerResumenDiaContableActual({ sucursal_id: sucursalId.value });
        resumenDia.value = data?.data || null;
    } catch (error) {
        resumenDia.value = null;
        mensajePantalla.value = error?.response?.data?.message || 'No se pudo obtener el resumen del día contable.';
    } finally {
        cargandoResumen.value = false;
    }
}

async function cerrarDiaDesdeDashboard() {
    if (!puedeCerrarDia.value || !sucursalId.value) {
        return;
    }

    const fechaObjetivoCierre = String(resumenDia.value?.fecha_contable || '').trim();
    if (!fechaObjetivoCierre) {
        mensajePantalla.value = 'No se pudo identificar la fecha contable a cerrar. Actualiza el resumen e intenta nuevamente.';
        return;
    }

    const confirmado = window.confirm(`Esta acción cerrará el día contable ${fechaObjetivoCierre} y bloqueará solo las capturas de ese día. ¿Deseas continuar?`);
    if (!confirmado) {
        return;
    }

    cerrandoDia.value = true;
    mensajePantalla.value = '';

    try {
        await cerrarDiaContableActual({
            sucursal_id: sucursalId.value,
            fecha_contable: fechaObjetivoCierre,
        });
        mensajePantalla.value = `Cierre de día ejecutado correctamente para ${fechaObjetivoCierre}. Solo ese día contable quedó bloqueado.`;
        await cargarResumenDiaContable();
    } catch (error) {
        mensajePantalla.value = error?.response?.data?.message || 'No se pudo completar el cierre de día.';
    } finally {
        cerrandoDia.value = false;
    }
}

onMounted(async () => {
    await cargarResumenDiaContable();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card border border-surface-200/80 dark:border-surface-700/80 overflow-hidden">
            <div class="rounded-xl p-5 sm:p-6 bg-[linear-gradient(120deg,#0f172a_0%,#1e3a8a_45%,#0f766e_100%)] text-white">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <small class="uppercase tracking-widest text-white/80">Operación diaria</small>
                        <h1 class="text-2xl sm:text-3xl font-semibold mt-2">Resumen del día contable</h1>
                        <p class="text-white/85 mt-2">Consulte el estado de captura y ejecute el cierre diario una vez completado el registro de movimientos.</p>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <Button icon="pi pi-refresh" label="Actualizar" severity="contrast" outlined :loading="cargandoResumen" @click="cargarResumenDiaContable" />
                        <Button
                            icon="pi pi-lock"
                            label="Cierre de día"
                            severity="danger"
                            :loading="cerrandoDia"
                            :disabled="!puedeCerrarDia"
                            @click="cerrarDiaDesdeDashboard"
                        />
                    </div>
                </div>
            </div>
        </div>

        <Message v-if="mensajePantalla" severity="warn" :closable="false">{{ mensajePantalla }}</Message>

        <div v-if="resumenDia" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="card">
                <small class="text-surface-500">Fecha contable</small>
                <p class="font-semibold text-lg mt-1">{{ resumenDia.fecha_contable }}</p>
                <Tag class="mt-2" :severity="resumenDia.estado_reporte === 'CERRADO' ? 'danger' : 'success'" :value="resumenDia.estado_reporte" />
            </div>
            <div class="card">
                <small class="text-surface-500">Movimientos registrados</small>
                <p class="font-semibold text-2xl mt-1">{{ resumenDia.movimientos_registrados || 0 }}</p>
                <small class="text-surface-500">Conceptos recurrentes sin capturar: {{ resumenDia.conceptos_recurrentes_faltantes || 0 }}</small>
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Ingresos capturados</small>
                <MontoMonedaColoreado :monto="resumenDia.ingresos_capturados || 0" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Egresos capturados</small>
                <MontoMonedaColoreado :monto="resumenDia.egresos_capturados || 0" />
            </div>
        </div>

        <div v-if="resumenDia" class="card">
            <div class="flex items-center justify-between">
                <small class="text-surface-500">Resultado neto capturado</small>
                <span class="text-sm font-semibold" :class="claseResultadoNeto">Estado de avance</span>
            </div>
            <div class="mt-2">
                <MontoMonedaColoreado :monto="resumenDia.resultado_neto_capturado || 0" />
            </div>
        </div>

        <div v-if="resumenDia" class="card space-y-3">
            <div class="flex items-center justify-between gap-2">
                <h2 class="text-lg font-semibold">Conceptos recurrentes pendientes</h2>
                <Tag :value="`Pendientes: ${resumenDia.conceptos_recurrentes_faltantes || 0}`" severity="warn" />
            </div>
            <div v-if="faltantesVisibles.length" class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div v-for="faltante in faltantesVisibles" :key="faltante.id" class="rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 dark:border-surface-700 dark:bg-surface-800/70">
                    <p class="font-semibold text-sm">{{ faltante.nombre }}</p>
                    <small class="text-surface-500">{{ faltante.categoria_nombre }} · {{ faltante.tipo }}</small>
                </div>
            </div>
            <small v-else class="text-emerald-700 font-semibold">Todos los conceptos recurrentes han sido registrados correctamente para este día contable.</small>
        </div>
    </section>
</template>
