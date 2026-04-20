<script setup>
import { actualizarPerfilPropio, obtenerPerfilPropio } from '@/service/autenticacionServicio';
import { useSesionStore } from '@/stores/sesion';
import Cropper from 'cropperjs/dist/cropper.esm.js';
import 'cropperjs/dist/cropper.css';
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';

const sesionStore = useSesionStore();

const cargandoPerfil = ref(false);
const guardandoPerfil = ref(false);
const mensajeError = ref('');
const mensajeExito = ref('');
const referenciaInputImagen = ref(null);
const referenciaSeccionSeguridad = ref(null);
const referenciaImagenRecorte = ref(null);
const mostrarDialogoRecorte = ref(false);
const urlImagenRecorteTemporal = ref('');
const instanciaRecorte = ref(null);

const perfil = reactive({
    id: null,
    username: '',
    nombre: '',
    correo: '',
    sucursal_nombre: '',
    roles: [],
    foto_perfil_url: '',
    requiere_cambio_password: false
});

const formularioSeguridad = reactive({
    password_actual: '',
    password_nueva: '',
    password_confirmacion: ''
});

const archivoImagenSeleccionado = ref(null);
const urlVistaPrevia = ref('');
const eliminarFotoActual = ref(false);

const urlImagenMostrada = computed(() => {
    if (urlVistaPrevia.value) {
        return urlVistaPrevia.value;
    }
    return perfil.foto_perfil_url || '';
});

const inicialesUsuario = computed(() => {
    const nombreBase = (perfil.nombre || perfil.username || '').trim();
    if (!nombreBase) {
        return 'US';
    }

    const segmentos = nombreBase.split(/\s+/).filter(Boolean).slice(0, 2);
    return segmentos.map((segmento) => segmento[0]?.toUpperCase() || '').join('') || 'US';
});

const tieneCambioPassword = computed(() => {
    return Boolean(
        formularioSeguridad.password_actual ||
        formularioSeguridad.password_nueva ||
        formularioSeguridad.password_confirmacion
    );
});

const requiereCambioPasswordObligatorio = computed(() => {
    return Boolean(perfil.requiere_cambio_password || sesionStore.requiereCambioPassword);
});

// 1) Para qué sirve: limpiar alertas de estado al iniciar una nueva acción.
// 2) Cómo funciona: reinicia mensajes de éxito y error.
// 3) Qué hace: evita mostrar feedback viejo tras nuevas interacciones.
// 4) Cómo editarla: agrega más estados visuales aquí si se incorporan.
function limpiarMensajes() {
    mensajeError.value = '';
    mensajeExito.value = '';
}

// 1) Para qué sirve: liberar la URL temporal usada para vista previa de imagen.
// 2) Cómo funciona: revoca ObjectURL y limpia referencia local.
// 3) Qué hace: previene fugas de memoria en cambios repetidos de archivo.
// 4) Cómo editarla: mantén esta limpieza si cambias el mecanismo de preview.
function limpiarVistaPrevia() {
    if (urlVistaPrevia.value) {
        URL.revokeObjectURL(urlVistaPrevia.value);
        urlVistaPrevia.value = '';
    }
}

// 1) Para qué sirve: limpiar URL temporal de la imagen original usada en recorte.
// 2) Cómo funciona: revoca el ObjectURL y reinicia su estado.
// 3) Qué hace: evita fugas de memoria al abrir/cerrar el diálogo de recorte.
// 4) Cómo editarla: conserva esta limpieza si cambias el motor de recorte.
function limpiarImagenRecorteTemporal() {
    if (urlImagenRecorteTemporal.value) {
        URL.revokeObjectURL(urlImagenRecorteTemporal.value);
        urlImagenRecorteTemporal.value = '';
    }
}

// 1) Para qué sirve: destruir de forma segura la instancia activa de Cropper.
// 2) Cómo funciona: invoca destroy y limpia la referencia reactiva.
// 3) Qué hace: previene errores al recrear recorte con una nueva imagen.
// 4) Cómo editarla: reutilízala siempre antes de instanciar un nuevo recorte.
function destruirInstanciaRecorte() {
    if (instanciaRecorte.value) {
        instanciaRecorte.value.destroy();
        instanciaRecorte.value = null;
    }
}

