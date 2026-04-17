<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    crearUsuarioAdmin,
    eliminarUsuarioAdmin,
    listarRolesAdmin,
    listarSucursalesAdmin,
    listarUsuariosAdmin,
    actualizarUsuarioAdmin
} from '@/service/cabinaArquitecturaServicio';

const cargando = ref(false);
const guardando = ref(false);
const registros = ref([]);
const sucursales = ref([]);
const rolesDisponibles = ref([]);
const mostrarDialogo = ref(false);
const editandoId = ref(null);
const columnasDisponibles = [
    { label: 'ID', value: 'id' },
    { label: 'Usuario', value: 'username' },
    { label: 'Nombre', value: 'nombre' },
    { label: 'Correo', value: 'correo' },
    { label: 'Roles', value: 'roles' },
    { label: 'Activo', value: 'activo' }
];
const columnasVisibles = ref([...columnasDisponibles]);
const filasPorPagina = ref(10);
const contrasenaCreada = ref('');
const correoEnviado = ref(null);
const detalleCorreo = ref('');
const mensaje = ref('');
const severidadMensaje = ref('info');

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

// 1) Para qué sirve: decidir si una columna debe mostrarse en la tabla.
// 2) Cómo funciona: valida si la columna existe dentro de columnasVisibles.
// 3) Qué hace: permite personalizar visibilidad de columnas desde UI.
// 4) Cómo editarla: cambia el criterio de visibilidad si agregas perfiles por usuario.
const esColumnaVisible = (columna) => columnasVisibles.value.some((item) => item.value === columna);

const limpiarResultadoCredenciales = () => {
    contrasenaCreada.value = '';
    correoEnviado.value = null;
    detalleCorreo.value = '';
};

const construirMensajeError = (error, fallback = 'No se pudo completar la operación.') => {
    const erroresCampo = error?.response?.data?.data;
    if (erroresCampo && typeof erroresCampo === 'object') {
        const primerError = Object.values(erroresCampo).flat().find(Boolean);
        if (primerError) {
            return primerError;
        }
    }
    return error?.response?.data?.message || fallback;
};

const formulario = reactive({
    username: '',
    nombre: '',
    correo: '',
    sucursal: null,
    roles_ids: [],
    is_active: true,
    is_staff: false,
    password: ''
});

// 1) Para qué sirve: reiniciar el formulario a estado limpio.
// 2) Cómo funciona: restablece campos reactivos y limpia el id de edición.
// 3) Qué hace: evita arrastrar datos entre altas y ediciones.
// 4) Cómo editarla: agrega aquí cualquier campo nuevo del formulario de usuario.
const limpiarFormulario = () => {
    formulario.username = '';
    formulario.nombre = '';
    formulario.correo = '';
    formulario.sucursal = null;
    formulario.roles_ids = [];
    formulario.is_active = true;
    formulario.is_staff = false;
    formulario.password = '';
    editandoId.value = null;
};

// 1) Para qué sirve: cargar datos base para la pantalla de usuarios.
// 2) Cómo funciona: consulta usuarios, sucursales y roles en paralelo.
// 3) Qué hace: hidrata tablas y selects de captura.
// 4) Cómo editarla: añade nuevas fuentes de catálogo dentro de Promise.all.
const cargar = async () => {
    cargando.value = true;
    try {
        const [resUsuarios, resSucursales, resRoles] = await Promise.all([listarUsuariosAdmin(), listarSucursalesAdmin(), listarRolesAdmin()]);
        registros.value = resUsuarios.data.data || [];
        sucursales.value = resSucursales.data.data || [];
        rolesDisponibles.value = resRoles.data.data || [];
    } finally {
        cargando.value = false;
    }
};

