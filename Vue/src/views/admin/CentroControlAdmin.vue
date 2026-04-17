<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import {
    ejecutarTareaCentroControlAdmin,
    guardarEstadoCentroControlAdmin,
    listarSucursalesAdmin,
    listarTareasCentroControlAdmin,
    obtenerEstadoCentroControlAdmin,
    obtenerSaludServidorCentroControlAdmin
} from '@/service/cabinaArquitecturaServicio';

const cargandoInicial = ref(false);
const guardandoEstado = ref(false);
const cargandoSalud = ref(false);
const refrescandoTodo = ref(false);

const mensajeOperacion = ref('');
const severidadMensajeOperacion = ref('info');

const catalogos = reactive({
    estados: [],
    titulos: [],
    mensajes: [],
    etiquetas: [],
    iconos: [],
    decoradores: [],
    recomendaciones: [],
    plantillas: []
});

const formularioEstado = reactive({
    estado_aplicacion: 'PRODUCCION',
    titulo: '',
    mensaje: '',
    etiqueta: '',
    icono: '',
    decoradores: [],
    recomendaciones: [],
    inicio_actualizacion: null,
    fin_actualizacion: null
});

const seleccionPlantilla = ref(null);
const seleccionTituloPredefinido = ref(null);
const seleccionMensajePredefinido = ref(null);
const seleccionEtiquetaPredefinida = ref(null);

const tareasDisponibles = ref([]);
const ejecutandoTareas = reactive({});
const ejecucionesRecientes = reactive({});

const CLAVE_TODOS_CASINOS = 'TODOS_CASINOS';
const opcionesSucursalesTarea = ref([
    { label: 'Todos los casinos activos', value: CLAVE_TODOS_CASINOS }
]);

const parametrosTareas = reactive({
    fecha_contable: null,
    anio: new Date().getFullYear(),
    mes: new Date().getMonth() + 1,
    sucursal_id: CLAVE_TODOS_CASINOS
});

const saludServidor = ref(null);
let intervaloSaludId = null;

const opcionesMes = [
    { label: '01 - Enero', value: 1 },
    { label: '02 - Febrero', value: 2 },
    { label: '03 - Marzo', value: 3 },
    { label: '04 - Abril', value: 4 },
    { label: '05 - Mayo', value: 5 },
    { label: '06 - Junio', value: 6 },
    { label: '07 - Julio', value: 7 },
    { label: '08 - Agosto', value: 8 },
    { label: '09 - Septiembre', value: 9 },
    { label: '10 - Octubre', value: 10 },
    { label: '11 - Noviembre', value: 11 },
    { label: '12 - Diciembre', value: 12 }
];

const opcionesTitulos = computed(() => catalogos.titulos.map((item) => ({ label: item, value: item })));
const opcionesMensajes = computed(() => catalogos.mensajes.map((item) => ({ label: item, value: item })));
const opcionesEtiquetas = computed(() => catalogos.etiquetas.map((item) => ({ label: item, value: item })));
const opcionesIconos = computed(() => catalogos.iconos.map((item) => ({ label: item, value: item })));
const opcionesPlantillas = computed(() => {
    return catalogos.plantillas.map((plantilla) => ({
        label: plantilla.nombre,
        value: plantilla.clave
    }));
});

const estatusSalud = computed(() => {
    const estado = saludServidor.value?.estado_general;
    if (estado === 'saludable') {
        return { etiqueta: 'Saludable', severidad: 'success' };
    }
    return { etiqueta: 'Atencion', severidad: 'warn' };
});

const resumenSalud = computed(() => {
    const datos = saludServidor.value || {};
    const recursos = datos.recursos || {};
    return {
        cpu: Number(recursos.cpu_porcentaje ?? 0),
        memoria: Number(recursos.memoria_usada_porcentaje ?? 0),
        disco: Number(recursos.disco_usado_porcentaje ?? 0)
    };
});

