<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { crearRolAdmin, eliminarRolAdmin, listarRolesAdmin, actualizarRolAdmin } from '@/service/cabinaArquitecturaServicio';

const cargando = ref(false);
const registros = ref([]);
const mostrarDialogo = ref(false);
const guardando = ref(false);
const editandoId = ref(null);
const columnasDisponibles = [
    { label: 'ID', value: 'id' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Descripcion', value: 'descripcion' }
];
const columnasVisibles = ref([...columnasDisponibles]);
const filasPorPagina = ref(10);

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

// 1) Para qué sirve: validar si una columna debe renderizarse.
// 2) Cómo funciona: revisa la colección actual de columnas visibles.
// 3) Qué hace: habilita personalización de tabla por usuario.
// 4) Cómo editarla: agrega lógica por permisos si quieres ocultar columnas sensibles.
const esColumnaVisible = (columna) => columnasVisibles.value.some((item) => item.value === columna);

const formulario = reactive({
    nombre: '',
    descripcion: ''
});

// 1) Para qué sirve: limpiar formulario y salir de modo edición.
// 2) Cómo funciona: restablece campos y editandoId.
// 3) Qué hace: evita que datos previos se mezclen en nuevas capturas.
// 4) Cómo editarla: agrega campos nuevos del rol para mantener reinicio completo.
const limpiarFormulario = () => {
    formulario.nombre = '';
    formulario.descripcion = '';
    editandoId.value = null;
};

// 1) Para qué sirve: cargar listado de roles desde backend.
// 2) Cómo funciona: consulta servicio y asigna resultado a `registros`.
// 3) Qué hace: refresca información presentada en la tabla.
// 4) Cómo editarla: incorpora filtros o paginación remota según evolución API.
const cargar = async () => {
    cargando.value = true;
    try {
        const { data } = await listarRolesAdmin();
        registros.value = data.data || [];
    } finally {
        cargando.value = false;
    }
};

// 1) Para qué sirve: abrir diálogo para alta de rol.
// 2) Cómo funciona: limpia formulario y muestra modal.
// 3) Qué hace: inicia flujo de captura de un rol nuevo.
// 4) Cómo editarla: agrega valores iniciales predefinidos si se requiere.
const nuevo = () => {
    limpiarFormulario();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: abrir diálogo para edición de rol existente.
// 2) Cómo funciona: copia valores del registro al formulario reactivo.
// 3) Qué hace: habilita modificación directa de nombre/descripcion.
// 4) Cómo editarla: sincroniza aquí cualquier nuevo campo editable del rol.
const editar = (registro) => {
    formulario.nombre = registro.nombre;
    formulario.descripcion = registro.descripcion || '';
    editandoId.value = registro.id;
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: guardar cambios del rol en alta o edición.
// 2) Cómo funciona: decide entre create/update por presencia de editandoId.
// 3) Qué hace: persiste datos y recarga la tabla para mantener consistencia.
// 4) Cómo editarla: agrega validaciones previas o manejo de errores específicos.
const guardar = async () => {
    guardando.value = true;
    try {
        if (editandoId.value) {
            await actualizarRolAdmin(editandoId.value, formulario);
        } else {
            await crearRolAdmin(formulario);
        }
        mostrarDialogo.value = false;
        limpiarFormulario();
        await cargar();
    } finally {
        guardando.value = false;
    }
};

// 1) Para qué sirve: eliminar rol seleccionado.
// 2) Cómo funciona: llama servicio de borrado y refresca lista.
// 3) Qué hace: actualiza la vista quitando el registro eliminado.
// 4) Cómo editarla: inserta confirmación previa antes de ejecutar eliminación.
const eliminar = async (registro) => {
    await eliminarRolAdmin(registro.id);
    await cargar();
};

// 1) Para qué sirve: disparar carga inicial al montar la vista.
// 2) Cómo funciona: invoca `cargar` una vez en ciclo de vida.
// 3) Qué hace: presenta datos desde el primer render.
// 4) Cómo editarla: agrega inicializaciones adicionales si la vista crece.
onMounted(cargar);
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h1 class="text-2xl font-semibold">Roles</h1>
            <Button label="Nuevo rol" icon="pi pi-plus" @click="nuevo" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
                <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                <MultiSelect v-model="columnasVisibles" :options="columnasDisponibles" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opción..." />
            </div>
            <div>
                <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por página</label>
                <Select v-model="filasPorPagina" :options="opcionesFilasMostrar" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
            </div>
        </div>

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
            <Column v-if="esColumnaVisible('id')" field="id" header="ID" sortable />
            <Column v-if="esColumnaVisible('nombre')" field="nombre" header="Nombre" sortable />
            <Column v-if="esColumnaVisible('descripcion')" field="descripcion" header="Descripcion" sortable />
            <Column header="Acciones">
                <template #body="slotProps">
                    <div class="flex gap-2">
                        <Button size="small" icon="pi pi-pencil" severity="info" @click="editar(slotProps.data)" />
                        <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminar(slotProps.data)" />
                    </div>
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar rol' : 'Nuevo rol'" :style="{ width: '32rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-id-card mr-1 text-primary"></i>
                        Nombre <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. ADMINISTRADOR" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-align-left mr-1 text-primary"></i>
                        Descripcion <small class="text-surface-500">(opcional)</small>
                    </label>
                    <Textarea v-model="formulario.descripcion" rows="3" class="w-full" placeholder="Describe las responsabilidades del rol" />
                </div>
                <div class="flex justify-end gap-2">
                    <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                    <Button :loading="guardando" label="Guardar" @click="guardar" />
                </div>
            </div>
        </Dialog>
    </section>
</template>






