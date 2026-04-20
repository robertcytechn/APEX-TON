<script setup>
import ComponenteGraficas from 'vue3-apexcharts';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { obtenerEstadisticasOperativas } from '@/service/estadoResultadosServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();
const LIMITE_CASINOS_GRAFICA = 20;
const LIMITE_PUNTOS_FLUJO = 180;

const cargando = ref(false);
const mensajeError = ref('');
const datos = ref(null);
const periodo = ref('YTD');

const opcionesPeriodo = [
    { label: 'Año en curso (hasta ayer)', value: 'YTD' },
    { label: 'Últimos 365 días', value: '365' },
    { label: 'Últimos 90 días', value: '90' },
    { label: 'Últimos 30 días', value: '30' },
    { label: 'Histórico 5 años', value: 'HISTORICO' }
];

const puedeVer = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));
const resumen = computed(() => datos.value?.resumen_general || {});
const series = computed(() => datos.value?.series || {});
const filtrosAplicados = computed(() => datos.value?.filtros_aplicados || {});

const recaudadoPorCasino = computed(() => {
    const lista = Array.isArray(series.value?.por_sucursal) ? series.value.por_sucursal : [];
    return [...lista]
        .map((item) => ({
            ...item,
            ingresos: Number(item?.ingresos || 0),
            egresos: Number(item?.egresos || 0),
            neto: Number(item?.neto || 0),
            movimientos: Number(item?.movimientos || 0)
        }))
        .sort((a, b) => Number(b.ingresos || 0) - Number(a.ingresos || 0));
});

    const recaudadoPorCasinoGrafica = computed(() => recaudadoPorCasino.value.slice(0, LIMITE_CASINOS_GRAFICA));

const flujoPorDia = computed(() => {
    return Array.isArray(series.value?.por_dia)
        ? series.value.por_dia.map((item) => ({
            ...item,
            ingresos: Number(item?.ingresos || 0),
            egresos: Number(item?.egresos || 0),
            neto: Number(item?.neto || 0)
        }))
        : [];
});

const flujoPorDiaGrafica = computed(() => {
    if (flujoPorDia.value.length <= LIMITE_PUNTOS_FLUJO) {
        return flujoPorDia.value;
    }

    const paso = Math.ceil(flujoPorDia.value.length / LIMITE_PUNTOS_FLUJO);
    return flujoPorDia.value.filter((_, indice) => {
        const esUltimo = indice === flujoPorDia.value.length - 1;
        return esUltimo || indice % paso === 0;
    });
});

const avisoMuestreoFlujo = computed(() => flujoPorDia.value.length > flujoPorDiaGrafica.value.length);

const totalCasinos = computed(() => recaudadoPorCasino.value.length);
const totalMovimientos = computed(() => Number(resumen.value?.total_movimientos || 0));
const totalRecaudado = computed(() => recaudadoPorCasino.value.reduce((acumulado, item) => acumulado + Number(item.ingresos || 0), 0));
const totalEgresado = computed(() => recaudadoPorCasino.value.reduce((acumulado, item) => acumulado + Number(item.egresos || 0), 0));
const netoGeneral = computed(() => totalRecaudado.value - totalEgresado.value);

const etiquetaPeriodo = computed(() => {
    const inicio = String(filtrosAplicados.value?.fecha_inicio || '').trim();
    const fin = String(filtrosAplicados.value?.fecha_fin || '').trim();
    if (!inicio || !fin) {
        return 'Sin período aplicado';
    }
    return `${formatearFecha(inicio)} al ${formatearFecha(fin)}`;
});

const serieGraficaRecaudado = computed(() => {
    return [{
        name: 'Recaudado',
        data: recaudadoPorCasinoGrafica.value.map((item) => Number(item.ingresos || 0))
    }];
});

const opcionesGraficaRecaudado = computed(() => {
    return {
        chart: {
            toolbar: { show: false },
            fontFamily: 'Georgia, Cambria, serif'
        },
        colors: ['#0f766e'],
        plotOptions: {
            bar: {
                borderRadius: 6,
                distributed: false
            }
        },
        dataLabels: { enabled: false },
        xaxis: {
            categories: recaudadoPorCasinoGrafica.value.map((item) => item.sucursal_nombre || 'Sin nombre')
        },
        yaxis: {
            labels: {
                formatter: (valor) => formatearMonedaCompacta(valor)
            }
        },
        tooltip: {
            y: {
                formatter: (valor) => formatearMoneda(valor)
            }
        },
        grid: {
            borderColor: '#dbe3ef'
        }
    };
});

