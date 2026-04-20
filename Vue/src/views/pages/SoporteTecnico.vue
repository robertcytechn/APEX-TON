<script setup>
import { enviarSolicitudSoporteTecnico } from '@/service/soporteTecnicoServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, reactive, ref } from 'vue';

const sesionStore = useSesionStore();

const contactoPrincipal = {
    nombre: 'José Roberto Tamayo Montejano',
    whatsapp: '4437160182',
    telefonoAlterno: '7201734661',
    correoPrincipal: 'robert-cyby@hotmail.com',
    correoCopia: 'robertot@gbentretenimiento.com'
};

const opcionesProblemaPrincipal = [
    { label: 'No puedo iniciar sesión o perdí acceso', value: 'ACCESO' },
    { label: 'Error en captura operativa', value: 'CAPTURA' },
    { label: 'Inconsistencia en reportes o estadísticas', value: 'REPORTES' },
    { label: 'Pantalla lenta o bloqueada', value: 'RENDIMIENTO' },
    { label: 'Problema con correo, exportación o integración', value: 'INTEGRACION' },
    { label: 'Otro problema técnico', value: 'OTRO' }
];

const opcionesAreasAfectadas = [
    { label: 'Inicio de sesión y perfil', value: 'LOGIN' },
    { label: 'Panel de inicio', value: 'INICIO' },
    { label: 'Captura operativa', value: 'CAPTURA_OPERATIVA' },
    { label: 'Reporte diario', value: 'REPORTE_DIARIO' },
    { label: 'Estado de resultados', value: 'ESTADO_RESULTADOS' },
    { label: 'Estadísticas y gráficas', value: 'ESTADISTICAS' },
    { label: 'Módulo administrativo', value: 'ADMIN' },
    { label: 'Cabina director', value: 'DIRECTOR' },
    { label: 'Módulo de soporte', value: 'SOPORTE' },
    { label: 'Otra área', value: 'OTRA' }
];

const opcionesComportamiento = [
    { label: 'No carga / se queda pensando', value: 'NO_CARGA' },
    { label: 'Error visual o de maquetación', value: 'ERROR_VISUAL' },
    { label: 'Mensaje de validación inesperado', value: 'ERROR_VALIDACION' },
    { label: 'No tengo permisos en una acción esperada', value: 'ERROR_PERMISOS' },
    { label: 'Datos incorrectos o incompletos', value: 'DATOS_INCORRECTOS' },
    { label: 'Se cierra sesión inesperadamente', value: 'CIERRE_SESION' },
    { label: 'Otro comportamiento', value: 'OTRO' }
];

const opcionesPrioridad = [
    { label: 'Baja', value: 'BAJA' },
    { label: 'Media', value: 'MEDIA' },
    { label: 'Alta', value: 'ALTA' },
    { label: 'Crítica', value: 'CRITICA' }
];

const opcionesDispositivo = [
    { label: 'Equipo de escritorio', value: 'ESCRITORIO' },
    { label: 'Laptop', value: 'LAPTOP' },
    { label: 'Tablet', value: 'TABLET' },
    { label: 'Móvil', value: 'MOVIL' },
    { label: 'No aplica', value: 'NO_APLICA' }
];

const formulario = reactive({
    problema_principal: null,
    areas_afectadas: [],
    comportamiento_observado: null,
    prioridad: 'MEDIA',
    dispositivo: 'ESCRITORIO',
    pagina_afectada: '',
    descripcion_detallada: '',
    pasos_reproduccion: '',
    bloqueo_operativo: false
});

const estadoEnvio = reactive({
    tipo: '',
    mensaje: '',
    folio: ''
});

const errores = ref({});
const enviandoSolicitud = ref(false);

