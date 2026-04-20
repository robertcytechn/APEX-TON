<script setup>
import { actualizarEventoSoporteTecnico, listarEventosSoporteTecnico } from '@/service/soporteTecnicoServicio';
import { computed, onMounted, reactive, ref } from 'vue';

const cargando = ref(false);
const guardando = ref(false);
const eventos = ref([]);
const mensajeExito = ref('');
const mensajeError = ref('');

const filtroEstado = ref('');
const filtroBusqueda = ref('');

const mostrarDialogoSeguimiento = ref(false);
const eventoSeleccionado = ref(null);

const formularioSeguimiento = reactive({
    estado_seguimiento: 'NUEVO',
    notas_seguimiento: ''
});

const opcionesEstado = [
    { label: 'Todos', value: '' },
    { label: 'Nuevo', value: 'NUEVO' },
    { label: 'En proceso', value: 'EN_PROCESO' },
    { label: 'Completado', value: 'COMPLETADO' },
    { label: 'Descartado', value: 'DESCARTADO' }
];

const opcionesEstadoSeguimiento = opcionesEstado.filter((item) => item.value);

const totalEventos = computed(() => eventos.value.length);
const totalPendientes = computed(() => eventos.value.filter((item) => item.estado_seguimiento !== 'COMPLETADO').length);

function resolverEtiquetaEstado(codigo) {
    const opcion = opcionesEstado.find((item) => item.value === codigo);
    return opcion?.label || codigo || 'Sin estado';
}

function resolverSeveridadEstado(codigo) {
    if (codigo === 'COMPLETADO') return 'success';
    if (codigo === 'EN_PROCESO') return 'warn';
    if (codigo === 'DESCARTADO') return 'secondary';
    return 'info';
}

function resolverSeveridadPrioridad(codigo) {
    if (codigo === 'CRITICA' || codigo === 'ALTA') return 'danger';
    if (codigo === 'MEDIA') return 'warn';
    return 'info';
}

