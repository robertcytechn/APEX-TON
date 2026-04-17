<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    actualizarAsignacionFondoFijoAdmin,
    actualizarFondoFijoAdmin,
    actualizarSucursalAdmin,
    crearAsignacionFondoFijoAdmin,
    crearFondoFijoAdmin,
    crearSucursalAdmin,
    eliminarAsignacionFondoFijoAdmin,
    eliminarFondoFijoAdmin,
    eliminarSucursalAdmin,
    listarAsignacionesFondosFijosAdmin,
    listarFondosFijosAdmin,
    listarSucursalesAdmin
} from '@/service/cabinaArquitecturaServicio';
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';

const cargandoSucursales = ref(false);
const guardandoSucursal = ref(false);
const sucursales = ref([]);
const mostrarDialogoSucursal = ref(false);
const editandoSucursalId = ref(null);

const cargandoFondos = ref(false);
const guardandoFondo = ref(false);
const fondos = ref([]);
const mostrarDialogoFondo = ref(false);
const editandoFondoId = ref(null);

const cargandoAsignaciones = ref(false);
const guardandoAsignacion = ref(false);
const asignaciones = ref([]);
const mostrarDialogoAsignacion = ref(false);
const editandoAsignacionId = ref(null);

const columnasDisponiblesSucursales = [
    { label: 'ID', value: 'id' },
    { label: 'Clave', value: 'clave' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Ciudad', value: 'ciudad' },
    { label: 'Encargado', value: 'encargado' }
];
const columnasVisiblesSucursales = ref([...columnasDisponiblesSucursales]);
const filasPorPaginaSucursales = ref(10);

const columnasDisponiblesFondos = [
    { label: 'ID', value: 'id' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Descripcion', value: 'descripcion' },
    { label: 'Estado', value: 'estado' }
];
const columnasVisiblesFondos = ref([...columnasDisponiblesFondos]);
const filasPorPaginaFondos = ref(10);

const columnasDisponiblesAsignaciones = [
    { label: 'ID', value: 'id' },
    { label: 'Sucursal', value: 'sucursal_nombre' },
    { label: 'Fondo fijo', value: 'fondo_fijo_nombre' },
    { label: 'Monto asignado', value: 'monto_asignado' },
    { label: 'Estado', value: 'estado' }
];
const columnasVisiblesAsignaciones = ref([...columnasDisponiblesAsignaciones]);
const filasPorPaginaAsignaciones = ref(10);

const opcionesFilasMostrarSucursales = computed(() => {
    const total = sucursales.value.length;
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

const opcionesFilasMostrarFondos = computed(() => {
    const total = fondos.value.length;
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

const opcionesFilasMostrarAsignaciones = computed(() => {
    const total = asignaciones.value.length;
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

// 1) Para qué sirve: evaluar visibilidad dinámica de columnas por tabla.
// 2) Cómo funciona: verifica si la clave existe en el arreglo de columnas activas.
// 3) Qué hace: permite mostrar/ocultar columnas sin recargar la vista.
// 4) Cómo editarla: agrega reglas por rol si ciertas columnas deben restringirse.
const esColumnaVisible = (columnas, columna) => columnas.some((item) => item.value === columna);

const opcionesSucursales = computed(() =>
    sucursales.value.map((item) => ({
        label: `${item.clave} - ${item.nombre}`,
        value: item.id
    }))
);

const opcionesFondos = computed(() =>
    fondos.value.map((item) => ({
        label: item.nombre,
        value: item.id
    }))
);

const formularioSucursal = reactive({
    nombre: '',
    clave: '',
    direccion: '',
    ciudad: '',
    estado_republica: '',
    telefono: '',
    correo: '',
    encargado: ''
});

const formularioFondo = reactive({
// 1) Para qué sirve: resetear formulario de sucursal.
// 2) Cómo funciona: limpia todos los campos y desactiva modo edición.
// 3) Qué hace: prepara un estado neutro para alta o cancelación.
// 4) Cómo editarla: incluye nuevos atributos de sucursal cuando se agreguen.
    nombre: '',
    descripcion: ''
});

const formularioAsignacion = reactive({
    sucursal: null,
    fondo_fijo: null,
    monto_asignado: null
});

const limpiarFormularioSucursal = () => {
    formularioSucursal.nombre = '';
    formularioSucursal.clave = '';
    formularioSucursal.direccion = '';
    formularioSucursal.ciudad = '';
    formularioSucursal.estado_republica = '';
    formularioSucursal.telefono = '';
    formularioSucursal.correo = '';
    formularioSucursal.encargado = '';
    editandoSucursalId.value = null;
};

// 1) Para qué sirve: resetear formulario de fondo fijo.
// 2) Cómo funciona: limpia campos de nombre/descripcion y editandoFondoId.
// 3) Qué hace: evita contaminación de datos entre operaciones.
// 4) Cómo editarla: agrega limpieza de campos extra si el fondo crece.
const limpiarFormularioFondo = () => {
    formularioFondo.nombre = '';
    formularioFondo.descripcion = '';
    editandoFondoId.value = null;
};

// 1) Para qué sirve: resetear formulario de asignación sucursal-fondo.
// 2) Cómo funciona: restablece ids seleccionados y monto asignado.
// 3) Qué hace: deja el modal listo para una captura nueva.
// 4) Cómo editarla: incorpora nuevos campos de vigencia o prioridad cuando existan.
const limpiarFormularioAsignacion = () => {
    formularioAsignacion.sucursal = null;
    formularioAsignacion.fondo_fijo = null;
    formularioAsignacion.monto_asignado = null;
    editandoAsignacionId.value = null;
};

// 1) Para qué sirve: limpiar monto monetario al recibir foco en InputNumber.
// 2) Cómo funciona: si el valor actual es 0, lo cambia a null para captura limpia.
// 3) Qué hace: evita que el usuario tenga que borrar manualmente el 0.00.
// 4) Cómo editarla: reutiliza en nuevos campos monetarios del módulo.
const limpiarMonetarioEnFoco = (contenedor, campo) => {
    const valorActual = Number(contenedor?.[campo]);
    if (Number.isFinite(valorActual) && valorActual === 0) {
        contenedor[campo] = null;
    }
};

// 1) Para qué sirve: cargar catálogo de sucursales.
// 2) Cómo funciona: consulta servicio y actualiza estado `sucursales`.
// 3) Qué hace: alimenta tabla principal y opciones de asignación.
// 4) Cómo editarla: aplica transformaciones de respuesta si backend cambia estructura.
const cargarSucursales = async () => {
    cargandoSucursales.value = true;
    try {
        const { data } = await listarSucursalesAdmin();
        sucursales.value = data.data || [];
    } finally {
        cargandoSucursales.value = false;
    }
};

// 1) Para qué sirve: cargar catálogo de fondos fijos.
// 2) Cómo funciona: consulta endpoint de fondos y guarda registros.
// 3) Qué hace: permite mantenimiento y selección de fondos en asignaciones.
// 4) Cómo editarla: agrega filtros por estado si el endpoint los soporta.
const cargarFondos = async () => {
    cargandoFondos.value = true;
    try {
        const { data } = await listarFondosFijosAdmin();
        fondos.value = data.data || [];
    } finally {
        cargandoFondos.value = false;
    }
};

// 1) Para qué sirve: cargar asignaciones de fondos por sucursal.
// 2) Cómo funciona: obtiene relación desde API y actualiza la tabla correspondiente.
// 3) Qué hace: muestra configuración vigente de montos por sucursal.
// 4) Cómo editarla: agrega ordenamiento/normalización si backend devuelve datos ampliados.
const cargarAsignaciones = async () => {
    cargandoAsignaciones.value = true;
    try {
        const { data } = await listarAsignacionesFondosFijosAdmin();
        asignaciones.value = data.data || [];
    } finally {
        cargandoAsignaciones.value = false;
    }
};

// 1) Para qué sirve: abrir modal en modo alta de sucursal.
// 2) Cómo funciona: limpia formulario y activa diálogo.
// 3) Qué hace: inicia flujo de registro de nueva sala.
// 4) Cómo editarla: precarga valores por default según políticas de negocio.
const nuevoSucursal = () => {
    limpiarFormularioSucursal();
    mostrarDialogoSucursal.value = true;
};

// 1) Para qué sirve: abrir modal de edición para una sucursal existente.
// 2) Cómo funciona: mapea los datos del registro al formulario.
// 3) Qué hace: habilita actualización de datos operativos de sucursal.
// 4) Cómo editarla: sincroniza nuevos campos cuando el modelo de sucursal se expanda.
const editarSucursal = (registro) => {
    formularioSucursal.nombre = registro.nombre || '';
    formularioSucursal.clave = registro.clave || '';
    formularioSucursal.direccion = registro.direccion || '';
    formularioSucursal.ciudad = registro.ciudad || '';
    formularioSucursal.estado_republica = registro.estado_republica || '';
    formularioSucursal.telefono = registro.telefono || '';
    formularioSucursal.correo = registro.correo || '';
    formularioSucursal.encargado = registro.encargado || '';
    editandoSucursalId.value = registro.id;
    mostrarDialogoSucursal.value = true;
};

// 1) Para qué sirve: guardar alta/edición de sucursal en backend.
// 2) Cómo funciona: decide create o update según editandoSucursalId.
// 3) Qué hace: persiste cambios y recarga la tabla de sucursales.
// 4) Cómo editarla: agrega validaciones previas de negocio antes de enviar payload.
const guardarSucursal = async () => {
    guardandoSucursal.value = true;
    try {
        const payload = {
            ...formularioSucursal
        };

        if (editandoSucursalId.value) {
            await actualizarSucursalAdmin(editandoSucursalId.value, payload);
        } else {
            await crearSucursalAdmin(payload);
        }
        mostrarDialogoSucursal.value = false;
        limpiarFormularioSucursal();
        await cargarSucursales();
    } finally {
        guardandoSucursal.value = false;
    }
};

// 1) Para qué sirve: eliminar sucursal seleccionada.
// 2) Cómo funciona: llama servicio de eliminación y recarga listado.
// 3) Qué hace: refleja baja lógica inmediatamente en UI.
// 4) Cómo editarla: agrega confirmación explícita antes de borrar.
const eliminarSucursal = async (registro) => {
    await eliminarSucursalAdmin(registro.id);
    await cargarSucursales();
};

// 1) Para qué sirve: abrir modal de alta para fondo fijo.
// 2) Cómo funciona: limpia formulario de fondo y muestra diálogo.
// 3) Qué hace: inicia captura de nuevo fondo en catálogo.
// 4) Cómo editarla: preselecciona estado inicial si se agrega ese campo al formulario.
const nuevoFondo = () => {
    limpiarFormularioFondo();
    mostrarDialogoFondo.value = true;
};

// 1) Para qué sirve: abrir edición de fondo fijo existente.
// 2) Cómo funciona: carga datos del registro al formulario.
// 3) Qué hace: permite actualizar nombre y descripción del fondo.
// 4) Cómo editarla: incorpora campos extra del fondo en el mapeo.
const editarFondo = (registro) => {
    formularioFondo.nombre = registro.nombre || '';
    formularioFondo.descripcion = registro.descripcion || '';
    editandoFondoId.value = registro.id;
    mostrarDialogoFondo.value = true;
};

// 1) Para qué sirve: guardar cambios de fondos fijos.
// 2) Cómo funciona: crea o actualiza según editandoFondoId y recarga catálogos.
// 3) Qué hace: mantiene sincronía entre fondos y asignaciones.
// 4) Cómo editarla: ajusta post-guardado si agregas dependencias adicionales.
const guardarFondo = async () => {
    guardandoFondo.value = true;
    try {
        if (editandoFondoId.value) {
            await actualizarFondoFijoAdmin(editandoFondoId.value, formularioFondo);
        } else {
            await crearFondoFijoAdmin(formularioFondo);
        }
        mostrarDialogoFondo.value = false;
        limpiarFormularioFondo();
        await Promise.all([cargarFondos(), cargarAsignaciones()]);
    } finally {
        guardandoFondo.value = false;
    }
};

// 1) Para qué sirve: eliminar fondo fijo del catálogo.
// 2) Cómo funciona: invoca servicio de borrado y recarga fondos/asignaciones.
// 3) Qué hace: actualiza UI para evitar referencias obsoletas.
// 4) Cómo editarla: valida relaciones activas antes de eliminar si negocio lo exige.
const eliminarFondo = async (registro) => {
    await eliminarFondoFijoAdmin(registro.id);
    await Promise.all([cargarFondos(), cargarAsignaciones()]);
};

// 1) Para qué sirve: abrir modal de nueva asignación de fondo por sucursal.
// 2) Cómo funciona: limpia formulario de asignación y muestra diálogo.
// 3) Qué hace: inicia vínculo entre sucursal y fondo fijo.
// 4) Cómo editarla: agrega defaults por sucursal seleccionada si se requiere.
const nuevaAsignacion = () => {
    limpiarFormularioAsignacion();
    mostrarDialogoAsignacion.value = true;
};

// 1) Para qué sirve: abrir edición de asignación existente.
// 2) Cómo funciona: carga ids y monto del registro en formulario.
// 3) Qué hace: permite ajustar montos asignados por sucursal.
// 4) Cómo editarla: incorpora campos de vigencia o responsable cuando existan.
const editarAsignacion = (registro) => {
    formularioAsignacion.sucursal = registro.sucursal || null;
    formularioAsignacion.fondo_fijo = registro.fondo_fijo || null;
    formularioAsignacion.monto_asignado = registro.monto_asignado === null || registro.monto_asignado === undefined
        ? null
        : Number(registro.monto_asignado);
    editandoAsignacionId.value = registro.id;
    mostrarDialogoAsignacion.value = true;
};

// 1) Para qué sirve: guardar alta/edición de asignaciones.
// 2) Cómo funciona: decide create/update y recarga tabla de asignaciones.
// 3) Qué hace: persiste configuración financiera por sucursal.
// 4) Cómo editarla: incluye validaciones de monto mínimo/máximo antes de guardar.
const guardarAsignacion = async () => {
    guardandoAsignacion.value = true;
    try {
        const payload = {
            ...formularioAsignacion,
            monto_asignado: Number(formularioAsignacion.monto_asignado || 0)
        };

        if (editandoAsignacionId.value) {
            await actualizarAsignacionFondoFijoAdmin(editandoAsignacionId.value, payload);
        } else {
            await crearAsignacionFondoFijoAdmin(payload);
        }
        mostrarDialogoAsignacion.value = false;
        limpiarFormularioAsignacion();
        await cargarAsignaciones();
    } finally {
        guardandoAsignacion.value = false;
    }
};

// 1) Para qué sirve: eliminar asignación sucursal-fondo.
// 2) Cómo funciona: llama endpoint de baja y recarga datos.
// 3) Qué hace: remueve vínculo operativo reflejado en la tabla.
// 4) Cómo editarla: añade confirmación o auditoría previa en UI.
const eliminarAsignacion = async (registro) => {
    await eliminarAsignacionFondoFijoAdmin(registro.id);
    await cargarAsignaciones();
};

// 1) Para qué sirve: ejecutar carga inicial integral del módulo.
// 2) Cómo funciona: solicita en paralelo sucursales, fondos y asignaciones.
// 3) Qué hace: deja listas las tres secciones administrativas al abrir la vista.
// 4) Cómo editarla: agrega más catálogos al Promise.all si la vista crece.
onMounted(async () => {
    await Promise.all([cargarSucursales(), cargarFondos(), cargarAsignaciones()]);
});
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h1 class="text-2xl font-semibold">Sucursales</h1>
                <Button label="Nueva sucursal" icon="pi pi-plus" @click="nuevoSucursal" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesSucursales" :options="columnasDisponiblesSucursales" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaSucursales" :options="opcionesFilasMostrarSucursales" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="sucursales"
                :loading="cargandoSucursales"
                paginator
                :rows="filasPorPaginaSucursales"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column v-if="esColumnaVisible(columnasVisiblesSucursales, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesSucursales, 'clave')" field="clave" header="Clave" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesSucursales, 'nombre')" field="nombre" header="Nombre" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesSucursales, 'ciudad')" field="ciudad" header="Ciudad" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesSucursales, 'encargado')" field="encargado" header="Encargado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarSucursal(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarSucursal(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h2 class="text-xl font-semibold">Catalogo de Fondos Fijos</h2>
                <Button label="Nuevo fondo fijo" icon="pi pi-plus" severity="contrast" @click="nuevoFondo" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesFondos" :options="columnasDisponiblesFondos" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaFondos" :options="opcionesFilasMostrarFondos" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="fondos"
                :loading="cargandoFondos"
                paginator
                :rows="filasPorPaginaFondos"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column v-if="esColumnaVisible(columnasVisiblesFondos, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesFondos, 'nombre')" field="nombre" header="Nombre" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesFondos, 'descripcion')" field="descripcion" header="Descripcion" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesFondos, 'estado')" field="estado" header="Estado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarFondo(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarFondo(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <div class="card space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h2 class="text-xl font-semibold">Asignacion de Fondos Fijos por Sucursal</h2>
                <Button label="Nueva asignacion" icon="pi pi-plus" severity="success" @click="nuevaAsignacion" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-columns mr-1 text-primary"></i>Columnas visibles</label>
                    <MultiSelect v-model="columnasVisiblesAsignaciones" :options="columnasDisponiblesAsignaciones" optionLabel="label" display="chip" class="w-full" placeholder="Selecciona columnas" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-list mr-1 text-primary"></i>Filas por pagina</label>
                    <Select v-model="filasPorPaginaAsignaciones" :options="opcionesFilasMostrarAsignaciones" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona cantidad" />
                </div>
            </div>

            <DataTable
                :value="asignaciones"
                :loading="cargandoAsignaciones"
                paginator
                :rows="filasPorPaginaAsignaciones"
                responsiveLayout="scroll"
                reorderableColumns
                resizableColumns
                columnResizeMode="fit"
                sortMode="multiple"
                removableSort
            >
                <Column v-if="esColumnaVisible(columnasVisiblesAsignaciones, 'id')" field="id" header="ID" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesAsignaciones, 'sucursal_nombre')" field="sucursal_nombre" header="Sucursal" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesAsignaciones, 'fondo_fijo_nombre')" field="fondo_fijo_nombre" header="Fondo fijo" sortable />
                <Column v-if="esColumnaVisible(columnasVisiblesAsignaciones, 'monto_asignado')" field="monto_asignado" header="Monto asignado" sortable>
                    <template #body="slotProps">
                        <MontoMonedaColoreado :monto="slotProps.data.monto_asignado" />
                    </template>
                </Column>
                <Column v-if="esColumnaVisible(columnasVisiblesAsignaciones, 'estado')" field="estado" header="Estado" sortable />
                <Column header="Acciones">
                    <template #body="slotProps">
                        <div class="flex gap-2">
                            <Button size="small" icon="pi pi-pencil" severity="info" @click="editarAsignacion(slotProps.data)" />
                            <Button size="small" icon="pi pi-trash" severity="danger" @click="eliminarAsignacion(slotProps.data)" />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog v-model:visible="mostrarDialogoSucursal" modal :header="editandoSucursalId ? 'Editar sucursal' : 'Nueva sucursal'" :style="{ width: '48rem' }">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioSucursal.nombre" class="w-full" placeholder="Ej. Sala Morelia Centro" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-hashtag mr-1 text-primary"></i>Clave <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioSucursal.clave" class="w-full" placeholder="Ej. MOR-01" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-map-marker mr-1 text-primary"></i>Ciudad <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioSucursal.ciudad" class="w-full" placeholder="Ej. Morelia" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-map mr-1 text-primary"></i>Estado <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioSucursal.estado_republica" class="w-full" placeholder="Ej. Michoacan" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-phone mr-1 text-primary"></i>Telefono <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioSucursal.telefono" class="w-full" placeholder="Ej. 4431234567" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-envelope mr-1 text-primary"></i>Correo <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioSucursal.correo" class="w-full" placeholder="sucursal@empresa.com" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-user mr-1 text-primary"></i>Encargado <small class="text-surface-500">(opcional)</small></label>
                    <InputText v-model="formularioSucursal.encargado" class="w-full" placeholder="Nombre del responsable" />
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm mb-2"><i class="pi pi-home mr-1 text-primary"></i>Direccion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioSucursal.direccion" rows="3" class="w-full" placeholder="Calle, numero, colonia y referencias" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoSucursal = false" />
                <Button :loading="guardandoSucursal" label="Guardar" @click="guardarSucursal" />
            </div>
        </Dialog>

        <Dialog v-model:visible="mostrarDialogoFondo" modal :header="editandoFondoId ? 'Editar fondo fijo' : 'Nuevo fondo fijo'" :style="{ width: '36rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-bookmark mr-1 text-primary"></i>Nombre <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <InputText v-model="formularioFondo.nombre" class="w-full" placeholder="Ej. Caja Chica" />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-align-left mr-1 text-primary"></i>Descripcion <small class="text-surface-500">(opcional)</small></label>
                    <Textarea v-model="formularioFondo.descripcion" rows="3" class="w-full" placeholder="Describe el uso operativo del fondo fijo" />
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoFondo = false" />
                <Button :loading="guardandoFondo" label="Guardar" @click="guardarFondo" />
            </div>
        </Dialog>

        <Dialog v-model:visible="mostrarDialogoAsignacion" modal :header="editandoAsignacionId ? 'Editar asignacion de fondo fijo' : 'Nueva asignacion de fondo fijo'" :style="{ width: '40rem' }">
            <div class="space-y-4">
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Sucursal <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioAsignacion.sucursal" :options="opcionesSucursales" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona sucursal" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-wallet mr-1 text-primary"></i>Fondo fijo <span class="text-red-500">*</span> <small class="text-surface-500">(obligatorio)</small></label>
                    <Select v-model="formularioAsignacion.fondo_fijo" :options="opcionesFondos" optionLabel="label" optionValue="value" class="w-full" placeholder="Selecciona fondo fijo" filter filterPlaceholder="Buscar opcion..." />
                </div>
                <div>
                    <label class="block text-sm mb-2"><i class="pi pi-dollar mr-1 text-primary"></i>Monto asignado <span class="text-red-500">*</span> <small class="text-surface-500">(formato monetario obligatorio)</small></label>
                    <InputNumber
                        v-model="formularioAsignacion.monto_asignado"
                        class="w-full"
                        mode="decimal"
                        :min="0"
                        :minFractionDigits="2"
                        :maxFractionDigits="2"
                        :useGrouping="true"
                        placeholder="0.00"
                        @focus="limpiarMonetarioEnFoco(formularioAsignacion, 'monto_asignado')"
                    />
                    <small class="text-surface-500">Vista previa monetaria coloreada</small>
                    <div class="mt-2">
                        <MontoMonedaColoreado :monto="Number(formularioAsignacion.monto_asignado || 0)" />
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogoAsignacion = false" />
                <Button :loading="guardandoAsignacion" label="Guardar" @click="guardarAsignacion" />
            </div>
        </Dialog>
    </section>
</template>