// 1) Para qué sirve: abrir el flujo de recorte para una imagen recién seleccionada.
// 2) Cómo funciona: genera URL temporal y abre el diálogo de edición.
// 3) Qué hace: separa selección de archivo y confirmación final de recorte.
// 4) Cómo editarla: agrega metadatos de imagen aquí si más adelante se requieren.
function abrirDialogoRecorte(archivo) {
    destruirInstanciaRecorte();
    limpiarImagenRecorteTemporal();

    urlImagenRecorteTemporal.value = URL.createObjectURL(archivo);
    mostrarDialogoRecorte.value = true;
}

// 1) Para qué sirve: inicializar Cropper cuando la imagen del diálogo está lista.
// 2) Cómo funciona: crea instancia con recorte cuadrado para avatar.
// 3) Qué hace: permite mover/zoom/rotar antes de confirmar la imagen final.
// 4) Cómo editarla: ajusta aspectRatio o restricciones visuales según política UX.
async function manejarImagenListaParaRecorte() {
    await nextTick();
    destruirInstanciaRecorte();

    if (!referenciaImagenRecorte.value) {
        return;
    }

    instanciaRecorte.value = new Cropper(referenciaImagenRecorte.value, {
        aspectRatio: 1,
        viewMode: 1,
        dragMode: 'move',
        autoCropArea: 0.92,
        background: false,
        responsive: true,
        modal: true,
        guides: false,
        center: true
    });
}

function acercarRecorte() {
    instanciaRecorte.value?.zoom(0.12);
}

function alejarRecorte() {
    instanciaRecorte.value?.zoom(-0.12);
}

function rotarRecorte() {
    instanciaRecorte.value?.rotate(90);
}

function reiniciarRecorte() {
    instanciaRecorte.value?.reset();
}

// 1) Para qué sirve: cancelar el recorte activo sin guardar cambios.
// 2) Cómo funciona: cierra diálogo y limpia archivos temporales.
// 3) Qué hace: regresa al estado previo de imagen sin alterar perfil.
// 4) Cómo editarla: agrega confirmación si deseas proteger cierres accidentales.
function cancelarRecorteImagen() {
    mostrarDialogoRecorte.value = false;
    destruirInstanciaRecorte();
    limpiarImagenRecorteTemporal();

    if (referenciaInputImagen.value) {
        referenciaInputImagen.value.value = '';
    }
}

// 1) Para qué sirve: convertir la selección de cropper en archivo final para envío.
// 2) Cómo funciona: exporta canvas recortado y crea un File JPEG optimizado.
// 3) Qué hace: establece la vista previa definitiva que se mandará al backend.
// 4) Cómo editarla: ajusta dimensiones/calidad si cambia la política de avatar.
async function aplicarRecorteImagen() {
    if (!instanciaRecorte.value) {
        mensajeError.value = 'No se pudo inicializar el recorte de imagen.';
        return;
    }

    const lienzoRecortado = instanciaRecorte.value.getCroppedCanvas({
        width: 640,
        height: 640,
        fillColor: '#ffffff',
        imageSmoothingEnabled: true,
        imageSmoothingQuality: 'high'
    });

    if (!lienzoRecortado) {
        mensajeError.value = 'No se pudo generar la imagen recortada.';
        return;
    }

    const blobImagen = await new Promise((resolver) => {
        lienzoRecortado.toBlob(resolver, 'image/jpeg', 0.92);
    });

    if (!blobImagen) {
        mensajeError.value = 'No se pudo preparar el archivo final de imagen.';
        return;
    }

    const archivoFinal = new File([blobImagen], 'perfil_recortada.jpg', { type: 'image/jpeg' });

    limpiarMensajes();
    limpiarVistaPrevia();
    archivoImagenSeleccionado.value = archivoFinal;
    eliminarFotoActual.value = false;
    urlVistaPrevia.value = URL.createObjectURL(archivoFinal);

    mostrarDialogoRecorte.value = false;
    destruirInstanciaRecorte();
    limpiarImagenRecorteTemporal();

    if (referenciaInputImagen.value) {
        referenciaInputImagen.value.value = '';
    }
}