function formatoFecha(fechaIso) {
    if (!fechaIso) {
        return '-';
    }

    const fecha = new Date(fechaIso);
    if (Number.isNaN(fecha.getTime())) {
        return fechaIso;
    }

    return fecha.toLocaleString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatoLista(valor) {
    if (Array.isArray(valor)) {
        return valor.join(', ');
    }
    return String(valor || '').trim() || '-';
}

async function cargarEventosSoporte() {
    cargando.value = true;
    mensajeError.value = '';
    try {
        const params = {};
        if (filtroEstado.value) {
            params.estado_seguimiento = filtroEstado.value;
        }

        const busqueda = String(filtroBusqueda.value || '').trim();
        if (busqueda) {
            params.busqueda = busqueda;
        }

        const { data } = await listarEventosSoporteTecnico(params);
        eventos.value = Array.isArray(data?.data) ? data.data : [];
    } catch (error) {
        eventos.value = [];
        mensajeError.value = error?.response?.data?.message || 'No se pudieron cargar los eventos de soporte técnico.';
    } finally {
        cargando.value = false;
    }
}

function abrirSeguimiento(evento) {
    eventoSeleccionado.value = evento;
    formularioSeguimiento.estado_seguimiento = evento?.estado_seguimiento || 'NUEVO';
    formularioSeguimiento.notas_seguimiento = evento?.notas_seguimiento || '';
    mostrarDialogoSeguimiento.value = true;
}

async function guardarSeguimiento() {
    if (!eventoSeleccionado.value?.id || guardando.value) {
        return;
    }

    guardando.value = true;
    mensajeExito.value = '';
    mensajeError.value = '';

    try {
        const payload = {
            estado_seguimiento: formularioSeguimiento.estado_seguimiento,
            notas_seguimiento: formularioSeguimiento.notas_seguimiento
        };

        const { data } = await actualizarEventoSoporteTecnico(eventoSeleccionado.value.id, payload);
        const eventoActualizado = data?.data || null;

        if (eventoActualizado?.id) {
            eventos.value = eventos.value.map((evento) => (evento.id === eventoActualizado.id ? eventoActualizado : evento));
            eventoSeleccionado.value = eventoActualizado;
        }

        mostrarDialogoSeguimiento.value = false;
        mensajeExito.value = data?.message || 'Ticket de soporte actualizado correctamente.';
    } catch (error) {
        mensajeError.value = error?.response?.data?.message || 'No se pudo actualizar el ticket de soporte.';
    } finally {
        guardando.value = false;
    }
}

onMounted(async () => {
    await cargarEventosSoporte();
});
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
                <h1 class="text-2xl font-semibold">Eventos de Soporte Técnico</h1>
                <small class="text-surface-500">Bandeja administrativa para seguimiento y cierre de tickets.</small>
            </div>
            <div class="flex items-center gap-2">
                <Tag :value="`Total: ${totalEventos}`" severity="info" />
                <Tag :value="`Pendientes: ${totalPendientes}`" severity="warn" />
                <Button label="Actualizar" icon="pi pi-refresh" :loading="cargando" @click="cargarEventosSoporte" />
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
                <label class="block text-sm mb-2">Buscar ticket</label>
                <InputText
                    v-model="filtroBusqueda"
                    class="w-full"
                    placeholder="Folio, usuario, correo o problema"
                    @keyup.enter="cargarEventosSoporte"
                />
            </div>
            <div>
                <label class="block text-sm mb-2">Estado</label>
                <Select
                    v-model="filtroEstado"
                    :options="opcionesEstado"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full"
                    placeholder="Filtrar estado"
                    @change="cargarEventosSoporte"
                />
            </div>
        </div>

        <Message v-if="mensajeExito" severity="success" :closable="true" @close="mensajeExito = ''">{{ mensajeExito }}</Message>
        <Message v-if="mensajeError" severity="error" :closable="true" @close="mensajeError = ''">{{ mensajeError }}</Message>

        <DataTable
            :value="eventos"
            :loading="cargando"
            paginator
            :rows="10"
            responsiveLayout="scroll"
            reorderableColumns
            resizableColumns
            columnResizeMode="fit"
            sortMode="multiple"
            removableSort
        >
            <Column field="folio" header="Folio" sortable />
            <Column header="Fecha" sortable sortField="creado_en">
                <template #body="slotProps">
                    {{ formatoFecha(slotProps.data.creado_en) }}
                </template>
            </Column>
            <Column header="Solicitante">
                <template #body="slotProps">
                    <div class="space-y-1">
                        <p class="font-semibold text-sm">{{ slotProps.data.usuario_nombre || '-' }}</p>
                        <small class="text-surface-500">{{ slotProps.data.usuario_correo || 'Sin correo' }}</small>
                    </div>
                </template>
            </Column>
            <Column header="Problema">
                <template #body="slotProps">
                    <div class="space-y-1">
                        <p class="font-semibold text-sm">{{ slotProps.data.problema_principal_etiqueta || '-' }}</p>
                        <small class="text-surface-500">Página: {{ slotProps.data.pagina_afectada || 'No especificada' }}</small>
                    </div>
                </template>
            </Column>
            <Column header="Prioridad" sortable sortField="prioridad">
                <template #body="slotProps">
                    <Tag
                        :value="slotProps.data.prioridad_etiqueta || slotProps.data.prioridad"
                        :severity="resolverSeveridadPrioridad(slotProps.data.prioridad)"
                    />
                </template>
            </Column>
            <Column header="Estado" sortable sortField="estado_seguimiento">
                <template #body="slotProps">
                    <Tag
                        :value="resolverEtiquetaEstado(slotProps.data.estado_seguimiento)"
                        :severity="resolverSeveridadEstado(slotProps.data.estado_seguimiento)"
                    />
                </template>
            </Column>
            <Column header="Acciones">
                <template #body="slotProps">
                    <Button
                        size="small"
                        icon="pi pi-eye"
                        label="Gestionar"
                        severity="contrast"
                        @click="abrirSeguimiento(slotProps.data)"
                    />
                </template>
            </Column>
        </DataTable>

        <Dialog
            v-model:visible="mostrarDialogoSeguimiento"
            modal
            header="Detalle y seguimiento del ticket"
            :style="{ width: '56rem' }"
        >
            <div v-if="eventoSeleccionado" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm mb-1">Folio</label>
                        <InputText :modelValue="eventoSeleccionado.folio" class="w-full" readonly />
                    </div>
                    <div>
                        <label class="block text-sm mb-1">Solicitante</label>
                        <InputText :modelValue="eventoSeleccionado.usuario_nombre" class="w-full" readonly />
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm mb-1">Áreas afectadas</label>
                        <InputText :modelValue="formatoLista(eventoSeleccionado.areas_afectadas_etiquetas)" class="w-full" readonly />
                    </div>
                    <div>
                        <label class="block text-sm mb-1">Comportamiento observado</label>
                        <InputText :modelValue="eventoSeleccionado.comportamiento_observado_etiqueta" class="w-full" readonly />
                    </div>
                </div>

                <div>
                    <label class="block text-sm mb-1">Descripción detallada</label>
                    <Textarea :modelValue="eventoSeleccionado.descripcion_detallada" rows="4" class="w-full" readonly />
                </div>

                <div>
                    <label class="block text-sm mb-1">Pasos para reproducir</label>
                    <Textarea :modelValue="eventoSeleccionado.pasos_reproduccion || 'No especificados'" rows="3" class="w-full" readonly />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm mb-1">Estado de seguimiento</label>
                        <Select
                            v-model="formularioSeguimiento.estado_seguimiento"
                            :options="opcionesEstadoSeguimiento"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                        />
                    </div>
                    <div>
                        <label class="block text-sm mb-1">Atendido por</label>
                        <InputText :modelValue="eventoSeleccionado.atendido_por_nombre || 'Sin asignar'" class="w-full" readonly />
                    </div>
                </div>

                <div>
                    <label class="block text-sm mb-1">Notas de seguimiento</label>
                    <Textarea
                        v-model="formularioSeguimiento.notas_seguimiento"
                        rows="4"
                        class="w-full"
                        placeholder="Describe acciones realizadas y acuerdos de cierre"
                    />
                </div>

                <div class="flex justify-end gap-2 mt-4">
                    <Button label="Cancelar" severity="secondary" @click="mostrarDialogoSeguimiento = false" />
                    <Button label="Guardar seguimiento" icon="pi pi-check" :loading="guardando" @click="guardarSeguimiento" />
                </div>
            </div>
        </Dialog>
    </section>
</template>