const serieGraficaFlujo = computed(() => {
    return [
        {
            name: 'Ingresos',
            data: flujoPorDiaGrafica.value.map((item) => Number(item.ingresos || 0))
        },
        {
            name: 'Egresos',
            data: flujoPorDiaGrafica.value.map((item) => Number(item.egresos || 0))
        }
    ];
});

const opcionesGraficaFlujo = computed(() => {
    return {
        chart: {
            toolbar: { show: false },
            fontFamily: 'Georgia, Cambria, serif'
        },
        colors: ['#1d4ed8', '#dc2626'],
        stroke: {
            curve: 'smooth',
            width: 3
        },
        dataLabels: { enabled: false },
        xaxis: {
            categories: flujoPorDiaGrafica.value.map((item) => formatearFechaCorta(item.fecha))
        },
        yaxis: {
            labels: {
                formatter: (valor) => formatearMonedaCompacta(valor)
            }
        },
        tooltip: {
            y: {
                formatter: (valor) => formatearMoneda(valor)
            }
        },
        grid: {
            borderColor: '#dbe3ef'
        }
    };
});

function formatearFecha(fechaIso) {
    if (!fechaIso) return '-';
    const fecha = new Date(`${fechaIso}T00:00:00`);
    if (Number.isNaN(fecha.getTime())) return fechaIso;
    return fecha.toLocaleDateString('es-MX', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function formatearFechaCorta(fechaIso) {
    if (!fechaIso) return '-';
    const fecha = new Date(`${fechaIso}T00:00:00`);
    if (Number.isNaN(fecha.getTime())) return fechaIso;
    return fecha.toLocaleDateString('es-MX', {
        day: '2-digit',
        month: 'short'
    });
}

function formatearMoneda(valor) {
    const monto = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN',
        maximumFractionDigits: 2
    }).format(Number.isFinite(monto) ? monto : 0);
}

function formatearMonedaCompacta(valor) {
    const monto = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(Number.isFinite(monto) ? monto : 0);
}

function aFechaIso(fecha) {
    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

function construirRango() {
    const hoy = new Date();
    const fechaMaxima = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);

    if (periodo.value === 'YTD') {
        const fechaInicioAnual = new Date(fechaMaxima.getFullYear(), 0, 1);
        return {
            fecha_inicio: aFechaIso(fechaInicioAnual),
            fecha_fin: aFechaIso(fechaMaxima)
        };
    }

    if (periodo.value === 'HISTORICO') {
        const fechaInicioHistorica = new Date(fechaMaxima);
        fechaInicioHistorica.setDate(fechaInicioHistorica.getDate() - (365 * 5));
        return {
            fecha_inicio: aFechaIso(fechaInicioHistorica),
            fecha_fin: aFechaIso(fechaMaxima)
        };
    }

    const dias = Number(periodo.value || 30);
    const fechaInicio = new Date(fechaMaxima);
    fechaInicio.setDate(fechaInicio.getDate() - (dias - 1));

    return {
        fecha_inicio: aFechaIso(fechaInicio),
        fecha_fin: aFechaIso(fechaMaxima)
    };
}

async function cargarTableroDirector() {
    if (!puedeVer.value) {
        return;
    }

    cargando.value = true;
    mensajeError.value = '';

    try {
        const rango = construirRango();
        const { data } = await obtenerEstadisticasOperativas({
            fecha_inicio: rango.fecha_inicio,
            fecha_fin: rango.fecha_fin
        });
        datos.value = data?.data || null;
    } catch (error) {
        datos.value = null;
        mensajeError.value = error?.response?.data?.message || error?.message || 'No fue posible cargar el tablero directivo.';
    } finally {
        cargando.value = false;
    }
}

