<script setup>
import ComponenteGraficas from 'vue3-apexcharts';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import {
    listarSucursalesAdmin,
    listarUsuariosAdmin,
    obtenerEstadoCentroControlAdmin
} from '@/service/cabinaArquitecturaServicio';
import { obtenerEstadisticasOperativas } from '@/service/estadoResultadosServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const mensajeError = ref('');
const estadisticas = ref(null);
const usuarios = ref([]);
const sucursales = ref([]);
const estadoCentroControl = ref(null);

const puedeVer = computed(() => sesionStore.cumpleAlgunoRoles(['ADMINISTRADOR', 'SUPERUSUARIO']));

const resumenGeneral = computed(() => estadisticas.value?.resumen_general || {});
const seriePorSucursal = computed(() => {
    const lista = Array.isArray(estadisticas.value?.series?.por_sucursal) ? estadisticas.value.series.por_sucursal : [];
    return [...lista]
        .map((item) => ({
            ...item,
            ingresos: Number(item?.ingresos || 0),
            egresos: Number(item?.egresos || 0),
            neto: Number(item?.neto || 0),
            movimientos: Number(item?.movimientos || 0)
        }))
        .sort((a, b) => Number(b.neto || 0) - Number(a.neto || 0));
});

const totalUsuarios = computed(() => usuarios.value.length);
const usuariosActivos = computed(() => usuarios.value.filter((item) => Boolean(item?.is_active)).length);
const totalSucursales = computed(() => sucursales.value.length);
const sucursalesActivas = computed(() => {
    return sucursales.value.filter((item) => String(item?.estado || '').toUpperCase() === 'ACTIVO').length;
});

const totalIngresos = computed(() => Number(resumenGeneral.value?.total_ingresos || 0));
const totalEgresos = computed(() => Number(resumenGeneral.value?.total_egresos || 0));
const resultadoNeto = computed(() => Number(resumenGeneral.value?.resultado_neto || 0));
const totalMovimientos = computed(() => Number(resumenGeneral.value?.total_movimientos || 0));

const etiquetaEstadoApp = computed(() => {
    const estado = String(estadoCentroControl.value?.estado_aplicacion || '').toUpperCase();
    if (estado === 'MANTENIMIENTO') {
        return { texto: 'Mantenimiento', severidad: 'warn' };
    }
    return { texto: 'Producción', severidad: 'success' };
});

const serieGraficaNetoSucursales = computed(() => {
    return [{
        name: 'Neto por casino',
        data: seriePorSucursal.value.slice(0, 8).map((item) => Number(item.neto || 0))
    }];
});

