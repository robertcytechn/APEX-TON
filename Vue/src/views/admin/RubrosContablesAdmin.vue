<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    actualizarPadreRubroContableAdmin,
    crearRubroContableAdmin,
    crearPadreRubroContableAdmin,
    eliminarRubroContableAdmin,
    eliminarPadreRubroContableAdmin,
    listarPadresRubrosContablesAdmin,
    listarRubrosContablesAdmin,
    obtenerOpcionesRubroContableAdmin,
    actualizarRubroContableAdmin
} from '@/service/cabinaArquitecturaServicio';

const opcionesPadre = ref([]);
const opcionesTipo = ref([]);
const padresRegistros = ref([]);

const cargando = ref(false);
const guardando = ref(false);
const guardandoPadre = ref(false);
const registros = ref([]);
const mostrarDialogo = ref(false);
const mostrarDialogoPadre = ref(false);
const editandoId = ref(null);
const editandoPadreId = ref(null);
const columnasDisponibles = [
    { label: 'ID', value: 'id' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Padre', value: 'padre' },
    { label: 'Tipo', value: 'tipo' }
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

// 1) Para qué sirve: decidir visibilidad de columnas en la tabla de rubros.
// 2) Cómo funciona: valida si la columna está seleccionada en columnasVisibles.
// 3) Qué hace: permite personalizar la vista del catálogo.
// 4) Cómo editarla: incorpora restricciones por rol para columnas sensibles.
const esColumnaVisible = (columna) => columnasVisibles.value.some((item) => item.value === columna);

const formulario = reactive({
    nombre: '',
    padre: null,
    tipo: 'INGRESO',
    descripcion: ''
});

const formularioPadre = reactive({
    clave: '',
    nombre: '',
    descripcion: ''
});

// 1) Para qué sirve: resetear formulario a valores por defecto.
// 2) Cómo funciona: limpia campos y sale de modo edición.
// 3) Qué hace: evita mezcla de datos entre operaciones.
// 4) Cómo editarla: agrega limpieza para cualquier campo nuevo del rubro.
const limpiarFormulario = () => {
    formulario.nombre = '';
    formulario.padre = null;
    formulario.tipo = 'INGRESO';
    formulario.descripcion = '';
    editandoId.value = null;
};

const limpiarFormularioPadre = () => {
    formularioPadre.clave = '';
    formularioPadre.nombre = '';
    formularioPadre.descripcion = '';
    editandoPadreId.value = null;
};

// 1) Para qué sirve: cargar catálogo de rubros y opciones de select.
// 2) Cómo funciona: consulta en paralelo listado principal y metadatos de padres/tipos.
// 3) Qué hace: prepara tabla y controles del formulario.
// 4) Cómo editarla: agrega mapeos si backend cambia estructura de opciones.
const cargar = async () => {
    cargando.value = true;
    try {
        const [respuestaRubros, respuestaOpciones] = await Promise.all([
            listarRubrosContablesAdmin(),
            obtenerOpcionesRubroContableAdmin()
        ]);

        registros.value = respuestaRubros.data.data || [];
        opcionesPadre.value = respuestaOpciones.data.data?.padres || [];
        opcionesTipo.value = respuestaOpciones.data.data?.tipos || [];
        const respuestaPadres = await listarPadresRubrosContablesAdmin();
        padresRegistros.value = respuestaPadres.data.data || [];

        if (!opcionesPadre.value.some((opcion) => Number(opcion.value) === Number(formulario.padre)) && opcionesPadre.value.length > 0) {
            formulario.padre = opcionesPadre.value[0].value;
        }

        if (!opcionesTipo.value.some((opcion) => opcion.value === formulario.tipo) && opcionesTipo.value.length > 0) {
            formulario.tipo = opcionesTipo.value[0].value;
        }
    } finally {
        cargando.value = false;
    }
};

// 1) Para qué sirve: abrir diálogo para crear rubro contable.
// 2) Cómo funciona: limpia formulario y activa modal.
// 3) Qué hace: inicia captura de nuevo rubro.
// 4) Cómo editarla: precarga valores preferidos según política contable.
const nuevo = () => {
    limpiarFormulario();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: abrir diálogo para editar rubro existente.
// 2) Cómo funciona: mapea datos del registro al formulario.
// 3) Qué hace: habilita actualización de padre/tipo/descripcion.
// 4) Cómo editarla: incluye nuevos campos del modelo cuando se agreguen.
const editar = (registro) => {
    formulario.nombre = registro.nombre || '';
    formulario.padre = registro.padre || registro.padre_info?.id || null;
    formulario.tipo = registro.tipo || 'INGRESO';
    formulario.descripcion = registro.descripcion || '';
    editandoId.value = registro.id;
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: guardar alta o edición de rubro.
// 2) Cómo funciona: selecciona create/update por editandoId y recarga tabla.
// 3) Qué hace: persiste cambios y refresca estado visual.
// 4) Cómo editarla: agrega validaciones client-side previas al envío.
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
            await actualizarRubroContableAdmin(editandoId.value, payload);
        } else {
            await crearRubroContableAdmin(payload);
        }
        mostrarDialogo.value = false;
        limpiarFormulario();
        await cargar();
    } finally {
        guardando.value = false;
    }
};

// 1) Para qué sirve: eliminar rubro seleccionado del catálogo.
// 2) Cómo funciona: invoca servicio de borrado y recarga información.
// 3) Qué hace: actualiza de inmediato el listado visible.
// 4) Cómo editarla: agrega confirmación previa para evitar borrados accidentales.
const eliminar = async (registro) => {
    await eliminarRubroContableAdmin(registro.id);
    await cargar();
};

const nuevoPadre = () => {
    limpiarFormularioPadre();
    mostrarDialogoPadre.value = true;
};

const editarPadre = (registro) => {
    formularioPadre.clave = registro.clave || '';
    formularioPadre.nombre = registro.nombre || '';
    formularioPadre.descripcion = registro.descripcion || '';
    editandoPadreId.value = registro.id;
    mostrarDialogoPadre.value = true;
};

const guardarPadre = async () => {
    guardandoPadre.value = true;
    try {
        const payload = {
            clave: formularioPadre.clave,
            nombre: formularioPadre.nombre,
            descripcion: formularioPadre.descripcion
        };

        if (editandoPadreId.value) {
            await actualizarPadreRubroContableAdmin(editandoPadreId.value, payload);
        } else {
            await crearPadreRubroContableAdmin(payload);
        }

        mostrarDialogoPadre.value = false;
        limpiarFormularioPadre();
        await cargar();
    } finally {
        guardandoPadre.value = false;
    }
};

const eliminarPadre = async (registro) => {
    await eliminarPadreRubroContableAdmin(registro.id);
    await cargar();
};

// 1) Para qué sirve: cargar datos iniciales cuando abre la vista.
// 2) Cómo funciona: ejecuta `cargar` en ciclo de vida onMounted.
// 3) Qué hace: garantiza tabla y selects listos desde el inicio.
// 4) Cómo editarla: incluye cargas extra si se amplía el módulo.
onMounted(cargar);
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h1 class="text-2xl font-semibold">Rubros Contables</h1>
            <div class="flex flex-col sm:flex-row gap-2">
                <Button label="Nuevo padre" icon="pi pi-plus" severity="help" @click="nuevoPadre" />
                <Button label="Nuevo rubro" icon="pi pi-plus" @click="nuevo" />
            </div>
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
            <Column v-if="esColumnaVisible('padre')" header="Padre" sortable sortField="padre_nombre">
                <template #body="slotProps">
                    {{ slotProps.data.padre_nombre || slotProps.data.padre_info?.nombre || 'Sin padre' }}
                </template>
            </Column>
            <Column v-if="esColumnaVisible('tipo')" field="tipo" header="Tipo" sortable />
            <Column header="Acciones">
                <template #body="slotProps">
                    <div class="flex gap-2">
                        <Button size="small" icon="pi pi-pencil" severity="info" @click="editar(slotProps.data)" />
                        <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminar(slotProps.data)" />
                    </div>
                </template>
            </Column>
        </DataTable>

        <div class="pt-2">
            <h2 class="text-xl font-semibold mb-3">Padres de Rubro</h2>
            <DataTable
                :value="padresRegistros"
                responsiveLayout="scroll"
                paginator
                :rows="10"
                sortMode="multiple"
                removableSort
            >
                <Column field="id" header="ID" sortable />
                <Column field="clave" header="Clave" sortable />
                <Column field="nombre" header="Nombre" sortable />
                <Column field="descripcion" header="Descripcion" />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarPadre(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarPadre(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar rubro' : 'Nuevo rubro'" :style="{ width: '40rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-bookmark mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. VENTAS_BEBIDAS" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-sitemap mr-1 text-primary"></i>Padre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formulario.padre" :options="opcionesPadre" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona categoría padre" filter filterPlaceholder="Buscar opción..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-tags mr-1 text-primary"></i>Tipo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formulario.tipo" :options="opcionesTipo" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona tipo" filter filterPlaceholder="Buscar opción..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formulario.descripcion" rows="3" class="w-full" placeholder="Describe cuando aplica este rubro" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar" @click="guardar" />
            </div>
        </Dialog>

        <Dialog v-model:visible="mostrarDialogoPadre" modal :header="editandoPadreId ? 'Editar padre de rubro' : 'Nuevo padre de rubro'" :style="{ width: '36rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-key mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioPadre.clave" class="w-full" placeholder="Ej. GASTOS" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-tag mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioPadre.nombre" class="w-full" placeholder="Ej. Gastos" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioPadre.descripcion" rows="3" class="w-full" placeholder="Describe el uso de este padre" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoPadre = false" />
                <Button :loading="guardandoPadre" label="Guardar" @click="guardarPadre" />
            </div>
        </Dialog>
    </section>
</template>