const usuarioActual = computed(() => sesionStore.usuario || {});
const nombreUsuario = computed(() => usuarioActual.value.nombre || usuarioActual.value.username || 'Usuario autenticado');
const correoUsuario = computed(() => usuarioActual.value.correo || 'No capturado en tu perfil');
const puedeVerTarjetaResponsable = computed(() => {
    const roles = Array.isArray(sesionStore.roles) ? sesionStore.roles : [];
    return roles.some((rol) => {
        const nombreRol = String(rol?.nombre || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .trim()
            .toUpperCase();
        return nombreRol.includes('DIRECTOR') || nombreRol.includes('ADMINISTRADOR');
    });
});

function formatoVisibleTelefono(numero) {
    const limpio = String(numero || '').replace(/\D/g, '');
    if (limpio.length !== 10) {
        return numero;
    }
    return `${limpio.slice(0, 3)} ${limpio.slice(3, 6)} ${limpio.slice(6, 10)}`;
}

function enlaceWhatsapp(numero) {
    const limpio = String(numero || '').replace(/\D/g, '');
    return `https://wa.me/52${limpio}`;
}

function enlaceLlamada(numero) {
    const limpio = String(numero || '').replace(/\D/g, '');
    return `tel:+52${limpio}`;
}

function enlaceCorreo(correo) {
    return `mailto:${correo}`;
}

function limpiarEstadoEnvio() {
    estadoEnvio.tipo = '';
    estadoEnvio.mensaje = '';
    estadoEnvio.folio = '';
}

function reiniciarFormulario() {
    formulario.problema_principal = null;
    formulario.areas_afectadas = [];
    formulario.comportamiento_observado = null;
    formulario.prioridad = 'MEDIA';
    formulario.dispositivo = 'ESCRITORIO';
    formulario.pagina_afectada = '';
    formulario.descripcion_detallada = '';
    formulario.pasos_reproduccion = '';
    formulario.bloqueo_operativo = false;
}

function registrarErrorCampo(clave, mensaje) {
    errores.value = {
        ...errores.value,
        [clave]: mensaje
    };
}

function validarFormulario() {
    errores.value = {};

    if (!formulario.problema_principal) {
        registrarErrorCampo('problema_principal', 'Selecciona el tipo de problema principal.');
    }

    if (!Array.isArray(formulario.areas_afectadas) || formulario.areas_afectadas.length === 0) {
        registrarErrorCampo('areas_afectadas', 'Selecciona al menos un área afectada.');
    }

    if (!formulario.comportamiento_observado) {
        registrarErrorCampo('comportamiento_observado', 'Selecciona el comportamiento observado.');
    }

    const descripcion = String(formulario.descripcion_detallada || '').trim();
    if (!descripcion) {
        registrarErrorCampo('descripcion_detallada', 'Captura una descripción detallada de la incidencia.');
    } else if (descripcion.length < 20) {
        registrarErrorCampo('descripcion_detallada', 'La descripción debe contener al menos 20 caracteres.');
    }

    return Object.keys(errores.value).length === 0;
}

function recolectarMensajesError(payloadData) {
    const mensajes = [];

    if (!payloadData || typeof payloadData !== 'object') {
        return mensajes;
    }

    Object.entries(payloadData).forEach(([campo, valor]) => {
        if (Array.isArray(valor)) {
            valor.forEach((texto) => {
                if (texto) {
                    mensajes.push(`${campo}: ${texto}`);
                }
            });
            return;
        }

        if (typeof valor === 'string' && valor.trim()) {
            mensajes.push(`${campo}: ${valor.trim()}`);
        }
    });

    return mensajes;
}

async function enviarFormularioSoporte() {
    limpiarEstadoEnvio();
    if (!validarFormulario() || enviandoSolicitud.value) {
        return;
    }

    enviandoSolicitud.value = true;
    try {
        const payload = {
            problema_principal: formulario.problema_principal,
            areas_afectadas: formulario.areas_afectadas,
            comportamiento_observado: formulario.comportamiento_observado,
            prioridad: formulario.prioridad,
            dispositivo: formulario.dispositivo,
            pagina_afectada: formulario.pagina_afectada,
            descripcion_detallada: formulario.descripcion_detallada,
            pasos_reproduccion: formulario.pasos_reproduccion,
            bloqueo_operativo: formulario.bloqueo_operativo
        };

        const respuesta = await enviarSolicitudSoporteTecnico(payload);
        const mensaje = respuesta?.data?.message || 'Solicitud enviada correctamente.';
        const folio = respuesta?.data?.data?.folio || '';

        estadoEnvio.tipo = 'success';
        estadoEnvio.mensaje = mensaje;
        estadoEnvio.folio = folio;

        reiniciarFormulario();
    } catch (error) {
        const mensajeBackend = error?.response?.data?.message || error?.response?.data?.detail || 'No se pudo enviar tu solicitud de soporte.';
        const mensajesCampos = recolectarMensajesError(error?.response?.data?.data);
        estadoEnvio.tipo = 'error';
        estadoEnvio.mensaje = mensajesCampos.length > 0 ? `${mensajeBackend} ${mensajesCampos.join(' | ')}` : mensajeBackend;
    } finally {
        enviandoSolicitud.value = false;
    }
}
</script>

<template>
    <section class="space-y-4">
        <div class="card border border-surface-200/80 dark:border-surface-700/80 overflow-hidden">
            <div class="rounded-xl p-6 bg-[linear-gradient(120deg,#0f172a_0%,#1e293b_45%,#0f766e_100%)] text-white">
                <small class="uppercase tracking-widest text-white/80">Soporte de aplicación</small>
                <h1 class="text-2xl sm:text-3xl font-semibold mt-2">Mesa de ayuda técnica</h1>
                <p class="text-white/85 mt-2">
                    Reporta incidencias operativas y técnicas desde este formulario. El ticket se envía por correo al equipo de soporte.
                </p>
            </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-12 gap-4">
            <div class="card space-y-4" :class="puedeVerTarjetaResponsable ? 'xl:col-span-8' : 'xl:col-span-12'">
                <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h2 class="text-xl font-semibold">Formulario de solicitud</h2>
                        <small class="text-surface-500">Campos marcados con * son obligatorios.</small>
                    </div>
                    <Tag severity="info" value="Disponible para todo usuario con sesión activa" />
                </div>

                <Message
                    v-if="estadoEnvio.mensaje"
                    :severity="estadoEnvio.tipo === 'success' ? 'success' : 'error'"
                    :closable="false"
                >
                    {{ estadoEnvio.mensaje }}
                    <template v-if="estadoEnvio.folio">
                        Folio: <strong>{{ estadoEnvio.folio }}</strong>
                    </template>
                </Message>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm font-medium mb-1">Nombre del usuario</label>
                        <InputText :modelValue="nombreUsuario" class="w-full" readonly />
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Correo del usuario</label>
                        <InputText :modelValue="correoUsuario" class="w-full" readonly />
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-sm font-medium mb-1">Problema principal *</label>
                        <Select
                            v-model="formulario.problema_principal"
                            :options="opcionesProblemaPrincipal"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Selecciona una opción"
                            filter
                            filterPlaceholder="Buscar problema..."
                        />
                        <small v-if="errores.problema_principal" class="text-red-500">{{ errores.problema_principal }}</small>
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Comportamiento observado *</label>
                        <Select
                            v-model="formulario.comportamiento_observado"
                            :options="opcionesComportamiento"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Selecciona una opción"
                            filter
                            filterPlaceholder="Buscar comportamiento..."
                        />
                        <small v-if="errores.comportamiento_observado" class="text-red-500">{{ errores.comportamiento_observado }}</small>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1">Áreas afectadas *</label>
                    <MultiSelect
                        v-model="formulario.areas_afectadas"
                        :options="opcionesAreasAfectadas"
                        optionLabel="label"
                        optionValue="value"
                        display="chip"
                        class="w-full"
                        placeholder="Selecciona una o más áreas"
                        filter
                        filterPlaceholder="Buscar área..."
                    />
                    <small v-if="errores.areas_afectadas" class="text-red-500">{{ errores.areas_afectadas }}</small>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-sm font-medium mb-1">Prioridad</label>
                        <Select v-model="formulario.prioridad" :options="opcionesPrioridad" optionLabel="label" optionValue="value" class="w-full" />
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Dispositivo</label>
                        <Select v-model="formulario.dispositivo" :options="opcionesDispositivo" optionLabel="label" optionValue="value" class="w-full" />
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Página afectada</label>
                        <InputText v-model="formulario.pagina_afectada" class="w-full" placeholder="Ej. /reportes/reporte-diario" />
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1">Descripción detallada *</label>
                    <Textarea
                        v-model="formulario.descripcion_detallada"
                        rows="5"
                        class="w-full"
                        placeholder="Describe qué estabas haciendo, qué esperabas y qué ocurrió realmente."
                    />
                    <small class="text-surface-500">Mínimo 20 caracteres.</small>
                    <small v-if="errores.descripcion_detallada" class="block text-red-500">{{ errores.descripcion_detallada }}</small>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1">Pasos para reproducir (opcional)</label>
                    <Textarea
                        v-model="formulario.pasos_reproduccion"
                        rows="4"
                        class="w-full"
                        placeholder="1) Entré a... 2) Capturé... 3) Presioné guardar..."
                    />
                </div>

                <div class="flex items-center gap-2">
                    <Checkbox v-model="formulario.bloqueo_operativo" binary inputId="bloqueo_operativo" />
                    <label for="bloqueo_operativo" class="text-sm">Este problema bloquea mi operación diaria</label>
                </div>

                <div class="flex justify-end">
                    <Button
                        label="Enviar solicitud"
                        icon="pi pi-send"
                        :loading="enviandoSolicitud"
                        @click="enviarFormularioSoporte"
                    />
                </div>
            </div>

            <div v-if="puedeVerTarjetaResponsable" class="card xl:col-span-4 space-y-3">
                <div>
                    <small class="text-surface-500">Responsable</small>
                    <h2 class="text-lg font-semibold mt-1">{{ contactoPrincipal.nombre }}</h2>
                </div>

                <a
                    :href="enlaceWhatsapp(contactoPrincipal.whatsapp)"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="block rounded-lg border border-emerald-300/70 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-700/60 p-3 transition-colors hover:border-emerald-500"
                >
                    <p class="font-semibold"><i class="pi pi-whatsapp mr-2 text-emerald-600"></i>WhatsApp principal</p>
                    <small class="text-surface-500">{{ formatoVisibleTelefono(contactoPrincipal.whatsapp) }}</small>
                </a>

                <a
                    :href="enlaceWhatsapp(contactoPrincipal.telefonoAlterno)"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="block rounded-lg border border-sky-300/70 bg-sky-50 dark:bg-sky-950/20 dark:border-sky-700/60 p-3 transition-colors hover:border-sky-500"
                >
                    <p class="font-semibold"><i class="pi pi-comments mr-2 text-sky-600"></i>WhatsApp alterno</p>
                    <small class="text-surface-500">{{ formatoVisibleTelefono(contactoPrincipal.telefonoAlterno) }}</small>
                </a>

                <a
                    :href="enlaceLlamada(contactoPrincipal.telefonoAlterno)"
                    class="block rounded-lg border border-surface-300 dark:border-surface-700 p-3 transition-colors hover:border-primary"
                >
                    <p class="font-semibold"><i class="pi pi-phone mr-2 text-primary"></i>Llamada directa</p>
                    <small class="text-surface-500">{{ formatoVisibleTelefono(contactoPrincipal.telefonoAlterno) }}</small>
                </a>

                <a
                    :href="enlaceCorreo(contactoPrincipal.correoPrincipal)"
                    class="block rounded-lg border border-surface-300 dark:border-surface-700 p-3 transition-colors hover:border-primary"
                >
                    <p class="font-semibold">Correo destino</p>
                    <small class="text-surface-500 break-all">{{ contactoPrincipal.correoPrincipal }}</small>
                </a>

                <a
                    :href="enlaceCorreo(contactoPrincipal.correoCopia)"
                    class="block rounded-lg border border-surface-300 dark:border-surface-700 p-3 transition-colors hover:border-primary"
                >
                    <p class="font-semibold">Correo en copia</p>
                    <small class="text-surface-500 break-all">{{ contactoPrincipal.correoCopia }}</small>
                </a>

                <Message severity="info" :closable="false">
                    Este canal está disponible para cualquier usuario con sesión activa.
                </Message>
            </div>
        </div>
    </section>
</template>