// 1) Para qué sirve: abrir diálogo en modo alta de usuario.
// 2) Cómo funciona: limpia formulario y activa visibilidad del modal.
// 3) Qué hace: prepara captura inicial sin datos previos.
// 4) Cómo editarla: agrega valores por defecto específicos antes de abrir diálogo.
const nuevo = () => {
    limpiarFormulario();
    limpiarResultadoCredenciales();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: abrir diálogo en modo edición con datos del registro.
// 2) Cómo funciona: mapea propiedades del registro hacia el formulario reactivo.
// 3) Qué hace: permite modificar usuario existente en el mismo modal.
// 4) Cómo editarla: incluye aquí campos nuevos cuando el backend los exponga.
const editar = (registro) => {
    formulario.username = registro.username || '';
    formulario.nombre = registro.nombre || '';
    formulario.correo = registro.correo || '';
    formulario.sucursal = registro.sucursal || null;
    formulario.roles_ids = Array.isArray(registro.roles) ? registro.roles.map((rol) => rol.id) : [];
    formulario.is_active = !!registro.is_active;
    formulario.is_staff = !!registro.is_staff;
    formulario.password = '';
    editandoId.value = registro.id;
    limpiarResultadoCredenciales();
    mostrarDialogo.value = true;
};

// 1) Para qué sirve: construir payload final para crear o actualizar usuario.
// 2) Cómo funciona: toma valores de formulario y agrega password solo si existe.
// 3) Qué hace: evita enviar contraseña vacía en ediciones.
// 4) Cómo editarla: incorpora transformaciones adicionales si cambia contrato API.
const construirPayload = () => {
    const payload = {
        username: formulario.username,
        nombre: formulario.nombre,
        correo: formulario.correo,
        sucursal: formulario.sucursal,
        roles_ids: formulario.roles_ids,
        is_active: formulario.is_active,
        is_staff: formulario.is_staff
    };

    if (formulario.password) {
        payload.password = formulario.password;
    }

    return payload;
};

// 1) Para qué sirve: persistir cambios de usuario en backend.
// 2) Cómo funciona: decide alta o edición según editandoId y luego recarga lista.
// 3) Qué hace: sincroniza tabla con el estado guardado en servidor.
// 4) Cómo editarla: agrega validación previa al envío antes de llamar servicio.
const guardar = async () => {
    guardando.value = true;
    try {
        const payload = construirPayload();
        if (editandoId.value) {
            const { data } = await actualizarUsuarioAdmin(editandoId.value, payload);
            limpiarResultadoCredenciales();
            severidadMensaje.value = 'success';
            mensaje.value = data?.message || 'Usuario actualizado correctamente.';
        } else {
            const { data } = await crearUsuarioAdmin(payload);
            contrasenaCreada.value = data?.data?.contrasena_generada || '';
            correoEnviado.value = typeof data?.data?.correo_enviado === 'boolean' ? data.data.correo_enviado : null;
            detalleCorreo.value = data?.data?.detalle_correo || '';
            severidadMensaje.value = correoEnviado.value === false ? 'warn' : 'success';
            mensaje.value = data?.message || 'Usuario creado correctamente.';
        }
        mostrarDialogo.value = false;
        limpiarFormulario();
        await cargar();
    } catch (error) {
        severidadMensaje.value = 'error';
        mensaje.value = construirMensajeError(error, 'No se pudo guardar el usuario.');
    } finally {
        guardando.value = false;
    }
};

// 1) Para qué sirve: eliminar un usuario desde la tabla.
// 2) Cómo funciona: invoca endpoint de eliminación y vuelve a cargar registros.
// 3) Qué hace: refleja inmediatamente la baja en UI.
// 4) Cómo editarla: agrega confirmación modal si deseas prevenir borrados accidentales.
const eliminar = async (registro) => {
    await eliminarUsuarioAdmin(registro.id);
    severidadMensaje.value = 'success';
    mensaje.value = 'Usuario desactivado correctamente.';
    await cargar();
};

const copiarContrasena = async () => {
    if (!contrasenaCreada.value) {
        return;
    }

    try {
        await navigator.clipboard.writeText(contrasenaCreada.value);
        severidadMensaje.value = 'info';
        mensaje.value = 'Contraseña copiada al portapapeles.';
    } catch {
        severidadMensaje.value = 'warn';
        mensaje.value = 'No fue posible copiar la contraseña automáticamente.';
    }
};

// 1) Para qué sirve: inicializar la pantalla al montar el componente.
// 2) Cómo funciona: ejecuta la carga inicial de catálogos y registros.
// 3) Qué hace: muestra información actual al abrir módulo de usuarios.
// 4) Cómo editarla: añade cargas complementarias antes de pintar la tabla.
onMounted(cargar);
</script>

<template>
    <section class="card space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h1 class="text-2xl font-semibold">Usuarios</h1>
            <Button label="Nuevo usuario" icon="pi pi-plus" @click="nuevo" />
        </div>

        <Message v-if="mensaje" :severity="severidadMensaje" :closable="false">
            <div class="w-full flex flex-col gap-2">
                <span>{{ mensaje }}</span>
                <div class="flex flex-wrap items-center gap-2">
                    <Tag
                        v-if="correoEnviado !== null"
                        :value="correoEnviado ? 'Correo enviado' : 'Correo no enviado'"
                        :severity="correoEnviado ? 'success' : 'danger'"
                    />
                    <Tag v-if="contrasenaCreada" :value="`Contraseña generada: ${contrasenaCreada}`" severity="warn" />
                    <Button
                        v-if="contrasenaCreada"
                        label="Copiar"
                        icon="pi pi-copy"
                        size="small"
                        severity="secondary"
                        @click="copiarContrasena"
                    />
                </div>
                <small v-if="detalleCorreo" class="text-surface-700 dark:text-surface-200">{{ detalleCorreo }}</small>
            </div>
        </Message>

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
            <Column v-if="esColumnaVisible('username')" field="username" header="Usuario" sortable />
            <Column v-if="esColumnaVisible('nombre')" field="nombre" header="Nombre" sortable />
            <Column v-if="esColumnaVisible('correo')" field="correo" header="Correo" sortable />
            <Column v-if="esColumnaVisible('roles')" header="Roles">
                <template #body="slotProps">
                    {{ Array.isArray(slotProps.data.roles) && slotProps.data.roles.length ? slotProps.data.roles.map((rol) => rol.nombre).join(', ') : 'Sin rol asignado' }}
                </template>
            </Column>
            <Column v-if="esColumnaVisible('activo')" field="is_active" header="Activo" sortable>
                <template #body="slotProps">{{ slotProps.data.is_active ? 'Sí' : 'No' }}</template>
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

        <Dialog v-model:visible="mostrarDialogo" modal :header="editandoId ? 'Editar usuario' : 'Nuevo usuario'" :style="{ width: '40rem' }">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-user mr-1 text-primary"></i>
                        Usuario <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.username" class="w-full" placeholder="Ej. admin_principal" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-id-card mr-1 text-primary"></i>
                        Nombre completo <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. Juan Perez Garcia" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-envelope mr-1 text-primary"></i>
                        Correo <small class="text-surface-500">(opcional)</small>
                    </label>
                    <InputText v-model="formulario.correo" class="w-full" placeholder="usuario@empresa.com" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-building mr-1 text-primary"></i>
                        Sucursal <small class="text-surface-500">(opcional)</small>
                    </label>
                    <Select v-model="formulario.sucursal" :options="sucursales" optionLabel="nombre" optionValue="id" class="w-full" placeholder="Selecciona sucursal" filter filterPlaceholder="Buscar opción..." />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-shield mr-1 text-primary"></i>
                        Rol <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <MultiSelect v-model="formulario.roles_ids" :options="rolesDisponibles" optionLabel="nombre" optionValue="id" display="chip" class="w-full" placeholder="Selecciona uno o más roles" filter filterPlaceholder="Buscar opción..." />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-lock mr-1 text-primary"></i>
                        Contraseña <small class="text-surface-500">(opcional: si la dejas vacía se genera automáticamente)</small>
                    </label>
                    <Password v-model="formulario.password" :feedback="false" fluid placeholder="Mínimo 8 caracteres" />
                </div>
                <div class="flex flex-col gap-2">
                    <div class="flex items-center gap-2 mt-8">
                        <Checkbox v-model="formulario.is_active" binary inputId="activo_usuario" />
                        <label for="activo_usuario">Activo</label>
                    </div>
                    <div class="flex items-center gap-2">
                        <Checkbox v-model="formulario.is_staff" binary inputId="staff_usuario" />
                        <label for="staff_usuario">Es staff</label>
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="mostrarDialogo = false" />
                <Button :loading="guardando" label="Guardar" @click="guardar" />
            </div>
        </Dialog>
    </section>
</template>





