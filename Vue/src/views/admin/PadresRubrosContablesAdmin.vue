<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    actualizarPadreRubroContableAdmin,
    crearPadreRubroContableAdmin,
    eliminarPadreRubroContableAdmin,
    listarPadresRubrosContablesAdmin
} from '@/service/cabinaArquitecturaServicio';

const cargando = ref(false);
const guardando = ref(false);
const registros = ref([]);
const mostrarDialogo = ref(false);
const editandoId = ref(null);
const filasPorPagina = ref(10);
const mensajeError = ref('');
const mensajeExito = ref('');
const mensajeErrorFormulario = ref('');

const opcionesFilasMostrar = computed(() => {
    const total = registros.value.length;
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

const opcionesConsiderar = [
    { label: 'Si, considerar en estado de resultados', value: true },
    { label: 'No considerar en estado de resultados', value: false }
];

const formulario = reactive({
    clave: '',
    nombre: '',
    descripcion: '',
    considerar_en_estado_resultados: true
});

const limpiarFormulario = () => {
    formulario.clave = '';
    formulario.nombre = '';
    formulario.descripcion = '';
    formulario.considerar_en_estado_resultados = true;
    editandoId.value = null;
    mensajeErrorFormulario.value = '';
};

const normalizarClave = (valor) => {
    return String(valor || '')
        .trim()
        .toUpperCase()
        .replace(/\s+/g, '_');
};

const normalizarNombre = (valor) => String(valor || '').trim();

const validarFormulario = () => {
    const clave = normalizarClave(formulario.clave);
    const nombre = normalizarNombre(formulario.nombre);

    if (!clave) {
        mensajeErrorFormulario.value = 'La clave es obligatoria.';
        return false;
    }

    if (!nombre) {
        mensajeErrorFormulario.value = 'El nombre es obligatorio.';
        return false;
    }

    formulario.clave = clave;
    formulario.nombre = nombre;
    formulario.descripcion = String(formulario.descripcion || '').trim();
    mensajeErrorFormulario.value = '';
    return true;
};

const cargar = async () => {
    cargando.value = true;
    mensajeError.value = '';
    try {
        const respuesta = await listarPadresRubrosContablesAdmin();
        registros.value = respuesta.data.data || [];
    } catch (error) {
        mensajeError.value = error?.response?.data?.message || 'No se pudieron cargar los padres de rubros contables.';
    } finally {
        cargando.value = false;
    }
};

const nuevo = () => {
    limpiarFormulario();
    mostrarDialogo.value = true;
};

const editar = (registro) => {
    formulario.clave = registro.clave || '';
    formulario.nombre = registro.nombre || '';
    formulario.descripcion = registro.descripcion || '';
    formulario.considerar_en_estado_resultados = Boolean(registro.considerar_en_estado_resultados);
    editandoId.value = registro.id;
    mostrarDialogo.value = true;
};

const guardar = async () => {
    if (!validarFormulario()) {
        return;
    }

    guardando.value = true;
    try {
        mensajeError.value = '';
        mensajeExito.value = '';
        const payload = {
            clave: formulario.clave,
            nombre: formulario.nombre,
            descripcion: formulario.descripcion,
            considerar_en_estado_resultados: formulario.considerar_en_estado_resultados
        };

        if (editandoId.value) {
            await actualizarPadreRubroContableAdmin(editandoId.value, payload);
        } else {
            await crearPadreRubroContableAdmin(payload);
        }

        mostrarDialogo.value = false;
        mensajeExito.value = editandoId.value ? 'Padre actualizado correctamente.' : 'Padre creado correctamente.';
        limpiarFormulario();
        await cargar();
    } catch (error) {
        mensajeErrorFormulario.value = error?.response?.data?.message || 'No se pudo guardar el padre de rubro.';
    } finally {
        guardando.value = false;
    }
};

const eliminar = async (registro) => {
    const confirmado = window.confirm(`¿Seguro que deseas eliminar el padre "${registro.nombre}"?`);
    if (!confirmado) {
        return;
    }

    try {
        mensajeError.value = '';
        mensajeExito.value = '';
        await eliminarPadreRubroContableAdmin(registro.id);
        mensajeExito.value = 'Padre eliminado correctamente.';
        await cargar();
    } catch (error) {
        mensajeError.value = error?.response?.data?.message || 'No se pudo eliminar el padre seleccionado.';
    }
};

onMounted(cargar);
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h1 class="text-2xl font-semibold">Padres de Rubros Contables</h1>
            <Button label="Nuevo padre" icon="pi pi-plus" @click="nuevo" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
                <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por página</label>
                <Select v-model="filasPorPagina" :options="opcionesFilasMostrar" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
            </div>
        </div>

        <Message v-if="mensajeExito" severity="success" :closable="true" @close="mensajeExito = ''">{{ mensajeExito }}</Message>
        <Message v-if="mensajeError" severity="error" :closable="true" @close="mensajeError = ''">{{ mensajeError }}</Message>

        <DataTable
            :value="registros"
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
            <Column field="id" header="ID" sortable />
            <Column field="clave" header="Clave" sortable />
            <Column field="nombre" header="Nombre" sortable />
            <Column field="descripcion" header="Descripcion" />
            <Column header="Considerar en ER" sortable sortField="considerar_en_estado_resultados">
                <template #body="slotProps">
                    <Tag
                        :value="slotProps.data.considerar_en_estado_resultados ? 'Si' : 'No'"
                        :severity="slotProps.data.considerar_en_estado_resultados ? 'success' : 'warning'"
                    />
                </template>
            </Column>
            <Column header="Acciones">
                <template #body="slotProps">
                    <div class="flex gap-2">
                        <Button size="small" icon="pi pi-pencil" severity="info" @click="editar(slotProps.data)" />
                        <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminar(slotProps.data)" />
                    </div>
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar padre' : 'Nuevo padre'" :style="{ width: '40rem' }">
            <div class="space-y-4">
                <Message v-if="mensajeErrorFormulario" severity="error" :closable="false">{{ mensajeErrorFormulario }}</Message>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-key mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formulario.clave" class="w-full" placeholder="Ej. CARGAR_FISCALES" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-tag mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. Cargas Fiscales" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-calculator mr-1 text-primary"></i>Participacion en estado de resultados <span class="text-red-500">*</span></label>
                    <Select
                        v-model="formulario.considerar_en_estado_resultados"
                        :options="opcionesConsiderar"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona comportamiento"
                        filter
                        filterPlaceholder="Buscar opción..."
                    />
                    <small class="text-surface-500 block mt-1">
                        Si seleccionas "No considerar", este padre se mostrará en el reporte pero no afectará los totales generales.
                    </small>
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formulario.descripcion" rows="3" class="w-full" placeholder="Describe el objetivo de este padre" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar" @click="guardar" />
            </div>
        </Dialog>
    </section>
</template>

