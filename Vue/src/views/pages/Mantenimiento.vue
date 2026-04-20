<script setup>
import {
    ESTADO_APLICACION,
    estaBypassMantenimientoActivo,
    sincronizarEstadoAplicacion
} from '@/utils/estadoAplicacion';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const segundosRestantes = ref(null);
const referenciaInicioLocal = ref(new Date());
let identificadorIntervalo = null;
let identificadorIntervaloSincronizacion = null;
let sincronizandoEstado = false;
let liberacionAutomaticaLocalAplicada = false;

const CLASES_POR_ESTADO = {
    mantenimiento_general: {
        tarjeta: 'border-amber-300 bg-amber-50/70',
        burbujaIcono: 'bg-amber-100 text-amber-700',
        barraProgreso: 'bg-amber-500',
        panelDecoradores: 'border-amber-200 bg-amber-50',
        panelTemporizador: 'border-amber-200 bg-amber-50',
        textoAcento: 'text-amber-900'
    },
    actualizacion_software: {
        tarjeta: 'border-sky-300 bg-sky-50/70',
        burbujaIcono: 'bg-sky-100 text-sky-700',
        barraProgreso: 'bg-sky-500',
        panelDecoradores: 'border-sky-200 bg-sky-50',
        panelTemporizador: 'border-sky-200 bg-sky-50',
        textoAcento: 'text-sky-900'
    },
    mantenimiento_infraestructura: {
        tarjeta: 'border-violet-300 bg-violet-50/70',
        burbujaIcono: 'bg-violet-100 text-violet-700',
        barraProgreso: 'bg-violet-500',
        panelDecoradores: 'border-violet-200 bg-violet-50',
        panelTemporizador: 'border-violet-200 bg-violet-50',
        textoAcento: 'text-violet-900'
    },
    migracion_datos: {
        tarjeta: 'border-emerald-300 bg-emerald-50/70',
        burbujaIcono: 'bg-emerald-100 text-emerald-700',
        barraProgreso: 'bg-emerald-500',
        panelDecoradores: 'border-emerald-200 bg-emerald-50',
        panelTemporizador: 'border-emerald-200 bg-emerald-50',
        textoAcento: 'text-emerald-900'
    },
    contingencia_operativa: {
        tarjeta: 'border-rose-300 bg-rose-50/70',
        burbujaIcono: 'bg-rose-100 text-rose-700',
        barraProgreso: 'bg-rose-500',
        panelDecoradores: 'border-rose-200 bg-rose-50',
        panelTemporizador: 'border-rose-200 bg-rose-50',
        textoAcento: 'text-rose-900'
    }
};

const estadoPorDefecto = {
    titulo: 'Mantenimiento del sistema',
    mensaje: 'Estamos aplicando ajustes operativos para estabilizar el servicio.',
    etiqueta: 'Operación interna',
    icono: 'pi pi-cog',
    decoradores: ['Revisión técnica'],
    recomendaciones: ['Espera la reactivación programada.']
};

function normalizarClaveEstado(valor) {
    return String(valor || '')
        .trim()
        .toLowerCase();
}

function construirFecha(fechaTexto, horaTexto) {
    const fecha = String(fechaTexto || '').trim();
    const hora = String(horaTexto || '').trim();
    if (!fecha || !hora) {
        return null;
    }

    const fechaConstruida = new Date(`${fecha}T${hora}`);
    if (Number.isNaN(fechaConstruida.getTime())) {
        return null;
    }

    return fechaConstruida;
}

const catalogoEstados = computed(() => {
    return ESTADO_APLICACION.estadosDisponibles || {};
});

const claveEstadoActual = computed(() => {
    const clave = normalizarClaveEstado(ESTADO_APLICACION.estadoActual);
    if (catalogoEstados.value[clave]) {
        return clave;
    }
    return 'mantenimiento_general';
});

const estadoActivo = computed(() => {
    return catalogoEstados.value[claveEstadoActual.value] || estadoPorDefecto;
});

const clasesEstadoActivo = computed(() => {
    return CLASES_POR_ESTADO[claveEstadoActual.value] || CLASES_POR_ESTADO.mantenimiento_general;
});

const alertaConexionBdVisible = computed(() => Boolean(ESTADO_APLICACION.alertaConexionBdVisible));

const alertaConexionBdMensaje = computed(() => {
    return String(ESTADO_APLICACION.alertaConexionBdMensaje || '').trim();
});

const fechaReactivacionProgramada = computed(() => {
    const configuracionTemporizador = ESTADO_APLICACION.temporizadorReactivacion || {};
    if (!configuracionTemporizador.habilitar) {
        return null;
    }

    return construirFecha(configuracionTemporizador.fecha, configuracionTemporizador.hora);
});

const fechaInicioProgramada = computed(() => {
    const configuracionTemporizador = ESTADO_APLICACION.temporizadorReactivacion || {};
    return construirFecha(configuracionTemporizador.fechaInicio, configuracionTemporizador.horaInicio);
});

