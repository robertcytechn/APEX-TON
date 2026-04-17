<script setup>
import { listarSucursalesReporte } from '@/service/estadoResultadosServicio';
import { obtenerCalendarioMensualDiasContables } from '@/service/reporteDiarioServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const mensaje = ref('');
const sucursales = ref([]);
const calendario = ref([]);
const diaContableActual = ref('');

const hoy = new Date();
const fechaContablePorDefecto = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);

const filtroSucursalId = ref(sesionStore.usuario?.sucursal_id || null);
const filtroAnio = ref(fechaContablePorDefecto.getFullYear());
const filtroMes = ref(fechaContablePorDefecto.getMonth() + 1);

const puedeVerControlesAvanzados = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));
const sucursalAsignadaId = computed(() => Number(sesionStore.usuario?.sucursal_id || 0));

const nombresMes = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const nombresDiaSemana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

const opcionesMes = nombresMes.map((nombre, indice) => ({ label: nombre, value: indice + 1 }));

const colorTarjetaPorEstado = {
    verde: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    morado: 'bg-fuchsia-50 border-fuchsia-200 text-fuchsia-800',
    azul: 'bg-sky-50 border-sky-200 text-sky-800',
    rojo: 'bg-red-50 border-red-200 text-red-800'
};

const encabezadoCalendario = computed(() => {
    const mesIndice = Number(filtroMes.value || 1) - 1;
    return `${nombresMes[mesIndice] || ''} ${filtroAnio.value}`.trim();
});

const textoMesEnCurso = computed(() => {
    const mesIndice = fechaContablePorDefecto.getMonth();
    return `${nombresMes[mesIndice] || 'Mes actual'} ${fechaContablePorDefecto.getFullYear()}`;
});

const sucursalActual = computed(() => {
    return sucursales.value.find((sucursal) => Number(sucursal.id) === Number(filtroSucursalId.value)) || null;
});

const textoCasinoEnCurso = computed(() => {
    return sucursalActual.value?.nombre || 'Sin casino asignado';
});

// 1) Para qué sirve: construir rejilla semanal con huecos para render del mes.
// 2) Cómo funciona: alinea lunes-domingo, inserta null al inicio y agrupa en semanas de 7.
// 3) Qué hace: permite una vista calendario estable en móvil y escritorio.
// 4) Cómo editarla: ajusta el inicio de semana si negocio cambia la convención regional.
const semanasCalendario = computed(() => {
    if (!Array.isArray(calendario.value) || !calendario.value.length) {
        return [];
    }

    const primerDiaMes = new Date(filtroAnio.value, filtroMes.value - 1, 1);
    const indiceLunesDomingo = (primerDiaMes.getDay() + 6) % 7;

    const celdas = [];
    for (let i = 0; i < indiceLunesDomingo; i += 1) {
        celdas.push(null);
    }

    for (const dia of calendario.value) {
        celdas.push(dia);
    }

    const semanas = [];
    for (let i = 0; i < celdas.length; i += 7) {
        semanas.push(celdas.slice(i, i + 7));
    }
    return semanas;
});

const resumenEstados = computed(() => {
    const resumen = {
        verde: 0,
        morado: 0,
        azul: 0,
        rojo: 0,
    };

    for (const dia of calendario.value) {
        const color = dia?.color;
        if (Object.prototype.hasOwnProperty.call(resumen, color)) {
            resumen[color] += 1;
        }
    }

    return resumen;
});

// 1) Para qué sirve: cargar catálogo de sucursales activas para filtros del calendario.
// 2) Cómo funciona: consume endpoint de sucursales y ordena por nombre.
// 3) Qué hace: habilita selección de casino para el tablero mensual.
// 4) Cómo editarla: añade filtros por rol cuando backend exponga permisos por sucursal.
const cargarSucursales = async () => {
    const { data } = await listarSucursalesReporte();
    const listado = Array.isArray(data?.data) ? data.data : [];
    sucursales.value = listado
        .filter((sucursal) => sucursal.estado === 'ACTIVO')
        .sort((a, b) => (a.nombre || '').localeCompare(b.nombre || '', 'es-MX'));

    if (!puedeVerControlesAvanzados.value) {
        filtroSucursalId.value = sucursalAsignadaId.value || null;
        return;
    }

    if (!filtroSucursalId.value && sucursales.value.length) {
        filtroSucursalId.value = sucursales.value[0].id;
    }
};

// 1) Para qué sirve: consultar estados de días contables del mes seleccionado.
// 2) Cómo funciona: envía sucursal, año y mes al endpoint de calendario mensual.
// 3) Qué hace: alimenta el tablero de colores y la leyenda operativa.
// 4) Cómo editarla: integra paginación por rango si el backend ofrece periodos largos.
const consultarCalendario = async () => {
    mensaje.value = '';
    calendario.value = [];
    diaContableActual.value = '';

    if (!puedeVerControlesAvanzados.value) {
        filtroSucursalId.value = sucursalAsignadaId.value || null;
        filtroAnio.value = fechaContablePorDefecto.getFullYear();
        filtroMes.value = fechaContablePorDefecto.getMonth() + 1;
    }

    if (!filtroSucursalId.value) {
        mensaje.value = puedeVerControlesAvanzados.value
            ? 'Selecciona un casino para consultar los días contables.'
            : 'Tu usuario no tiene un casino asignado. Solicita apoyo al administrador.';
        return;
    }

    cargando.value = true;
    try {
        const { data } = await obtenerCalendarioMensualDiasContables({
            sucursal_id: filtroSucursalId.value,
            anio: filtroAnio.value,
            mes: filtroMes.value
        });

        calendario.value = Array.isArray(data?.data?.dias) ? data.data.dias : [];
        diaContableActual.value = data?.data?.dia_contable_actual || '';

        if (!calendario.value.length) {
            mensaje.value = 'No hay información para el mes seleccionado.';
        }
    } catch (error) {
        mensaje.value = error?.response?.data?.message || 'No fue posible consultar el calendario de días contables.';
    } finally {
        cargando.value = false;
    }
};

