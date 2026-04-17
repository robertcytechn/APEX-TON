<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    actualizarRubroContableDirector,
    crearRubroContableDirector,
    listarRubrosContablesDirector,
    obtenerOpcionesRubroContableDirector
} from '@/service/cabinaArquitecturaServicio';

const cargando = ref(false);
const guardando = ref(false);
const mostrarDialogo = ref(false);
const editandoId = ref(null);

const rubros = ref([]);
const opcionesPadre = ref([]);
const opcionesTipo = ref([]);

const filasPorPagina = ref(10);
const mensaje = ref('');
const severidadMensaje = ref('info');

const formulario = reactive({
    nombre: '',
    padre: null,
    tipo: 'INGRESO',
    descripcion: ''
});

const opcionesFilas = computed(() => {
    const total = rubros.value.length;
    const opciones = [
        { label: '10', value: 10 },
        { label: '20', value: 20 },
        { label: '50', value: 50 }
    ];
    if (total > 0 && !opciones.some((opcion) => opcion.value === total)) {
        opciones.push({ label: 'Todos', value: total });
    }
    return opciones;
});

const limpiarFormulario = () => {
    formulario.nombre = '';
    formulario.padre = null;
    formulario.tipo = 'INGRESO';
    formulario.descripcion = '';
    editandoId.value = null;
};

const abrirNuevo = () => {
    limpiarFormulario();
    mostrarDialogo.value = true;
};

const abrirEdicion = (registro) => {
    formulario.nombre = registro.nombre || '';
    formulario.padre = registro.padre || registro.padre_info?.id || null;
    formulario.tipo = registro.tipo || 'INGRESO';
    formulario.descripcion = registro.descripcion || '';
    editandoId.value = registro.id;
    mostrarDialogo.value = true;
};

const cargar = async () => {
    cargando.value = true;
    try {
        const [respuestaRubros, respuestaOpciones] = await Promise.all([
            listarRubrosContablesDirector(),
            obtenerOpcionesRubroContableDirector()
        ]);

        rubros.value = respuestaRubros.data.data || [];
        opcionesPadre.value = respuestaOpciones.data.data?.padres || [];
        opcionesTipo.value = respuestaOpciones.data.data?.tipos || [];

        if (!opcionesTipo.value.some((opcion) => opcion.value === formulario.tipo) && opcionesTipo.value.length > 0) {
            formulario.tipo = opcionesTipo.value[0].value;
        }
    } finally {
        cargando.value = false;
    }
};

const guardar = async () => {
    guardando.value = true;
    try {
        const payload = {
            nombre: formulario.nombre,
            padre: formulario.padre,
            tipo: formulario.tipo,
            descripcion: formulario.descripcion
        };

        if (editandoId.value) {
            await actualizarRubroContableDirector(editandoId.value, payload);
            severidadMensaje.value = 'success';
            mensaje.value = 'Rubro contable actualizado correctamente.';
        } else {
            await crearRubroContableDirector(payload);
            severidadMensaje.value = 'success';
            mensaje.value = 'Rubro contable creado correctamente.';
        }

        mostrarDialogo.value = false;
        limpiarFormulario();
        await cargar();
    } finally {
        guardando.value = false;
    }
};

onMounted(cargar);
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Cabina Director: Rubros Contables</h1>
                    <p class="text-sm text-surface-500 mt-1">Cada rubro requiere obligatoriamente un padre y su tipo de movimiento (ingreso o egreso).</p>
                </div>
                <Button label="Nuevo rubro" icon="pi pi-plus" @click="abrirNuevo" />
            </div>

            <Message v-if="mensaje" :severity="severidadMensaje" :closable="false">{{ mensaje }}</Message>

            <DataTable
                :value="rubros"
                :loading="cargando"
                paginator
                :rows="filasPorPagina"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <template #paginatorstart>
                    <Select v-model="filasPorPagina" :options="opcionesFilas" optionLabel="label" optionValue="value" class="w-32" />
                </template>

                <Column field="nombre" header="Rubro" sortable />
                <Column header="Padre" sortable sortField="padre_nombre">
                    <template #body="slotProps">
                        {{ slotProps.data.padre_nombre || slotProps.data.padre_info?.nombre || 'Sin padre' }}
                    </template>
                </Column>
                <Column field="tipo" header="Tipo" sortable>
                    <template #body="slotProps">
                        <Tag
                            :value="slotProps.data.tipo"
                            :severity="slotProps.data.tipo === 'INGRESO' ? 'success' : 'danger'"
                        />
                    </template>
                </Column>
                <Column field="descripcion" header="Descripción" />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <Button size="small" icon="pi pi-pencil" label="Editar" severity="info" @click="abrirEdicion(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar rubro contable' : 'Nuevo rubro contable'" :style="{ width: '42rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-bookmark mr-1 text-primary" />
                        Nombre <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. VENTAS_BEBIDAS" />
                </div>

                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-sitemap mr-1 text-primary" />
                        Padre del rubro <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <Select
                        v-model="formulario.padre"
                        :options="opcionesPadre"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona padre contable"
                        filter
                        filterPlaceholder="Buscar padre..."
                    />
                </div>

                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-tags mr-1 text-primary" />
                        Tipo <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <Select
                        v-model="formulario.tipo"
                        :options="opcionesTipo"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona tipo"
                        filter
                        filterPlaceholder="Buscar tipo..."
                    />
                </div>

                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-align-left mr-1 text-primary" />
                        Descripción <small class="text-surface-500">(opcional)</small>
                    </label>
                    <Textarea v-model="formulario.descripcion" rows="3" class="w-full" placeholder="Describe cuándo aplica este rubro" />
                </div>
            </div>

            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar" icon="pi pi-check" @click="guardar" />
            </div>
        </Dialog>
    </section>
</template>