const temporizadorVisible = computed(() => Boolean(fechaReactivacionProgramada.value));

const fechaReactivacionTexto = computed(() => {
    if (!fechaReactivacionProgramada.value) {
        return '';
    }

    return fechaReactivacionProgramada.value.toLocaleString('es-MX', {
        dateStyle: 'full',
        timeStyle: 'medium'
    });
});

const cuentaRegresiva = computed(() => {
    if (segundosRestantes.value === null || segundosRestantes.value < 0) {
        return null;
    }

    const totalSegundos = segundosRestantes.value;
    const dias = Math.floor(totalSegundos / 86400);
    const horas = Math.floor((totalSegundos % 86400) / 3600);
    const minutos = Math.floor((totalSegundos % 3600) / 60);
    const segundos = totalSegundos % 60;
    return { dias, horas, minutos, segundos };
});

const reactivacionAlcanzada = computed(() => {
    if (!temporizadorVisible.value) {
        return false;
    }

    return segundosRestantes.value !== null && segundosRestantes.value <= 0;
});

const porcentajeProgreso = computed(() => {
    if (!temporizadorVisible.value || segundosRestantes.value === null) {
        return 0;
    }

    const fechaFin = fechaReactivacionProgramada.value;
    let fechaInicio = fechaInicioProgramada.value;
    if (!fechaInicio || fechaInicio.getTime() >= fechaFin.getTime()) {
        fechaInicio = referenciaInicioLocal.value;
    }

    const totalSegundos = Math.max(1, Math.floor((fechaFin.getTime() - fechaInicio.getTime()) / 1000));
    const segundosTranscurridos = Math.max(0, Math.min(totalSegundos, totalSegundos - segundosRestantes.value));
    return Math.round((segundosTranscurridos / totalSegundos) * 100);
});

function darFormatoDosDigitos(valor) {
    return String(valor).padStart(2, '0');
}

function actualizarCuentaRegresiva() {
    if (!fechaReactivacionProgramada.value) {
        segundosRestantes.value = null;
        return;
    }

    const diferenciaMilisegundos = fechaReactivacionProgramada.value.getTime() - Date.now();
    segundosRestantes.value = Math.max(0, Math.floor(diferenciaMilisegundos / 1000));

    if (segundosRestantes.value <= 0 && !liberacionAutomaticaLocalAplicada) {
        liberacionAutomaticaLocalAplicada = true;
        ESTADO_APLICACION.modoMantenimiento = false;
        router.replace('/');
    }
}

function iniciarTemporizador() {
    referenciaInicioLocal.value = new Date();
    actualizarCuentaRegresiva();

    if (identificadorIntervalo) {
        clearInterval(identificadorIntervalo);
    }

    if (!temporizadorVisible.value) {
        return;
    }

    identificadorIntervalo = setInterval(() => {
        actualizarCuentaRegresiva();
    }, 1000);
}

async function sincronizarEstadoMantenimiento(forzar = false) {
    if (sincronizandoEstado) {
        return;
    }

    sincronizandoEstado = true;
    try {
        await sincronizarEstadoAplicacion({ forzar });
        if (!ESTADO_APLICACION.modoMantenimiento || estaBypassMantenimientoActivo()) {
            await router.replace('/');
        }
    } finally {
        sincronizandoEstado = false;
    }
}

async function manejarBypassActivado() {
    if (estaBypassMantenimientoActivo()) {
        await router.replace('/');
    }
}

onMounted(() => {
    liberacionAutomaticaLocalAplicada = false;
    iniciarTemporizador();

    sincronizarEstadoMantenimiento(true);
    identificadorIntervaloSincronizacion = setInterval(() => {
        sincronizarEstadoMantenimiento(false);
    }, 15000);

    window.addEventListener('binsur:bypass-mantenimiento-activado', manejarBypassActivado);
});

onBeforeUnmount(() => {
    if (identificadorIntervalo) {
        clearInterval(identificadorIntervalo);
    }

    if (identificadorIntervaloSincronizacion) {
        clearInterval(identificadorIntervaloSincronizacion);
    }

    window.removeEventListener('binsur:bypass-mantenimiento-activado', manejarBypassActivado);
});
</script>

