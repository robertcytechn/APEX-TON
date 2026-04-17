<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    actualizarUsuarioDirector,
    crearUsuarioDirector,
    listarRolesDisponiblesDirector,
    listarSucursalesDirector,
    listarUsuariosDirector,
    reiniciarPasswordUsuarioDirector
} from '@/service/cabinaArquitecturaServicio';

const cargando = ref(false);
const guardando = ref(false);
const mostrarDialogo = ref(false);
const modoEdicion = ref(false);
const usuarioEditandoId = ref(null);
const reiniciandoUsuarioId = ref(null);

const usuarios = ref([]);
const sucursales = ref([]);
const roles = ref([]);

const contrasenaCreada = ref('');
const correoEnviado = ref(null);
const detalleCorreo = ref('');
const mensaje = ref('');
const severidadMensaje = ref('info');

const formulario = reactive({
    username: '',
    nombre: '',
    correo: '',
    sucursal: null,
    rol: null,
    is_active: true
});

const opcionesEstadoUsuario = [
    { label: 'Activo', value: true },
    { label: 'Inactivo', value: false }
];

const opcionesFilas = computed(() => {
    const total = usuarios.value.length;
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

const filasPorPagina = ref(10);

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

const limpiarFormulario = () => {
    formulario.username = '';
    formulario.nombre = '';
    formulario.correo = '';
    formulario.sucursal = null;
    formulario.rol = null;
    formulario.is_active = true;
};

const abrirDialogoNuevo = () => {
    modoEdicion.value = false;
    usuarioEditandoId.value = null;
    limpiarResultadoCredenciales();
    limpiarFormulario();
    mostrarDialogo.value = true;
};

const abrirDialogoEdicion = (usuario) => {
    modoEdicion.value = true;
    usuarioEditandoId.value = usuario.id;
    limpiarResultadoCredenciales();

    formulario.username = usuario.username || '';
    formulario.nombre = usuario.nombre || '';
    formulario.correo = usuario.correo || '';
    formulario.sucursal = usuario.sucursal || null;
    formulario.rol = usuario.rol_info?.id || null;
    formulario.is_active = !!usuario.is_active;

    mostrarDialogo.value = true;
};

const cerrarDialogo = () => {
    mostrarDialogo.value = false;
    limpiarFormulario();
    modoEdicion.value = false;
    usuarioEditandoId.value = null;
};

const cargarCatalogos = async () => {
    const [respuestaSucursales, respuestaRoles] = await Promise.all([
        listarSucursalesDirector(),
        listarRolesDisponiblesDirector()
    ]);

    sucursales.value = respuestaSucursales.data.data || [];
    roles.value = respuestaRoles.data.data || [];
};

const cargarUsuarios = async () => {
    const { data } = await listarUsuariosDirector();
    usuarios.value = data.data || [];
};

const cargarVista = async () => {
    cargando.value = true;
    try {
        await Promise.all([cargarCatalogos(), cargarUsuarios()]);
    } finally {
        cargando.value = false;
    }
};

const guardar = async () => {
    if (!formulario.username || !formulario.nombre || !formulario.correo || !formulario.sucursal || !formulario.rol) {
        severidadMensaje.value = 'error';
        mensaje.value = 'Completa todos los campos obligatorios antes de guardar.';
        return;
    }

    guardando.value = true;
    try {
        const payload = {
            username: formulario.username,
            nombre: formulario.nombre,
            correo: formulario.correo,
            sucursal: formulario.sucursal,
            rol: formulario.rol,
            is_active: formulario.is_active
        };

        let data = null;
        if (modoEdicion.value && usuarioEditandoId.value) {
            ({ data } = await actualizarUsuarioDirector(usuarioEditandoId.value, payload));
            limpiarResultadoCredenciales();
            severidadMensaje.value = 'success';
            mensaje.value = data?.message || 'Usuario actualizado correctamente.';
        } else {
            ({ data } = await crearUsuarioDirector(payload));
            contrasenaCreada.value = data?.data?.contrasena_generada || '';
            correoEnviado.value = typeof data?.data?.correo_enviado === 'boolean' ? data.data.correo_enviado : null;
            detalleCorreo.value = data?.data?.detalle_correo || '';
            severidadMensaje.value = correoEnviado.value === false ? 'warn' : 'success';
            mensaje.value = data?.message || 'Usuario creado correctamente para captura operativa.';
        }

        cerrarDialogo();
        await cargarUsuarios();
    } catch (error) {
        severidadMensaje.value = 'error';
        mensaje.value = construirMensajeError(error, 'No se pudo guardar el usuario.');
    } finally {
        guardando.value = false;
    }
};

const reiniciarContrasena = async (usuario) => {
    const confirmado = window.confirm(`¿Deseas reiniciar la contraseña de ${usuario.nombre || usuario.username}?`);
    if (!confirmado) {
        return;
    }

    reiniciandoUsuarioId.value = usuario.id;
    try {
        const { data } = await reiniciarPasswordUsuarioDirector(usuario.id);
        contrasenaCreada.value = data?.data?.contrasena_generada || '';
        correoEnviado.value = typeof data?.data?.correo_enviado === 'boolean' ? data.data.correo_enviado : null;
        detalleCorreo.value = data?.data?.detalle_correo || '';
        severidadMensaje.value = correoEnviado.value === false ? 'warn' : 'success';
        mensaje.value = data?.message || 'Contraseña reiniciada correctamente.';

        await cargarUsuarios();
    } catch (error) {
        severidadMensaje.value = 'error';
        mensaje.value = construirMensajeError(error, 'No se pudo reiniciar la contraseña del usuario.');
    } finally {
        reiniciandoUsuarioId.value = null;
    }
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

onMounted(cargarVista);
</script>

<template>
    <section class="space-y-6">
        <div class="card space-y-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Cabina Director: Usuarios Operativos</h1>
                    <p class="text-sm text-surface-500 mt-1">Alta, edición y reinicio de contraseña para usuarios CONTADOR y GERENTE con un solo casino y un solo rol.</p>
                </div>
                <Button label="Nuevo usuario" icon="pi pi-user-plus" @click="abrirDialogoNuevo" />
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

            <DataTable
                :value="usuarios"
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

                <Column field="username" header="Usuario" sortable />
                <Column field="nombre" header="Nombre" sortable />
                <Column field="correo" header="Correo" sortable />
                <Column field="sucursal_nombre" header="Casino" sortable />
                <Column header="Rol" sortable sortField="rol_info.nombre">
                    <template #body="slotProps">
                        {{ slotProps.data.rol_info?.nombre || 'Sin rol' }}
                    </template>
                </Column>
                <Column field="is_active" header="Activo" sortable>
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.is_active ? 'Sí' : 'No'" :severity="slotProps.data.is_active ? 'success' : 'danger'" />
                    </template>
                </Column>
                <Column header="Acciones" style="min-width: 11rem">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-2">
                            <Button
                                icon="pi pi-pencil"
                                label="Editar"
                                size="small"
                                outlined
                                @click="abrirDialogoEdicion(slotProps.data)"
                            />
                            <Button
                                icon="pi pi-refresh"
                                label="Reset"
                                size="small"
                                severity="warn"
                                :loading="reiniciandoUsuarioId === slotProps.data.id"
                                @click="reiniciarContrasena(slotProps.data)"
                            />
                        </div>
                    </template>
                </Column>
            </DataTable>
        </div>

        <Dialog
            v-model:visible="mostrarDialogo"
            modal
            :header="modoEdicion ? 'Editar usuario operativo' : 'Nuevo usuario operativo'"
            :style="{ width: '42rem' }"
            @hide="cerrarDialogo"
        >
            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-user mr-1 text-primary" />
                        Usuario <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.username" class="w-full" placeholder="Ej. conta_morelia_01" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-id-card mr-1 text-primary" />
                        Nombre completo <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.nombre" class="w-full" placeholder="Ej. Maria Lopez" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-envelope mr-1 text-primary" />
                        Correo <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <InputText v-model="formulario.correo" class="w-full" placeholder="usuario@empresa.com" />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-building mr-1 text-primary" />
                        Casino asignado <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <Select
                        v-model="formulario.sucursal"
                        :options="sucursales"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Selecciona casino"
                        filter
                        filterPlaceholder="Buscar casino..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-shield mr-1 text-primary" />
                        Rol operativo <span class="text-red-500">*</span>
                        <small class="text-surface-500 ml-1">(obligatorio)</small>
                    </label>
                    <Select
                        v-model="formulario.rol"
                        :options="roles"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Selecciona rol"
                        filter
                        filterPlaceholder="Buscar rol..."
                    />
                </div>
                <div>
                    <label class="block text-sm mb-2">
                        <i class="pi pi-lock mr-1 text-primary" />
                        Estado del usuario
                    </label>
                    <Select
                        v-model="formulario.is_active"
                        :options="opcionesEstadoUsuario"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Selecciona estado"
                    />
                    <small class="text-surface-500 block mt-2">
                        {{ modoEdicion ? 'Puedes activar o desactivar el acceso del usuario.' : 'Se recomienda dejarlo activo en su creación.' }}
                    </small>
                </div>
            </div>

            <small class="text-surface-500 block mt-4">La contraseña se genera automáticamente con 8 dígitos al crear o reiniciar.</small>

            <div class="flex justify-end gap-2 mt-6">
                <Button label="Cancelar" severity="secondary" @click="cerrarDialogo" />
                <Button
                    :loading="guardando"
                    :label="modoEdicion ? 'Guardar cambios' : 'Crear usuario'"
                    icon="pi pi-check"
                    @click="guardar"
                />
            </div>
        </Dialog>
    </section>
</template>