function mostrarMensaje(texto, severidad = 'info') {
    mensajeOperacion.value = texto;
    severidadMensajeOperacion.value = severidad;
}

function normalizarArreglo(valor) {
    return Array.isArray(valor) ? valor.filter((item) => !!String(item || '').trim()) : [];
}

function parsearFechaHora(valor) {
    if (!valor) {
        return null;
    }
    const fecha = new Date(valor);
    return Number.isNaN(fecha.getTime()) ? null : fecha;
}

function formatearDos(valor) {
    return String(valor).padStart(2, '0');
}

function serializarFechaHoraLocal(fecha) {
    if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) {
        return null;
    }

    return `${fecha.getFullYear()}-${formatearDos(fecha.getMonth() + 1)}-${formatearDos(fecha.getDate())}T${formatearDos(fecha.getHours())}:${formatearDos(fecha.getMinutes())}:${formatearDos(fecha.getSeconds())}`;
}

function aplicarPlantilla(plantilla) {
    if (!plantilla) {
        return;
    }

    formularioEstado.estado_aplicacion = plantilla.estado_aplicacion || 'PRODUCCION';
    formularioEstado.titulo = plantilla.titulo || '';
    formularioEstado.mensaje = plantilla.mensaje || '';
    formularioEstado.etiqueta = plantilla.etiqueta || '';
    formularioEstado.icono = plantilla.icono || '';
    formularioEstado.decoradores = [...normalizarArreglo(plantilla.decoradores)];
    formularioEstado.recomendaciones = [...normalizarArreglo(plantilla.recomendaciones)];

    seleccionTituloPredefinido.value = formularioEstado.titulo;
    seleccionMensajePredefinido.value = formularioEstado.mensaje;
    seleccionEtiquetaPredefinida.value = formularioEstado.etiqueta;
}

function sincronizarCatalogos(dataCatalogos = {}) {
    catalogos.estados = Array.isArray(dataCatalogos.estados) ? dataCatalogos.estados : [];
    catalogos.titulos = Array.isArray(dataCatalogos.titulos) ? dataCatalogos.titulos : [];
    catalogos.mensajes = Array.isArray(dataCatalogos.mensajes) ? dataCatalogos.mensajes : [];
    catalogos.etiquetas = Array.isArray(dataCatalogos.etiquetas) ? dataCatalogos.etiquetas : [];
    catalogos.iconos = Array.isArray(dataCatalogos.iconos) ? dataCatalogos.iconos : [];
    catalogos.decoradores = Array.isArray(dataCatalogos.decoradores) ? dataCatalogos.decoradores : [];
    catalogos.recomendaciones = Array.isArray(dataCatalogos.recomendaciones) ? dataCatalogos.recomendaciones : [];
    catalogos.plantillas = Array.isArray(dataCatalogos.plantillas) ? dataCatalogos.plantillas : [];
}

function hidratarEstado(payload = {}) {
    formularioEstado.estado_aplicacion = payload.estado_aplicacion || 'PRODUCCION';
    formularioEstado.titulo = payload.titulo || '';
    formularioEstado.mensaje = payload.mensaje || '';
    formularioEstado.etiqueta = payload.etiqueta || '';
    formularioEstado.icono = payload.icono || '';
    formularioEstado.decoradores = normalizarArreglo(payload.decoradores);
    formularioEstado.recomendaciones = normalizarArreglo(payload.recomendaciones);
    formularioEstado.inicio_actualizacion = parsearFechaHora(payload.inicio_actualizacion);
    formularioEstado.fin_actualizacion = parsearFechaHora(payload.fin_actualizacion);

    seleccionTituloPredefinido.value = formularioEstado.titulo;
    seleccionMensajePredefinido.value = formularioEstado.mensaje;
    seleccionEtiquetaPredefinida.value = formularioEstado.etiqueta;
}

function obtenerPlantillaSeleccionada() {
    if (!seleccionPlantilla.value) {
        return null;
    }
    return catalogos.plantillas.find((item) => item.clave === seleccionPlantilla.value) || null;
}