onMounted(async () => {
    await cargarSucursales();
    await consultarCalendario();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card space-y-4">
            <div>
                <h1 class="text-2xl font-semibold">Días contables</h1>
                <p class="text-surface-500 mt-1">Calendario mensual del estatus operativo de captura por casino.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div v-if="puedeVerControlesAvanzados">
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Casino <span class="text-red-500">*</span></label>
                    <Select
                        v-model="filtroSucursalId"
                        :options="sucursales"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Selecciona casino"
                        filter
                        filterPlaceholder="Buscar opción..."
                        @change="consultarCalendario"
                    />
                </div>

                <div v-else>
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Casino visible</label>
                    <div class="w-full rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-surface-700 font-semibold">
                        {{ textoCasinoEnCurso }}
                    </div>
                </div>

                <template v-if="puedeVerControlesAvanzados">
                    <div>
                        <label class="block text-sm mb-2"><i class="pi pi-calendar mr-1 text-primary"></i>Mes <span class="text-red-500">*</span></label>
                        <Select
                            v-model="filtroMes"
                            :options="opcionesMes"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Selecciona mes"
                            filter
                            filterPlaceholder="Buscar opción..."
                        />
                    </div>

                    <div>
                        <label class="block text-sm mb-2"><i class="pi pi-hashtag mr-1 text-primary"></i>Año <span class="text-red-500">*</span></label>
                        <InputNumber v-model="filtroAnio" :useGrouping="false" :min="2020" :max="2100" class="w-full" placeholder="2026" />
                    </div>

                    <div class="flex items-end">
                        <Button icon="pi pi-search" label="Consultar calendario" class="w-full" :loading="cargando" @click="consultarCalendario" />
                    </div>
                </template>

                <div v-else class="md:col-span-3">
                    <label class="block text-sm mb-2"><i class="pi pi-calendar-clock mr-1 text-primary"></i>Periodo visible</label>
                    <div class="w-full rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-surface-700 font-semibold">
                        Mes en curso: {{ textoMesEnCurso }}
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                    <small class="text-emerald-700">Verde</small>
                    <p class="font-semibold">{{ resumenEstados.verde }} días</p>
                </div>
                <div class="rounded-xl border border-fuchsia-200 bg-fuchsia-50 p-3">
                    <small class="text-fuchsia-700">Morado</small>
                    <p class="font-semibold">{{ resumenEstados.morado }} días</p>
                </div>
                <div class="rounded-xl border border-sky-200 bg-sky-50 p-3">
                    <small class="text-sky-700">Azul</small>
                    <p class="font-semibold">{{ resumenEstados.azul }} días</p>
                </div>
                <div class="rounded-xl border border-red-200 bg-red-50 p-3">
                    <small class="text-red-700">Rojo</small>
                    <p class="font-semibold">{{ resumenEstados.rojo }} días</p>
                </div>
            </div>

            <small v-if="diaContableActual" class="text-surface-500 block">Día contable actual del sistema: {{ diaContableActual }}</small>
        </div>

        <Message v-if="mensaje" severity="warn" :closable="false">{{ mensaje }}</Message>

        <div class="card space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold">{{ encabezadoCalendario }}</h2>
            </div>

            <div class="grid grid-cols-7 gap-2">
                <div v-for="nombre in nombresDiaSemana" :key="nombre" class="text-center text-xs font-semibold text-surface-500 uppercase tracking-wide">
                    {{ nombre }}
                </div>
            </div>

            <div class="space-y-2">
                <div v-for="(semana, indiceSemana) in semanasCalendario" :key="`semana-${indiceSemana}`" class="grid grid-cols-7 gap-2">
                    <div
                        v-for="(dia, indiceDia) in semana"
                        :key="`dia-${indiceSemana}-${indiceDia}-${dia?.fecha_contable || 'vacio'}`"
                        class="min-h-24 rounded-xl border p-2"
                        :class="dia ? colorTarjetaPorEstado[dia.color] || 'bg-surface-50 border-surface-200 text-surface-700' : 'bg-transparent border-dashed border-surface-200'"
                    >
                        <template v-if="dia">
                            <div class="flex items-start justify-between gap-2">
                                <span class="text-sm font-bold">{{ dia.dia }}</span>
                                <Tag :severity="dia.editable ? 'success' : 'secondary'" :value="dia.editable ? 'Editable' : 'Bloqueado'" />
                            </div>
                            <p class="mt-2 text-xs font-medium">{{ dia.mensaje_estado }}</p>
                            <p class="mt-1 text-[11px]">{{ dia.fecha_contable }}</p>
                        </template>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3 class="text-lg font-semibold mb-3">Leyenda operativa</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">Verde: llenado en tiempo correcto o día actual disponible.</div>
                <div class="rounded-lg border border-fuchsia-200 bg-fuchsia-50 px-3 py-2">Morado: llenado tardío o día pasado que sigue abierto.</div>
                <div class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2">Azul: día futuro, no capturable.</div>
                <div class="rounded-lg border border-red-200 bg-red-50 px-3 py-2">Rojo: día pasado sin captura o cerrado por antigüedad mayor a 5 días.</div>
            </div>
        </div>
    </section>
</template>