onMounted(async () => {
    await cargarTableroDirector();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card border border-surface-200/80 dark:border-surface-700/80 overflow-hidden">
            <div class="rounded-xl p-5 sm:p-6 bg-[linear-gradient(120deg,#172554_0%,#0f766e_55%,#155e75_100%)] text-white">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
                    <div>
                        <small class="uppercase tracking-widest text-white/80">Dirección general</small>
                        <h1 class="text-2xl sm:text-3xl font-semibold mt-2">Tablero ejecutivo por casino</h1>
                        <p class="text-white/85 mt-2">Seguimiento de recaudación acumulada y comportamiento operativo de todas las salas.</p>
                    </div>
                    <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                        <Select
                            v-model="periodo"
                            :options="opcionesPeriodo"
                            option-label="label"
                            option-value="value"
                            class="min-w-56"
                            @change="cargarTableroDirector"
                        />
                        <Button icon="pi pi-refresh" label="Actualizar" severity="contrast" outlined :loading="cargando" @click="cargarTableroDirector" />
                    </div>
                </div>
                <small class="block mt-3 text-white/75">Período activo: {{ etiquetaPeriodo }}</small>
            </div>
        </div>

        <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="card">
                <small class="text-surface-500">Casinos con operación</small>
                <p class="text-2xl font-semibold mt-1">{{ totalCasinos }}</p>
            </div>
            <div class="card">
                <small class="text-surface-500">Movimientos acumulados</small>
                <p class="text-2xl font-semibold mt-1">{{ totalMovimientos.toLocaleString('es-MX') }}</p>
            </div>
            <div class="card">
                <small class="text-surface-500">Recaudado hasta la fecha</small>
                <div class="mt-1"><MontoMonedaColoreado :monto="totalRecaudado" /></div>
            </div>
            <div class="card">
                <small class="text-surface-500">Resultado neto acumulado</small>
                <div class="mt-1"><MontoMonedaColoreado :monto="netoGeneral" /></div>
            </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div class="card xl:col-span-2">
                <div class="flex items-center justify-between gap-2 mb-3">
                    <h2 class="text-lg font-semibold">Recaudado por casino</h2>
                    <Tag value="Acumulado" severity="info" />
                </div>
                <ComponenteGraficas
                    v-if="recaudadoPorCasinoGrafica.length"
                    type="bar"
                    height="340"
                    :options="opcionesGraficaRecaudado"
                    :series="serieGraficaRecaudado"
                />
                <small v-if="recaudadoPorCasino.length > recaudadoPorCasinoGrafica.length" class="text-surface-500">
                    Mostrando top {{ recaudadoPorCasinoGrafica.length }} casinos por recaudación para optimizar rendimiento visual.
                </small>
                <Message v-else severity="warn" :closable="false">No hay movimientos para construir la gráfica de recaudación.</Message>
            </div>

            <div class="card">
                <h2 class="text-lg font-semibold mb-3">Ranking de recaudación</h2>
                <div class="space-y-2 max-h-[340px] overflow-auto pr-1">
                    <div
                        v-for="(casino, indice) in recaudadoPorCasino"
                        :key="casino.sucursal_id"
                        class="rounded-lg border border-surface-200 dark:border-surface-700 p-3"
                    >
                        <div class="flex items-center justify-between gap-2">
                            <p class="font-semibold text-sm">{{ indice + 1 }}. {{ casino.sucursal_nombre }}</p>
                            <Tag :value="`${casino.movimientos} mov.`" severity="contrast" />
                        </div>
                        <div class="mt-2">
                            <small class="text-surface-500">Recaudado</small>
                            <MontoMonedaColoreado :monto="casino.ingresos" />
                        </div>
                        <small class="text-surface-500">Egresos: {{ formatearMoneda(casino.egresos) }} · Neto: {{ formatearMoneda(casino.neto) }}</small>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="flex items-center justify-between gap-2 mb-3">
                <h2 class="text-lg font-semibold">Tendencia diaria de ingresos y egresos</h2>
                <Tag value="Serie temporal" severity="secondary" />
            </div>
            <ComponenteGraficas
                v-if="flujoPorDiaGrafica.length"
                type="line"
                height="320"
                :options="opcionesGraficaFlujo"
                :series="serieGraficaFlujo"
            />
            <small v-if="avisoMuestreoFlujo" class="text-surface-500">
                La gráfica usa muestreo para mantener fluidez; los totales del tablero consideran el período completo.
            </small>
            <Message v-else severity="warn" :closable="false">No hay datos diarios disponibles para este período.</Message>
        </div>
    </section>
</template>