// 1) Para qué sirve: cargar datos de perfil en el estado reactivo de la vista.
// 2) Cómo funciona: mapea payload del backend y resetea banderas de imagen.
// 3) Qué hace: sincroniza formulario con información real del usuario.
// 4) Cómo editarla: agrega nuevos campos de perfil cuando backend los exponga.
function hidratarPerfil(datos = {}) {
    perfil.id = datos.id || null;
    perfil.username = datos.username || '';
    perfil.nombre = datos.nombre || '';
    perfil.correo = datos.correo || '';
    perfil.sucursal_nombre = datos.sucursal_nombre || 'Sin casino asignado';
    perfil.roles = Array.isArray(datos.roles) ? datos.roles : [];
    perfil.foto_perfil_url = datos.foto_perfil_url || '';
    perfil.requiere_cambio_password = !!datos.requiere_cambio_password;

    eliminarFotoActual.value = false;
    archivoImagenSeleccionado.value = null;
}

// 1) Para qué sirve: consultar el perfil propio desde backend al entrar a la vista.
// 2) Cómo funciona: llama endpoint dedicado y actualiza estado local.
// 3) Qué hace: llena datos personales, roles e imagen de perfil actual.
// 4) Cómo editarla: agrega cargas complementarias si el módulo lo requiere.
async function cargarPerfil() {
    cargandoPerfil.value = true;
    limpiarMensajes();

    try {
        const { data } = await obtenerPerfilPropio();
        hidratarPerfil(data?.data || {});
    } catch (error) {
        mensajeError.value = error?.response?.data?.message || 'No se pudo cargar tu perfil.';
    } finally {
        cargandoPerfil.value = false;
    }
}

// 1) Para qué sirve: abrir selector de imagen de perfil.
// 2) Cómo funciona: dispara click sobre input type file oculto.
// 3) Qué hace: permite al usuario elegir una foto desde su equipo.
// 4) Cómo editarla: reemplaza por componente especializado si lo necesitas.
function abrirSelectorImagen() {
    referenciaInputImagen.value?.click();
}

// 1) Para qué sirve: procesar archivo seleccionado para foto de perfil.
// 2) Cómo funciona: valida tipo básico y genera una vista previa temporal.
// 3) Qué hace: prepara el archivo para enviarse al guardar cambios.
// 4) Cómo editarla: agrega validación por tamaño máximo si se requiere.
function manejarCambioImagen(event) {
    const archivo = event?.target?.files?.[0] || null;
    if (!archivo) {
        return;
    }

    if (!archivo.type.startsWith('image/')) {
        mensajeError.value = 'El archivo seleccionado no es una imagen válida.';
        return;
    }

    const tamanioMaximoMb = 8;
    const tamanioMaximoBytes = tamanioMaximoMb * 1024 * 1024;
    if (archivo.size > tamanioMaximoBytes) {
        mensajeError.value = `La imagen excede ${tamanioMaximoMb} MB. Selecciona un archivo más ligero.`;
        return;
    }

    limpiarMensajes();
    abrirDialogoRecorte(archivo);
}

// 1) Para qué sirve: quitar imagen en edición (actual o nueva).
// 2) Cómo funciona: limpia archivo temporal o marca eliminación de foto existente.
// 3) Qué hace: permite guardar perfil sin imagen si así se desea.
// 4) Cómo editarla: agrega confirmación modal si negocio lo solicita.
function quitarImagenPerfil() {
    limpiarMensajes();

    if (mostrarDialogoRecorte.value) {
        cancelarRecorteImagen();
    }

    if (archivoImagenSeleccionado.value) {
        archivoImagenSeleccionado.value = null;
        limpiarVistaPrevia();
        if (referenciaInputImagen.value) {
            referenciaInputImagen.value.value = '';
        }
        return;
    }

    if (perfil.foto_perfil_url) {
        eliminarFotoActual.value = true;
        perfil.foto_perfil_url = '';
    }
}

// 1) Para qué sirve: validar rápidamente campos de cambio de contraseña.
// 2) Cómo funciona: revisa completitud y coincidencia antes de enviar al backend.
// 3) Qué hace: evita llamadas innecesarias cuando hay datos incompletos.
// 4) Cómo editarla: incorpora reglas adicionales de fortaleza si lo deseas.
function validarSeguridadAntesDeGuardar() {
    if (requiereCambioPasswordObligatorio.value && !tieneCambioPassword.value) {
        mensajeError.value = 'Debes cambiar tu contraseña para continuar usando el sistema.';
        return false;
    }

    if (!tieneCambioPassword.value) {
        return true;
    }

    if (!formularioSeguridad.password_actual || !formularioSeguridad.password_nueva || !formularioSeguridad.password_confirmacion) {
        mensajeError.value = 'Para cambiar contraseña debes capturar contraseña actual, nueva y confirmación.';
        return false;
    }

    if (formularioSeguridad.password_nueva !== formularioSeguridad.password_confirmacion) {
        mensajeError.value = 'La confirmación de contraseña no coincide con la nueva contraseña.';
        return false;
    }

    return true;
}