async function cargarEstadoCentroControl() {
    const { data } = await obtenerEstadoCentroControlAdmin();
    const payload = data?.data || {};

    sincronizarCatalogos(payload.catalogos || {});
    hidratarEstado(payload);
}

async function cargarTareasCentroControl() {
    const { data } = await listarTareasCentroControlAdmin();
    const payload = data?.data || {};
    tareasDisponibles.value = Array.isArray(payload.tareas) ? payload.tareas : [];
}

async function cargarSucursalesTareas() {
    const { data } = await listarSucursalesAdmin();
    const sucursales = Array.isArray(data?.data) ? data.data : [];
    const sucursalesActivas = sucursales.filter((sucursal) => {
        const estado = String(sucursal?.estado || '').toUpperCase();
        return estado === 'ACTIVO' && !sucursal?.eliminado_en;
    });
    const sucursalesVisibles = sucursalesActivas.length ? sucursalesActivas : sucursales;

    opcionesSucursalesTarea.value = [
        { label: 'Todos los casinos activos', value: CLAVE_TODOS_CASINOS },
        ...sucursalesVisibles.map((sucursal) => ({
            label: `${sucursal?.nombre || 'SIN NOMBRE'} (${sucursal?.clave || 'SIN CLAVE'})`,
            value: Number(sucursal?.id)
        }))
    ];
}

async function cargarSaludServidor() {
    cargandoSalud.value = true;
    try {
        const { data } = await obtenerSaludServidorCentroControlAdmin();
        saludServidor.value = data?.data || null;
    } finally {
        cargandoSalud.value = false;
    }
}

async function cargarInicial() {
    cargandoInicial.value = true;
    try {
        await Promise.all([
            cargarEstadoCentroControl(),
            cargarTareasCentroControl(),
            cargarSucursalesTareas(),
            cargarSaludServidor()
        ]);
        mostrarMensaje('Centro de Control cargado correctamente.', 'success');
    } catch (error) {
        const detalle = error?.response?.data?.message || 'No se pudo cargar la informacion inicial del Centro de Control.';
        mostrarMensaje(detalle, 'error');
    } finally {
        cargandoInicial.value = false;
    }
}

async function recargarTodo() {
    refrescandoTodo.value = true;
    try {
        await cargarInicial();
    } finally {
        refrescandoTodo.value = false;
    }
}

async function guardarEstado() {
    guardandoEstado.value = true;

    try {
        const payload = {
            estado_aplicacion: formularioEstado.estado_aplicacion,
            titulo: String(formularioEstado.titulo || '').trim(),
            mensaje: String(formularioEstado.mensaje || '').trim(),
            etiqueta: String(formularioEstado.etiqueta || '').trim(),
            icono: String(formularioEstado.icono || '').trim(),
            decoradores: normalizarArreglo(formularioEstado.decoradores),
            recomendaciones: normalizarArreglo(formularioEstado.recomendaciones),
            inicio_actualizacion: serializarFechaHoraLocal(formularioEstado.inicio_actualizacion),
            fin_actualizacion: serializarFechaHoraLocal(formularioEstado.fin_actualizacion)
        };

        if (payload.estado_aplicacion === 'PRODUCCION') {
            payload.inicio_actualizacion = null;
            payload.fin_actualizacion = null;
        }

        const { data } = await guardarEstadoCentroControlAdmin(payload);
        const payloadRespuesta = data?.data || {};
        sincronizarCatalogos(payloadRespuesta.catalogos || {});
        hidratarEstado(payloadRespuesta);

        mostrarMensaje('Estado de aplicacion guardado correctamente.', 'success');
    } catch (error) {
        const detalle = error?.response?.data?.message || 'No se pudo guardar el estado de aplicacion.';
        mostrarMensaje(detalle, 'error');
    } finally {
        guardandoEstado.value = false;
    }
}