<template>
    <div class="min-h-screen bg-surface-100 flex items-center justify-center p-4">
        <section :class="['w-full max-w-3xl rounded-3xl border shadow-xl p-6 sm:p-10', clasesEstadoActivo.tarjeta]">
            <div class="flex items-start gap-4">
                <div :class="['h-14 w-14 rounded-2xl flex items-center justify-center text-2xl shrink-0', clasesEstadoActivo.burbujaIcono]">
                    <i :class="estadoActivo.icono"></i>
                </div>
                <div>
                    <p class="text-xs uppercase tracking-widest text-surface-600 font-semibold">Estado operativo &mdash; fuera de servicio</p>
                    <h1 class="text-3xl sm:text-4xl font-extrabold text-surface-900 mt-1">
                        {{ estadoActivo.titulo }}
                    </h1>
                    <p class="text-sm text-surface-600 mt-2">{{ estadoActivo.etiqueta }}</p>
                </div>
            </div>

            <p class="text-surface-700 mt-3 text-base sm:text-lg leading-relaxed">
                {{ estadoActivo.mensaje }}
            </p>

            <div v-if="alertaConexionBdVisible" class="mt-4 rounded-2xl border border-red-300 bg-red-50 p-4 sm:p-5">
                <div class="flex items-start gap-3">
                    <i class="pi pi-database text-red-700 text-xl mt-0.5"></i>
                    <div>
                        <h2 class="font-semibold text-red-800">Alerta de infraestructura</h2>
                        <p class="text-sm text-red-700 mt-1">
                            {{ alertaConexionBdMensaje }}
                        </p>
                    </div>
                </div>
            </div>

            <div :class="['mt-5 rounded-2xl border p-4 sm:p-5', clasesEstadoActivo.panelDecoradores]">
                <h2 :class="['font-semibold mb-3', clasesEstadoActivo.textoAcento]">Alcance de la intervención</h2>
                <div class="flex flex-wrap gap-2">
                    <span
                        v-for="(decorador, indiceDecorador) in estadoActivo.decoradores"
                        :key="`${indiceDecorador}-${decorador}`"
                        class="inline-flex items-center gap-2 rounded-full border border-surface-300 bg-surface-0 px-3 py-1 text-xs text-surface-700"
                    >
                        <i class="pi pi-sparkles"></i>
                        {{ decorador }}
                    </span>
                </div>
            </div>

            <div v-if="temporizadorVisible" :class="['mt-6 rounded-2xl border p-4 sm:p-5', clasesEstadoActivo.panelTemporizador]">
                <div class="flex items-center justify-between gap-3 flex-wrap">
                    <h2 :class="['font-semibold', clasesEstadoActivo.textoAcento]">Reactivación estimada</h2>
                    <Tag :value="reactivacionAlcanzada ? 'Tiempo cumplido' : 'Cuenta regresiva'" :severity="reactivacionAlcanzada ? 'success' : 'warn'" />
                </div>
                <p :class="['text-sm mt-2', clasesEstadoActivo.textoAcento]">
                    Fecha tentativa de reactivación: {{ fechaReactivacionTexto }}
                </p>

                <div class="mt-4">
                    <div class="h-3 w-full rounded-full bg-surface-200 overflow-hidden">
                        <div
                            :class="['h-full transition-all duration-700', clasesEstadoActivo.barraProgreso]"
                            :style="{ width: `${porcentajeProgreso}%` }"
                        ></div>
                    </div>
                    <p class="mt-2 text-xs text-surface-600">Progreso estimado de la actualización: {{ porcentajeProgreso }}%</p>
                </div>

                <div v-if="cuentaRegresiva && !reactivacionAlcanzada" class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div class="rounded-xl border border-surface-200 bg-surface-0 p-3 text-center">
                        <p :class="['text-2xl font-extrabold', clasesEstadoActivo.textoAcento]">{{ cuentaRegresiva.dias }}</p>
                        <small class="text-surface-600">Días</small>
                    </div>
                    <div class="rounded-xl border border-surface-200 bg-surface-0 p-3 text-center">
                        <p :class="['text-2xl font-extrabold', clasesEstadoActivo.textoAcento]">{{ darFormatoDosDigitos(cuentaRegresiva.horas) }}</p>
                        <small class="text-surface-600">Horas</small>
                    </div>
                    <div class="rounded-xl border border-surface-200 bg-surface-0 p-3 text-center">
                        <p :class="['text-2xl font-extrabold', clasesEstadoActivo.textoAcento]">{{ darFormatoDosDigitos(cuentaRegresiva.minutos) }}</p>
                        <small class="text-surface-600">Minutos</small>
                    </div>
                    <div class="rounded-xl border border-surface-200 bg-surface-0 p-3 text-center">
                        <p :class="['text-2xl font-extrabold', clasesEstadoActivo.textoAcento]">{{ darFormatoDosDigitos(cuentaRegresiva.segundos) }}</p>
                        <small class="text-surface-600">Segundos</small>
                    </div>
                </div>

                <div v-else class="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                    La fecha y hora de reactivación ya se alcanzaron.
                </div>
            </div>

            <div class="mt-6 rounded-2xl border border-surface-200 bg-surface-50 p-4 sm:p-5">
                <h2 class="font-semibold text-surface-900 mb-3">Acciones recomendadas</h2>
                <ul class="space-y-2 text-surface-700">
                    <li v-for="(recomendacion, indice) in estadoActivo.recomendaciones" :key="`${indice}-${recomendacion}`" class="flex items-start gap-2">
                        <i class="pi pi-check-circle text-emerald-500 mt-1"></i>
                        <span>{{ recomendacion }}</span>
                    </li>
                </ul>
            </div>
        </section>
    </div>
</template>