// 1) Para qué sirve: construir payload multipart para actualizar perfil.
// 2) Cómo funciona: agrega correo, foto y bloque de seguridad según corresponda.
// 3) Qué hace: unifica en una sola petición cambios personales y de acceso.
// 4) Cómo editarla: agrega más campos de perfil permitidos en este constructor.
function construirPayloadActualizacion() {
    const payload = new FormData();
    payload.append('correo', perfil.correo || '');

    if (archivoImagenSeleccionado.value) {
        payload.append('foto_perfil', archivoImagenSeleccionado.value);
    }

    if (eliminarFotoActual.value) {
        payload.append('eliminar_foto', 'true');
    }

    if (tieneCambioPassword.value) {
        payload.append('password_actual', formularioSeguridad.password_actual);
        payload.append('password_nueva', formularioSeguridad.password_nueva);
        payload.append('password_confirmacion', formularioSeguridad.password_confirmacion);
    }

    return payload;
}

// 1) Para qué sirve: persistir cambios del perfil de usuario.
// 2) Cómo funciona: envía PATCH multipart y sincroniza store de sesión.
// 3) Qué hace: actualiza correo, contraseña e imagen sin perder sesión.
// 4) Cómo editarla: agrega manejo de errores por campo si backend amplía detalle.
async function guardarPerfil() {
    limpiarMensajes();

    if (!validarSeguridadAntesDeGuardar()) {
        return;
    }

    guardandoPerfil.value = true;
    try {
        const payload = construirPayloadActualizacion();
        const { data } = await actualizarPerfilPropio(payload);
        const datosPerfil = data?.data || {};

        hidratarPerfil(datosPerfil);
        limpiarVistaPrevia();

        sesionStore.actualizarUsuarioSesion({
            nombre: datosPerfil.nombre,
            username: datosPerfil.username,
            correo: datosPerfil.correo,
            sucursal_nombre: datosPerfil.sucursal_nombre,
            foto_perfil_url: datosPerfil.foto_perfil_url,
            requiere_cambio_password: !!datosPerfil.requiere_cambio_password
        });

        formularioSeguridad.password_actual = '';
        formularioSeguridad.password_nueva = '';
        formularioSeguridad.password_confirmacion = '';

        if (referenciaInputImagen.value) {
            referenciaInputImagen.value.value = '';
        }

        mensajeExito.value = data?.message || 'Perfil actualizado correctamente.';
    } catch (error) {
        const erroresCampo = error?.response?.data?.data;
        if (erroresCampo && typeof erroresCampo === 'object') {
            const primerError = Object.values(erroresCampo).flat().find(Boolean);
            mensajeError.value = primerError || error?.response?.data?.message || 'No se pudo actualizar el perfil.';
        } else {
            mensajeError.value = error?.response?.data?.message || 'No se pudo actualizar el perfil.';
        }
    } finally {
        guardandoPerfil.value = false;
    }
}