function construirPayloadTarea(tarea) {
    const payload = { tarea: tarea.clave };

    if (Array.isArray(tarea.parametros) && tarea.parametros.includes('fecha_contable')) {
        const fecha = parametrosTareas.fecha_contable;
        if (fecha instanceof Date && !Number.isNaN(fecha.getTime())) {
            payload.fecha_contable = `${fecha.getFullYear()}-${formatearDos(fecha.getMonth() + 1)}-${formatearDos(fecha.getDate())}`;
        }
    }

    if (Array.isArray(tarea.parametros) && tarea.parametros.includes('anio') && tarea.parametros.includes('mes')) {
        payload.anio = Number(parametrosTareas.anio);
        payload.mes = Number(parametrosTareas.mes);
    }

    if (Array.isArray(tarea.parametros) && tarea.parametros.includes('sucursal_id')) {
        const sucursalSeleccionada = Number(parametrosTareas.sucursal_id);
        if (Number.isInteger(sucursalSeleccionada) && sucursalSeleccionada > 0) {
            payload.sucursal_id = sucursalSeleccionada;
        }
    }

    return payload;
}

function formatearFechaHoraTexto(valorIso) {
    if (!valorIso) {
        return 'Sin fecha';
    }
    const fecha = new Date(valorIso);
    if (Number.isNaN(fecha.getTime())) {
        return String(valorIso);
    }
    return `${fecha.toLocaleDateString()} ${fecha.toLocaleTimeString()}`;
}

async function ejecutarTarea(tarea) {
    ejecutandoTareas[tarea.clave] = true;
    try {
        const payload = construirPayloadTarea(tarea);
        const { data } = await ejecutarTareaCentroControlAdmin(payload);
        const resultado = data?.data || {};

        ejecucionesRecientes[tarea.clave] = {
            task_id: resultado.task_id,
            solicitado_en: resultado.solicitado_en,
            solicitado_por: resultado.solicitado_por
        };

        mostrarMensaje(`Tarea ${tarea.nombre} enviada a Celery correctamente.`, 'success');
    } catch (error) {
        const detalle = error?.response?.data?.message || `No se pudo ejecutar ${tarea.nombre}.`;
        mostrarMensaje(detalle, 'error');
    } finally {
        ejecutandoTareas[tarea.clave] = false;
    }
}

function severidadPorPorcentaje(valor) {
    const numero = Number(valor || 0);
    if (numero >= 85) {
        return 'danger';
    }
    if (numero >= 70) {
        return 'warn';
    }
    return 'success';
}

watch(seleccionPlantilla, () => {
    const plantilla = obtenerPlantillaSeleccionada();
    if (!plantilla) {
        return;
    }
    aplicarPlantilla(plantilla);
});

watch(seleccionTituloPredefinido, (valor) => {
    if (valor) {
        formularioEstado.titulo = valor;
    }
});

watch(seleccionMensajePredefinido, (valor) => {
    if (valor) {
        formularioEstado.mensaje = valor;
    }
});

watch(seleccionEtiquetaPredefinida, (valor) => {
    if (valor) {
        formularioEstado.etiqueta = valor;
    }
});

onMounted(async () => {
    await cargarInicial();

    intervaloSaludId = window.setInterval(() => {
        cargarSaludServidor();
    }, 60000);
});

onBeforeUnmount(() => {
    if (intervaloSaludId) {
        window.clearInterval(intervaloSaludId);
        intervaloSaludId = null;
    }
});
</script>