const opcionesGraficaNetoSucursales = computed(() => {
    return {
        chart: {
            toolbar: { show: false },
            fontFamily: 'Georgia, Cambria, serif'
        },
        colors: ['#0f766e'],
        plotOptions: {
            bar: {
                horizontal: true,
                borderRadius: 6
            }
        },
        dataLabels: {
            enabled: true,
            formatter: (valor) => formatearMonedaCompacta(valor)
        },
        xaxis: {
            categories: seriePorSucursal.value.slice(0, 8).map((item) => item.sucursal_nombre || 'Sin nombre')
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

function obtenerRangoPredeterminado() {
    const hoy = new Date();
    const fechaFin = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);
    const fechaInicio = new Date(fechaFin.getFullYear(), 0, 1);

    return {
        fecha_inicio: aFechaIso(fechaInicio),
        fecha_fin: aFechaIso(fechaFin)
    };
}

function obtenerMensajeErrorCarga(error, fallback) {
    return error?.response?.data?.message || error?.message || fallback;
}

async function cargarInicioAdministrador() {
    if (!puedeVer.value) {
        return;
    }

    cargando.value = true;
    mensajeError.value = '';

    try {
        const rango = obtenerRangoPredeterminado();

        const [resEstadisticas, resUsuarios, resSucursales, resCentroControl] = await Promise.allSettled([
            obtenerEstadisticasOperativas({
                fecha_inicio: rango.fecha_inicio,
                fecha_fin: rango.fecha_fin
            }),
            listarUsuariosAdmin(),
            listarSucursalesAdmin(),
            obtenerEstadoCentroControlAdmin()
        ]);
        const errores = [];

        if (resEstadisticas.status === 'fulfilled') {
            estadisticas.value = resEstadisticas.value?.data?.data || null;
        } else {
            estadisticas.value = null;
            errores.push(`Estadísticas: ${obtenerMensajeErrorCarga(resEstadisticas.reason, 'sin respuesta')}`);
        }

        if (resUsuarios.status === 'fulfilled') {
            usuarios.value = Array.isArray(resUsuarios.value?.data?.data) ? resUsuarios.value.data.data : [];
        } else {
            usuarios.value = [];
            errores.push(`Usuarios: ${obtenerMensajeErrorCarga(resUsuarios.reason, 'sin respuesta')}`);
        }

        if (resSucursales.status === 'fulfilled') {
            sucursales.value = Array.isArray(resSucursales.value?.data?.data) ? resSucursales.value.data.data : [];
        } else {
            sucursales.value = [];
            errores.push(`Sucursales: ${obtenerMensajeErrorCarga(resSucursales.reason, 'sin respuesta')}`);
        }

        if (resCentroControl.status === 'fulfilled') {
            estadoCentroControl.value = resCentroControl.value?.data?.data || null;
        } else {
            estadoCentroControl.value = null;
            errores.push(`Centro de control: ${obtenerMensajeErrorCarga(resCentroControl.reason, 'sin respuesta')}`);
        }

        if (errores.length === 0) {
            mensajeError.value = '';
        } else if (errores.length === 4) {
            mensajeError.value = 'No se pudo cargar el panel administrativo. El servidor no respondió a los módulos principales.';
        } else {
            mensajeError.value = `Carga parcial completada. Revisar módulos con incidencia: ${errores.join(' | ')}`;
        }
    } catch {
        mensajeError.value = 'No se pudo cargar el panel administrativo.';
    } finally {
        cargando.value = false;
    }
}

onMounted(async () => {
    await cargarInicioAdministrador();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card border border-surface-200/80 dark:border-surface-700/80 overflow-hidden">
            <div class="rounded-xl p-5 sm:p-6 bg-[linear-gradient(120deg,#3f1d6b_0%,#0f172a_45%,#0f766e_100%)] text-white">
                <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
                    <div>
                        <small class="uppercase tracking-widest text-white/80">Administrador</small>
                        <h1 class="text-2xl sm:text-3xl font-semibold mt-2">Modo Dios · Centro de mando</h1>
                        <p class="text-white/85 mt-2">Control total de operación, seguridad, catálogos y salud general de la aplicación.</p>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                        <Tag :value="`Estado app: ${etiquetaEstadoApp.texto}`" :severity="etiquetaEstadoApp.severidad" />
                        <Button icon="pi pi-refresh" label="Actualizar" severity="contrast" outlined :loading="cargando" @click="cargarInicioAdministrador" />
                    </div>
                </div>
            </div>
        </div>

        <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>

        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="card">
                <small class="text-surface-500">Usuarios activos</small>
                <p class="text-2xl font-semibold mt-1">{{ usuariosActivos }} / {{ totalUsuarios }}</p>
            </div>
            <div class="card">
                <small class="text-surface-500">Casinos activos</small>
                <p class="text-2xl font-semibold mt-1">{{ sucursalesActivas }} / {{ totalSucursales }}</p>
            </div>
            <div class="card">
                <small class="text-surface-500">Ingresos acumulados del año</small>
                <div class="mt-1"><MontoMonedaColoreado :monto="totalIngresos" /></div>
            </div>
            <div class="card">
                <small class="text-surface-500">Neto acumulado del año</small>
                <div class="mt-1"><MontoMonedaColoreado :monto="resultadoNeto" /></div>
            </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div class="card xl:col-span-2">
                <div class="flex items-center justify-between gap-2 mb-3">
                    <h2 class="text-lg font-semibold">Top casinos por neto</h2>
                    <Tag value="Año en curso" severity="info" />
                </div>
                <ComponenteGraficas
                    v-if="seriePorSucursal.length"
                    type="bar"
                    height="330"
                    :options="opcionesGraficaNetoSucursales"
                    :series="serieGraficaNetoSucursales"
                />
                <Message v-else severity="warn" :closable="false">No hay datos suficientes para graficar casinos.</Message>
            </div>

            <div class="card space-y-3">
                <h2 class="text-lg font-semibold">Acciones rápidas</h2>
                <router-link to="/admin/centro-control" class="block rounded-lg border border-surface-200 dark:border-surface-700 p-3 hover:border-primary transition-colors">
                    <p class="font-semibold">Centro de control</p>
                    <small class="text-surface-500">Estado de aplicación, tareas y salud de servidor.</small>
                </router-link>
                <router-link to="/admin/usuarios" class="block rounded-lg border border-surface-200 dark:border-surface-700 p-3 hover:border-primary transition-colors">
                    <p class="font-semibold">Gestión de usuarios</p>
                    <small class="text-surface-500">Altas, bajas, roles y control de accesos.</small>
                </router-link>
                <router-link to="/admin/sucursales" class="block rounded-lg border border-surface-200 dark:border-surface-700 p-3 hover:border-primary transition-colors">
                    <p class="font-semibold">Gestión de sucursales</p>
                    <small class="text-surface-500">Casinos, fondos fijos y operación territorial.</small>
                </router-link>
                <router-link to="/admin/catalogo-operativo" class="block rounded-lg border border-surface-200 dark:border-surface-700 p-3 hover:border-primary transition-colors">
                    <p class="font-semibold">Catálogo operativo</p>
                    <small class="text-surface-500">Categorías, conceptos y reglas contables.</small>
                </router-link>
            </div>
        </div>

        <div class="card">
            <div class="flex flex-wrap items-center gap-4">
                <Tag :value="`Movimientos analizados: ${totalMovimientos.toLocaleString('es-MX')}`" severity="contrast" />
                <Tag :value="`Egresos del año: ${formatearMoneda(totalEgresos)}`" severity="danger" />
                <Tag :value="`Ingresos del año: ${formatearMoneda(totalIngresos)}`" severity="success" />
            </div>
        </div>
    </section>
</template>