function desplazarASeguridadSiCorresponde() {
    if (window.location.hash === '#seguridad' || requiereCambioPasswordObligatorio.value) {
        referenciaSeccionSeguridad.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

onMounted(async () => {
    await cargarPerfil();
    desplazarASeguridadSiCorresponde();
});

onBeforeUnmount(() => {
    destruirInstanciaRecorte();
    limpiarImagenRecorteTemporal();
    limpiarVistaPrevia();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card relative overflow-hidden border border-surface-200 dark:border-surface-700">
            <div class="absolute inset-0 bg-gradient-to-r from-sky-500/10 via-cyan-500/10 to-emerald-500/10"></div>
            <div class="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div class="flex items-center gap-4">
                    <div class="relative h-20 w-20 shrink-0">
                        <img
                            v-if="urlImagenMostrada"
                            :src="urlImagenMostrada"
                            alt="Foto de perfil"
                            class="h-20 w-20 rounded-2xl border border-white/60 object-cover shadow-lg"
                        />
                        <div
                            v-else
                            class="flex h-20 w-20 items-center justify-center rounded-2xl bg-surface-900 text-xl font-bold text-white shadow-lg"
                        >
                            {{ inicialesUsuario }}
                        </div>
                    </div>
                    <div>
                        <h1 class="text-2xl font-semibold">Mi perfil</h1>
                        <p class="text-surface-600 dark:text-surface-300 mt-1">
                            Gestione su información de contacto, credenciales de acceso e imagen de perfil.
                        </p>
                        <div class="mt-2 flex flex-wrap gap-2">
                            <Tag v-for="rol in perfil.roles" :key="rol.id || rol.nombre" :value="rol.nombre" severity="contrast" />
                        </div>
                    </div>
                </div>
                <Button
                    icon="pi pi-save"
                    label="Guardar cambios"
                    :loading="guardandoPerfil"
                    @click="guardarPerfil"
                    class="w-full md:w-auto"
                />
            </div>
        </div>

        <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>
        <Message v-if="mensajeExito" severity="success" :closable="false">{{ mensajeExito }}</Message>
        <Message
            v-if="requiereCambioPasswordObligatorio"
            severity="error"
            :closable="false"
        >
            Acción requerida: debe actualizar su contraseña de acceso de forma inmediata para continuar operando en el sistema.
        </Message>

        <div v-if="cargandoPerfil" class="card">
            <div class="flex items-center gap-3 text-surface-600 dark:text-surface-300">
                <ProgressSpinner style="width: 1.6rem; height: 1.6rem" strokeWidth="6" />
                <span>Cargando información de perfil...</span>
            </div>
        </div>

        <template v-else>
            <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
                <article class="card xl:col-span-2 space-y-4">
                    <header>
                        <h2 class="text-xl font-semibold">Datos personales</h2>
                        <p class="text-surface-500 mt-1">El nombre completo es de solo lectura para garantizar la trazabilidad administrativa del sistema.</p>
                    </header>

                    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div>
                            <label class="mb-2 block text-sm">
                                <i class="pi pi-id-card mr-1 text-primary"></i>
                                Nombre completo <small class="text-surface-500">(no editable)</small>
                            </label>
                            <InputText v-model="perfil.nombre" class="w-full" disabled />
                        </div>

                        <div>
                            <label class="mb-2 block text-sm">
                                <i class="pi pi-user mr-1 text-primary"></i>
                                Usuario <small class="text-surface-500">(no editable)</small>
                            </label>
                            <InputText v-model="perfil.username" class="w-full" disabled />
                        </div>

                        <div>
                            <label class="mb-2 block text-sm">
                                <i class="pi pi-envelope mr-1 text-primary"></i>
                                Correo <small class="text-surface-500">(opcional)</small>
                            </label>
                            <InputText
                                v-model="perfil.correo"
                                class="w-full"
                                placeholder="usuario@empresa.com"
                                autocomplete="email"
                            />
                        </div>

                        <div>
                            <label class="mb-2 block text-sm">
                                <i class="pi pi-building mr-1 text-primary"></i>
                                Casino asignado <small class="text-surface-500">(informativo)</small>
                            </label>
                            <InputText :model-value="perfil.sucursal_nombre" class="w-full" disabled />
                        </div>
                    </div>
                </article>

                <aside class="card space-y-4">
                    <header>
                        <h2 class="text-xl font-semibold">Imagen de perfil</h2>
                        <p class="text-surface-500 mt-1">La imagen se vincula a su usuario y sucursal para fines de trazabilidad y auditoría.</p>
                    </header>

                    <div class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300 p-4 dark:border-surface-600">
                        <img
                            v-if="urlImagenMostrada"
                            :src="urlImagenMostrada"
                            alt="Vista previa imagen perfil"
                            class="h-28 w-28 rounded-2xl object-cover shadow"
                        />
                        <div
                            v-else
                            class="flex h-28 w-28 items-center justify-center rounded-2xl bg-surface-200 text-2xl font-bold text-surface-700 dark:bg-surface-700 dark:text-surface-100"
                        >
                            {{ inicialesUsuario }}
                        </div>

                        <input
                            ref="referenciaInputImagen"
                            type="file"
                            class="hidden"
                            accept="image/png,image/jpeg,image/webp"
                            @change="manejarCambioImagen"
                        />

                        <div class="flex w-full flex-col gap-2 sm:flex-row">
                            <Button icon="pi pi-image" label="Seleccionar" class="w-full" outlined @click="abrirSelectorImagen" />
                            <Button
                                icon="pi pi-trash"
                                label="Quitar"
                                class="w-full"
                                severity="secondary"
                                text
                                @click="quitarImagenPerfil"
                            />
                        </div>

                        <small class="text-center text-surface-500">Formatos aceptados: PNG, JPG o WEBP. La imagen se recorta en formato cuadrado antes de guardar.</small>
                    </div>
                </aside>
            </div>

            <article ref="referenciaSeccionSeguridad" class="card space-y-4" id="seguridad">
                <header>
                    <h2 class="text-xl font-semibold">Seguridad y contraseña</h2>
                    <p class="text-surface-500 mt-1">
                        {{ requiereCambioPasswordObligatorio ? 'Tu acceso está bloqueado hasta que cambies tu contraseña.' : 'Si no deseas cambiar contraseña, deja estos campos vacíos.' }}
                    </p>
                </header>

                <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div>
                        <label class="mb-2 block text-sm">
                            <i class="pi pi-lock mr-1 text-primary"></i>
                            Contraseña actual <small class="text-surface-500">(obligatorio para cambiar)</small>
                        </label>
                        <Password
                            v-model="formularioSeguridad.password_actual"
                            :feedback="false"
                            toggleMask
                            inputClass="w-full"
                            class="w-full"
                            placeholder="Escribe tu contraseña actual"
                            autocomplete="current-password"
                        />
                    </div>

                    <div>
                        <label class="mb-2 block text-sm">
                            <i class="pi pi-key mr-1 text-primary"></i>
                            Nueva contraseña <small class="text-surface-500">(obligatorio para cambiar)</small>
                        </label>
                        <Password
                            v-model="formularioSeguridad.password_nueva"
                            toggleMask
                            inputClass="w-full"
                            class="w-full"
                            placeholder="Escribe tu nueva contraseña"
                            autocomplete="new-password"
                        />
                    </div>

                    <div>
                        <label class="mb-2 block text-sm">
                            <i class="pi pi-check-circle mr-1 text-primary"></i>
                            Confirmar contraseña <small class="text-surface-500">(obligatorio para cambiar)</small>
                        </label>
                        <Password
                            v-model="formularioSeguridad.password_confirmacion"
                            :feedback="false"
                            toggleMask
                            inputClass="w-full"
                            class="w-full"
                            placeholder="Confirma tu nueva contraseña"
                            autocomplete="new-password"
                        />
                    </div>
                </div>
            </article>
        </template>

        <Dialog
            v-model:visible="mostrarDialogoRecorte"
            modal
            :dismissableMask="false"
            :closable="false"
            header="Recortar imagen de perfil"
            :style="{ width: 'min(94vw, 46rem)' }"
        >
            <div class="space-y-4">
                <p class="text-sm text-surface-600 dark:text-surface-300">
                    Ajusta tu imagen en formato cuadrado para mantener un avatar limpio y consistente en toda la plataforma.
                </p>

                <div class="contenedor-recorte">
                    <img
                        v-if="urlImagenRecorteTemporal"
                        ref="referenciaImagenRecorte"
                        :src="urlImagenRecorteTemporal"
                        alt="Imagen para recortar"
                        class="imagen-recorte"
                        @load="manejarImagenListaParaRecorte"
                    />
                </div>

                <div class="flex flex-wrap gap-2">
                    <Button icon="pi pi-search-plus" label="Acercar" outlined size="small" @click="acercarRecorte" />
                    <Button icon="pi pi-search-minus" label="Alejar" outlined size="small" @click="alejarRecorte" />
                    <Button icon="pi pi-refresh" label="Rotar" outlined size="small" @click="rotarRecorte" />
                    <Button icon="pi pi-replay" label="Reiniciar" text size="small" @click="reiniciarRecorte" />
                </div>

                <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
                    <Button label="Cancelar" severity="secondary" text @click="cancelarRecorteImagen" />
                    <Button label="Aplicar recorte" icon="pi pi-check" @click="aplicarRecorteImagen" />
                </div>
            </div>
        </Dialog>
    </section>
</template>

<style scoped>
.contenedor-recorte {
    max-height: min(56vh, 26rem);
    min-height: 15rem;
    overflow: hidden;
    border-radius: 0.9rem;
    border: 1px solid color-mix(in srgb, var(--surface-border) 80%, transparent);
    background: color-mix(in srgb, var(--surface-100) 92%, white 8%);
}

.imagen-recorte {
    display: block;
    max-width: 100%;
}
</style>