<template>
    <section class="space-y-6">
        <div class="card border-l-4 border-l-red-500 space-y-4">
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Centro de Control</h1>
                    <p class="text-surface-600 mt-1">Panel exclusivo para ADMINISTRADOR con gestion de estado operativo, tareas Celery y salud del servidor.</p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <Tag :value="estatusSalud.etiqueta" :severity="estatusSalud.severidad" />
                    <Button :loading="refrescandoTodo" icon="pi pi-refresh" label="Recargar todo" severity="secondary" @click="recargarTodo" />
                </div>
            </div>

            <Message v-if="mensajeOperacion" :severity="severidadMensajeOperacion" :closable="false">
                {{ mensajeOperacion }}
            </Message>
        </div>

        <div class="card space-y-5">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 class="text-xl font-semibold">Estado de aplicacion</h2>
                <Tag value="Solo administrador" severity="danger" />
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-th-large mr-1 text-primary"></i>Plantilla rapida <small class="text-surface-500">(opcional)</small></label>
                    <Select
                        v-model="seleccionPlantilla"
                        :options="opcionesPlantillas"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona una plantilla"
                        filter
                        filterPlaceholder="Buscar plantilla..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sliders-h mr-1 text-primary"></i>Estado operativo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select
                        v-model="formularioEstado.estado_aplicacion"
                        :options="catalogos.estados"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona estado"
                        filter
                        filterPlaceholder="Buscar estado..."
                    />
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-bookmark mr-1 text-primary"></i>Titulo predefinido <small class="text-surface-500">(selector)</small></label>
                    <Select
                        v-model="seleccionTituloPredefinido"
                        :options="opcionesTitulos"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona titulo"
                        filter
                        filterPlaceholder="Buscar titulo..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-tag mr-1 text-primary"></i>Etiqueta predefinida <small class="text-surface-500">(selector)</small></label>
                    <Select
                        v-model="seleccionEtiquetaPredefinida"
                        :options="opcionesEtiquetas"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona etiqueta"
                        filter
                        filterPlaceholder="Buscar etiqueta..."
                    />
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-heading mr-1 text-primary"></i>Titulo visible <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioEstado.titulo" class="w-full" placeholder="Ej. Actualizacion de software en progreso" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-star mr-1 text-primary"></i>Etiqueta visible <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioEstado.etiqueta" class="w-full" placeholder="Ej. Intervencion preventiva" />
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-comment mr-1 text-primary"></i>Mensaje predefinido <small class="text-surface-500">(selector)</small></label>
                    <Select
                        v-model="seleccionMensajePredefinido"
                        :options="opcionesMensajes"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona mensaje"
                        filter
                        filterPlaceholder="Buscar mensaje..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-image mr-1 text-primary"></i>Icono <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select
                        v-model="formularioEstado.icono"
                        :options="opcionesIconos"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona icono"
                        filter
                        filterPlaceholder="Buscar icono..."
                    >
                        <template #option="slotProps">
                            <div class="flex items-center gap-2">
                                <i :class="slotProps.option.value"></i>
                                <span>{{ slotProps.option.label }}</span>
                            </div>
                        </template>
                    </Select>
                </div>
            </div>

            <div>
                <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Mensaje visible <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                <Textarea v-model="formularioEstado.mensaje" class="w-full" rows="3" placeholder="Mensaje para usuarios durante mantenimiento" />
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Decoradores visibles <small class="text-surface-500">(seleccion multiple)</small></label>
                    <MultiSelect
                        v-model="formularioEstado.decoradores"
                        :options="catalogos.decoradores"
                        class="w-full"
                        placeholder="Selecciona decoradores"
                        display="chip"
                        filter
                        filterPlaceholder="Buscar decorador..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-check-square mr-1 text-primary"></i>Recomendaciones visibles <small class="text-surface-500">(seleccion multiple)</small></label>
                    <MultiSelect
                        v-model="formularioEstado.recomendaciones"
                        :options="catalogos.recomendaciones"
                        class="w-full"
                        placeholder="Selecciona recomendaciones"
                        display="chip"
                        filter
                        filterPlaceholder="Buscar recomendacion..."
                    />
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-calendar-plus mr-1 text-primary"></i>Inicio actualizacion <small class="text-surface-500">(opcional)</small></label>
                    <DatePicker v-model="formularioEstado.inicio_actualizacion" class="w-full" showTime hourFormat="24" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DD HH:mm:ss" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-calendar-times mr-1 text-primary"></i>Fin actualizacion <small class="text-surface-500">(opcional)</small></label>
                    <DatePicker v-model="formularioEstado.fin_actualizacion" class="w-full" showTime hourFormat="24" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DD HH:mm:ss" />
                </div>
            </div>

            <div class="border border-surface-200 rounded-xl p-4 bg-surface-50">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div class="flex items-center gap-2">
                        <i :class="formularioEstado.icono || 'pi pi-info-circle'"></i>
                        <strong>{{ formularioEstado.titulo || 'Sin titulo' }}</strong>
                    </div>
                    <Tag :value="formularioEstado.etiqueta || 'Sin etiqueta'" severity="contrast" />
                </div>
                <p class="mt-2 text-surface-700">{{ formularioEstado.mensaje || 'Sin mensaje definido.' }}</p>
                <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <small class="font-semibold text-surface-500">Decoradores</small>
                        <ul class="list-disc pl-5 text-sm text-surface-700">
                            <li v-for="decorador in formularioEstado.decoradores" :key="decorador">{{ decorador }}</li>
                            <li v-if="!formularioEstado.decoradores.length" class="text-surface-400">Sin decoradores</li>
                        </ul>
                    </div>
                    <div>
                        <small class="font-semibold text-surface-500">Recomendaciones</small>
                        <ul class="list-disc pl-5 text-sm text-surface-700">
                            <li v-for="recomendacion in formularioEstado.recomendaciones" :key="recomendacion">{{ recomendacion }}</li>
                            <li v-if="!formularioEstado.recomendaciones.length" class="text-surface-400">Sin recomendaciones</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="flex flex-wrap justify-end gap-2">
                <Button :loading="guardandoEstado" icon="pi pi-save" label="Guardar estado" @click="guardarEstado" />
            </div>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 class="text-xl font-semibold">Gatillos manuales de Celery</h2>
                <Tag value="Tareas permitidas" severity="info" />
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-calendar mr-1 text-primary"></i>Fecha contable para resumen <small class="text-surface-500">(opcional)</small></label>
                    <DatePicker v-model="parametrosTareas.fecha_contable" class="w-full" dateFormat="yy-mm-dd" showIcon placeholder="YYYY-MM-DD" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Casino para el envio <small class="text-surface-500">(opcional)</small></label>
                    <Select
                        v-model="parametrosTareas.sucursal_id"
                        :options="opcionesSucursalesTarea"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Todos los casinos activos"
                        filter
                        filterPlaceholder="Buscar casino..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-hashtag mr-1 text-primary"></i>Anio cierre mensual</label>
                    <InputNumber v-model="parametrosTareas.anio" class="w-full" :useGrouping="false" :min="2000" :max="3000" placeholder="Ej. 2026" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-calendar-plus mr-1 text-primary"></i>Mes cierre mensual</label>
                    <Select v-model="parametrosTareas.mes" :options="opcionesMes" optionLabel="label" optionValue="value" class="w-full" filter filterPlaceholder="Buscar mes..." />
                </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                <div v-for="tarea in tareasDisponibles" :key="tarea.clave" class="border border-surface-200 rounded-xl p-4 space-y-3">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <h3 class="font-semibold text-lg">{{ tarea.nombre }}</h3>
                            <p class="text-sm text-surface-600 mt-1">{{ tarea.descripcion }}</p>
                        </div>
                        <Button
                            size="small"
                            icon="pi pi-play"
                            :loading="!!ejecutandoTareas[tarea.clave]"
                            @click="ejecutarTarea(tarea)"
                            label="Ejecutar"
                        />
                    </div>

                    <div class="flex flex-wrap gap-2">
                        <Tag v-for="parametro in tarea.parametros" :key="`${tarea.clave}-${parametro}`" :value="parametro" severity="contrast" />
                        <Tag v-if="!tarea.parametros.length" value="Sin parametros" severity="success" />
                    </div>

                    <Message v-if="ejecucionesRecientes[tarea.clave]" severity="secondary" :closable="false">
                        <div class="text-sm">
                            <div><strong>Task ID:</strong> {{ ejecucionesRecientes[tarea.clave].task_id }}</div>
                            <div><strong>Solicitado por:</strong> {{ ejecucionesRecientes[tarea.clave].solicitado_por }}</div>
                            <div><strong>Fecha:</strong> {{ formatearFechaHoraTexto(ejecucionesRecientes[tarea.clave].solicitado_en) }}</div>
                        </div>
                    </Message>
                </div>
            </div>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 class="text-xl font-semibold">Salud del servidor</h2>
                <Button :loading="cargandoSalud" icon="pi pi-heart" label="Actualizar salud" severity="secondary" @click="cargarSaludServidor" />
            </div>

            <div v-if="cargandoInicial" class="text-surface-500">Cargando metricas del servidor...</div>

            <div v-else-if="saludServidor" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="p-3 rounded-lg border border-surface-200 bg-surface-50">
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-semibold">CPU</span>
                            <Tag :value="`${resumenSalud.cpu.toFixed(2)}%`" :severity="severidadPorPorcentaje(resumenSalud.cpu)" />
                        </div>
                        <ProgressBar :value="resumenSalud.cpu" />
                    </div>

                    <div class="p-3 rounded-lg border border-surface-200 bg-surface-50">
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-semibold">Memoria RAM</span>
                            <Tag :value="`${resumenSalud.memoria.toFixed(2)}%`" :severity="severidadPorPorcentaje(resumenSalud.memoria)" />
                        </div>
                        <ProgressBar :value="resumenSalud.memoria" />
                    </div>

                    <div class="p-3 rounded-lg border border-surface-200 bg-surface-50">
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-semibold">Disco</span>
                            <Tag :value="`${resumenSalud.disco.toFixed(2)}%`" :severity="severidadPorPorcentaje(resumenSalud.disco)" />
                        </div>
                        <ProgressBar :value="resumenSalud.disco" />
                    </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div class="border border-surface-200 rounded-xl p-4">
                        <h3 class="font-semibold mb-2">Servidor</h3>
                        <p><strong>Hostname:</strong> {{ saludServidor.servidor?.hostname || 'N/D' }}</p>
                        <p><strong>Plataforma:</strong> {{ saludServidor.servidor?.plataforma || 'N/D' }}</p>
                        <p><strong>Python:</strong> {{ saludServidor.servidor?.python_version || 'N/D' }}</p>
                        <p><strong>Fecha servidor:</strong> {{ formatearFechaHoraTexto(saludServidor.fecha_hora_servidor) }}</p>
                    </div>

                    <div class="border border-surface-200 rounded-xl p-4 space-y-2">
                        <h3 class="font-semibold">Base de datos y Celery</h3>
                        <div class="flex items-center gap-2">
                            <Tag :value="saludServidor.base_datos?.ok ? 'BD OK' : 'BD con incidencias'" :severity="saludServidor.base_datos?.ok ? 'success' : 'danger'" />
                            <span class="text-sm">Latencia: {{ saludServidor.base_datos?.latencia_ms ?? 'N/D' }} ms</span>
                        </div>
                        <p class="text-sm text-surface-700">{{ saludServidor.base_datos?.mensaje }}</p>
                        <div class="flex items-center gap-2 mt-2">
                            <Tag :value="saludServidor.celery?.ok ? 'Celery en linea' : 'Celery sin respuesta'" :severity="saludServidor.celery?.ok ? 'success' : 'warn'" />
                            <span class="text-sm">Workers: {{ (saludServidor.celery?.workers || []).length }}</span>
                        </div>
                        <p class="text-sm text-surface-700">{{ saludServidor.celery?.mensaje }}</p>
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>
