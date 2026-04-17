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

// 1) Para qué sirve: refrescar tablero rápido del día contable actual.
// 2) Cómo funciona: consulta endpoint resumen-actual por sucursal del usuario.
// 3) Qué hace: muestra métricas y faltantes recurrentes para control operativo.
// 4) Cómo editarla: agrega filtros adicionales al payload cuando negocio lo requiera.
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

// 1) Para qué sirve: ejecutar cierre de día contable desde dashboard.
// 2) Cómo funciona: confirma acción y llama endpoint cerrar-actual por sucursal.
// 3) Qué hace: bloquea por completo el día para evitar nuevas modificaciones.
// 4) Cómo editarla: integra doble confirmación si se requiere protocolo más estricto.
async function cerrarDiaDesdeDashboard() {
    if (!puedeCerrarDia.value || !sucursalId.value) {
        return;
    }

    const fechaObjetivoCierre = String(resumenDia.value?.fecha_contable || '').trim();
    if (!fechaObjetivoCierre) {
        mensajePantalla.value = 'No se pudo identificar la fecha contable a cerrar. Actualiza el resumen e intenta nuevamente.';
        return;
    }

    const confirmado = window.confirm(`Esta accion cerrara el dia contable ${fechaObjetivoCierre} y bloqueara solo las capturas de ese dia. ¿Deseas continuar?`);
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
        mensajePantalla.value = `Cierre de dia ejecutado correctamente para ${fechaObjetivoCierre}. Solo ese dia contable quedo bloqueado.`;
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
    <section v-if="esContadorOGerente" class="space-y-4">
        <div class="card">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Resumen del dia contable</h1>
                    <p class="text-surface-500 mt-1">Vista rapida de avances para validar si falta captura antes del cierre.</p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <Button icon="pi pi-refresh" label="Actualizar" text :loading="cargandoResumen" @click="cargarResumenDiaContable" />
                    <Button
                        icon="pi pi-lock"
                        label="Cierre de dia"
                        severity="danger"
                        :loading="cerrandoDia"
                        :disabled="!puedeCerrarDia"
                        @click="cerrarDiaDesdeDashboard"
                    />
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
                <small class="text-surface-500">Faltantes recurrentes: {{ resumenDia.conceptos_recurrentes_faltantes || 0 }}</small>
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
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-semibold">Conceptos recurrentes pendientes</h2>
                <Tag :value="`Pendientes: ${resumenDia.conceptos_recurrentes_faltantes || 0}`" severity="warn" />
            </div>
            <div v-if="faltantesVisibles.length" class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div v-for="faltante in faltantesVisibles" :key="faltante.id" class="rounded-lg border border-surface-200 bg-surface-50 px-3 py-2">
                    <p class="font-semibold text-sm">{{ faltante.nombre }}</p>
                    <small class="text-surface-500">{{ faltante.categoria_nombre }} · {{ faltante.tipo }}</small>
                </div>
            </div>
            <small v-else class="text-emerald-700 font-semibold">No hay conceptos recurrentes pendientes en este dia contable.</small>
        </div>
    </section>

    <section v-else class="card border border-dashed border-surface-300 dark:border-surface-700 min-h-[65vh] flex items-center justify-center">
        <div class="text-center max-w-2xl px-4">
            <i class="pi pi-file-edit text-5xl text-primary mb-4"></i>
            <h1 class="text-3xl font-semibold text-surface-900 dark:text-surface-0 mb-3">Panel principal</h1>
            <p class="text-surface-600 dark:text-surface-300">
                Esta pagina esta lista para construir modulos del sistema por perfil de usuario.
            </p>
        </div>
    </section>
</template>

