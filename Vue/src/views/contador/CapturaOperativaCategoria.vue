<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import {
    eliminarMovimientoDiario,
    establecerSaldoInicialCategoriaManual,
    guardarCapturaRapida,
    listarConfiguracionesGlobales,
    listarMovimientosDiarios,
    obtenerCategoriaOperativa,
    obtenerReporteDiarioPorFecha,
    obtenerSaldoInicialCategoriaMensual
} from '@/service/capturaOperativaServicio';
import { cerrarDiaContableActual } from '@/service/reporteDiarioServicio';
import { useSesionStore } from '@/stores/sesion';
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const sesionStore = useSesionStore();

const cargando = ref(false);
const cargandoGuardado = ref(false);
const categoria = ref(null);
const reporteActual = ref(null);
const movimientosExistentes = ref([]);
const conceptosAdicionalesSeleccionados = ref([]);
const conceptoNoRecurrenteSeleccionado = ref(null);
const consecutivoFilaCaptura = ref(0);
const mensajePantalla = ref('');
const tasaCambioDolaresConfiguracion = ref(0);
const fechaContableSeleccionada = ref(null);
const cerrandoDiaContable = ref(false);
const mensajeCierreDiaContable = ref('');
const saldoInicialCategoriaMensual = ref(null);
const capturandoSaldoInicialManual = ref(false);
const mensajeSaldoInicialCategoria = ref('');
const montoSaldoInicialManual = ref(0);

const hoy = new Date();
const fechaContableMaxima = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);
const fechaContableMinima = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 6);

const capturasPorConcepto = reactive({});
const temporizadoresGuardado = new Map();
const temporizadoresEstado = new Map();
const intervaloMinutosCliente = ref(null);
const minutosActualesCliente = ref(0);
const resumenDiaBasePersistido = reactive({
    ingresos: 0,
    egresos: 0
});
const horarioOperacion = reactive({
    aperturaTexto: '',
    cierreTexto: '',
    minutosApertura: null,
    minutosCierre: null
});

// 1) Para qué sirve: traducir texto de hora (HH:MM o HH:MM:SS) a minutos del día.
// 2) Cómo funciona: parsea segmentos y valida rango de hora/minuto.
// 3) Qué hace: unifica comparaciones de ventana horaria en frontend.
// 4) Cómo editarla: adapta formato si el backend cambia la serialización de TIME.
function convertirHoraAMinutos(textoHora) {
    if (!textoHora) {
        return null;
    }

    const coincidencia = String(textoHora).trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (!coincidencia) {
        return null;
    }

    const hora = Number(coincidencia[1]);
    const minuto = Number(coincidencia[2]);
    if (!Number.isInteger(hora) || !Number.isInteger(minuto) || hora < 0 || hora > 23 || minuto < 0 || minuto > 59) {
        return null;
    }

    return (hora * 60) + minuto;
}

// 1) Para qué sirve: normalizar representación de hora en formato HH:MM.
// 2) Cómo funciona: parsea texto recibido y regresa hora/minuto con padding.
// 3) Qué hace: mejora legibilidad de mensajes de bloqueo por horario.
// 4) Cómo editarla: agrega segundos si en UX se requiere precisión adicional.
function normalizarHoraTexto(textoHora) {
    const minutos = convertirHoraAMinutos(textoHora);
    if (!Number.isInteger(minutos)) {
        return '';
    }

    const hora = Math.floor(minutos / 60);
    const minuto = minutos % 60;
    return `${String(hora).padStart(2, '0')}:${String(minuto).padStart(2, '0')}`;
}

// 1) Para qué sirve: extraer ventana de captura desde configuraciones globales.
// 2) Cómo funciona: busca HORARIO_APERTURA/HORARIO_CIERRE y convierte a minutos.
// 3) Qué hace: alimenta bloqueo preventivo de edición en la vista de captura.
// 4) Cómo editarla: ajusta claves buscadas si negocio renombra configuraciones.
function actualizarHorarioOperacionDesdeConfiguraciones(configuraciones) {
    const aperturaConfiguracion = configuraciones.find((item) => String(item?.clave || '').trim().toUpperCase() === 'HORARIO_APERTURA');
    const cierreConfiguracion = configuraciones.find((item) => String(item?.clave || '').trim().toUpperCase() === 'HORARIO_CIERRE');

    const horaAperturaCruda = aperturaConfiguracion?.valor_tipado ?? aperturaConfiguracion?.valor ?? '';
    const horaCierreCruda = cierreConfiguracion?.valor_tipado ?? cierreConfiguracion?.valor ?? '';

    horarioOperacion.aperturaTexto = normalizarHoraTexto(horaAperturaCruda);
    horarioOperacion.cierreTexto = normalizarHoraTexto(horaCierreCruda);
    horarioOperacion.minutosApertura = convertirHoraAMinutos(horarioOperacion.aperturaTexto);
    horarioOperacion.minutosCierre = convertirHoraAMinutos(horarioOperacion.cierreTexto);
}

// 1) Para qué sirve: refrescar minuto actual del cliente para bloqueo en tiempo real.
// 2) Cómo funciona: toma Date local y guarda hora*60 + minuto.
// 3) Qué hace: permite que la vista se bloquee/desbloquee sin recargar.
// 4) Cómo editarla: sincroniza con hora de servidor si se implementa endpoint dedicado.
function actualizarMinutoActualCliente() {
    const ahora = new Date();
    minutosActualesCliente.value = (ahora.getHours() * 60) + ahora.getMinutes();
}

// 1) Para qué sirve: evaluar si un minuto dado cae dentro de la ventana de captura.
// 2) Cómo funciona: soporta ventanas normales y ventanas que cruzan medianoche.
// 3) Qué hace: centraliza regla de horario para condiciones de bloqueo UI.
// 4) Cómo editarla: ajusta inclusión/exclusión de límites si negocio lo requiere.
function minutoDentroDeVentana(minutoActual, minutoApertura, minutoCierre) {
    if (!Number.isInteger(minutoApertura) || !Number.isInteger(minutoCierre)) {
        return true;
    }

    if (minutoApertura <= minutoCierre) {
        return minutoActual >= minutoApertura && minutoActual <= minutoCierre;
    }

    return minutoActual >= minutoApertura || minutoActual <= minutoCierre;
}

const sucursalId = computed(() => Number(sesionStore.usuario?.sucursal_id || 0));
const idCategoriaActual = computed(() => {
    const idParam = Number(route.params.categoriaId || 0);
    if (idParam > 0) {
        return idParam;
    }

    const coincidencia = (route.path || '').match(/\/operativo\/(\d+)\/?$/);
    if (coincidencia?.[1]) {
        return Number(coincidencia[1]);
    }

    return 0;
});

const detallesActivos = computed(() => {
    const detalles = categoria.value?.detalles_parametrizados || [];
    return detalles.filter((detalle) => detalle.estado === 'ACTIVO');
});

const categoriaPermiteConceptosDuplicados = computed(() => detallesActivos.value.length > 0);

const conceptosActivos = computed(() => {
    const conceptos = categoria.value?.conceptos || [];
    return conceptos.filter((concepto) => concepto.estado === 'ACTIVO');
});

const conceptosRecurrentes = computed(() => conceptosActivos.value.filter((concepto) => !!concepto.es_recurrente));

const conceptosNoRecurrentesDisponibles = computed(() => {
    const conceptosConFilas = new Set(
        (conceptosAdicionalesSeleccionados.value || []).map((fila) => Number(fila.conceptoId || 0))
    );

    if (categoriaPermiteConceptosDuplicados.value) {
        return conceptosActivos.value;
    }

    return conceptosActivos.value.filter((concepto) => !concepto.es_recurrente && !conceptosConFilas.has(concepto.id));
});

const hayConceptosConEvidencia = computed(() => conceptosVisibles.value.some((concepto) => !!concepto.requiere_imagen));

const esCategoriaDolares = computed(() => {
    const clave = String(categoria.value?.clave || '').trim().toUpperCase();
    const nombre = String(categoria.value?.nombre || '').trim().toUpperCase();
    return clave === 'DOLARES' || nombre === 'DOLARES';
});

const categoriaUsaSaldoInicialMensual = computed(() => !!categoria.value?.usa_saldo_inicial);

const estadoSaldoInicialCategoria = computed(() => saldoInicialCategoriaMensual.value || {});

const resumenMovimientosDia = computed(() => calcularResumenMovimientosDia());

const ingresosCategoriaDia = computed(() => normalizarNumero(resumenMovimientosDia.value.ingresos || 0));
const egresosCategoriaDia = computed(() => normalizarNumero(resumenMovimientosDia.value.egresos || 0));
const resultadoNetoCategoriaDia = computed(() => normalizarNumero(ingresosCategoriaDia.value - egresosCategoriaDia.value));

const requiereCapturaManualSaldoInicial = computed(() => {
    return categoriaUsaSaldoInicialMensual.value && !!estadoSaldoInicialCategoria.value?.requiere_captura_manual;
});

const permiteCapturaManualSaldoInicial = computed(() => {
    return categoriaUsaSaldoInicialMensual.value && !!estadoSaldoInicialCategoria.value?.permite_captura_manual;
});

const ajusteIngresosCategoriaMes = computed(() => {
    const baseIngresos = normalizarNumero(resumenDiaBasePersistido.ingresos || 0);
    return normalizarNumero(ingresosCategoriaDia.value - baseIngresos);
});

const ajusteEgresosCategoriaMes = computed(() => {
    const baseEgresos = normalizarNumero(resumenDiaBasePersistido.egresos || 0);
    return normalizarNumero(egresosCategoriaDia.value - baseEgresos);
});

const categoriaEsAdministracion = computed(() => {
    const banderaBackend = Boolean(estadoSaldoInicialCategoria.value?.es_categoria_administracion);
    if (banderaBackend) {
        return true;
    }

    const nombre = String(categoria.value?.nombre || '');
    const clave = String(categoria.value?.clave || '');
    const huella = `${nombre} ${clave}`
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase();
    return huella.includes('ADMINISTRACION');
});

const fondosFijosSucursalCategoriaMes = computed(() => normalizarNumero(estadoSaldoInicialCategoria.value?.fondos_fijos_sucursal || 0));

const saldoInicialCategoriaMes = computed(() => {
    const saldoInicialAdministracion = estadoSaldoInicialCategoria.value?.saldo_inicial_administracion;
    if (categoriaEsAdministracion.value && saldoInicialAdministracion !== null && saldoInicialAdministracion !== undefined) {
        return normalizarNumero(saldoInicialAdministracion);
    }
    return normalizarNumero(estadoSaldoInicialCategoria.value?.saldo_inicial || 0);
});
const ingresosCategoriaMes = computed(() => {
    const ingresosBaseMes = normalizarNumero(estadoSaldoInicialCategoria.value?.ingresos_mes || 0);
    return normalizarNumero(ingresosBaseMes + ajusteIngresosCategoriaMes.value);
});
const egresosCategoriaMes = computed(() => {
    const egresosBaseMes = normalizarNumero(estadoSaldoInicialCategoria.value?.egresos_mes || 0);
    return normalizarNumero(egresosBaseMes + ajusteEgresosCategoriaMes.value);
});
const resultadoNetoCategoriaMes = computed(() => normalizarNumero(ingresosCategoriaMes.value - egresosCategoriaMes.value));
const saldoFinalCategoriaMes = computed(() => normalizarNumero(saldoInicialCategoriaMes.value + resultadoNetoCategoriaMes.value));
const etiquetaQuintaTarjetaSaldoMensual = computed(() => {
    return categoriaEsAdministracion.value ? 'Fondos fijos de la sucursal' : 'Saldo final del mes';
});
const montoQuintaTarjetaSaldoMensual = computed(() => {
    return categoriaEsAdministracion.value ? fondosFijosSucursalCategoriaMes.value : saldoFinalCategoriaMes.value;
});

const origenSaldoInicialCategoria = computed(() => {
    const origen = String(estadoSaldoInicialCategoria.value?.origen_saldo_inicial || '').toUpperCase();
    if (origen === 'MANUAL') {
        return 'Manual';
    }
    if (origen === 'AUTOMATICO') {
        return 'Automático';
    }
    if (origen === 'PENDIENTE_MANUAL') {
        return 'Pendiente manual';
    }
    return 'No definido';
});

const tasaCambioDolares = computed(() => {
    const tasaSnapshot = normalizarNumero(reporteActual.value?.tipo_cambio_usd_snapshot || 0);
    const tasa = tasaSnapshot > 0 ? tasaSnapshot : tasaCambioDolaresConfiguracion.value;
    return Number.isFinite(tasa) && tasa > 0 ? tasa : 0;
});

const reporteCerrado = computed(() => reporteActual.value?.estado_reporte === 'CERRADO');
const horarioOperacionConfigurado = computed(() => Number.isInteger(horarioOperacion.minutosApertura) && Number.isInteger(horarioOperacion.minutosCierre));
const capturaFueraHorario = computed(() => {
    if (!horarioOperacionConfigurado.value) {
        return false;
    }
    return !minutoDentroDeVentana(
        minutosActualesCliente.value,
        horarioOperacion.minutosApertura,
        horarioOperacion.minutosCierre
    );
});
const mensajeBloqueoHorario = computed(() => {
    if (!capturaFueraHorario.value || !horarioOperacionConfigurado.value) {
        return '';
    }
    return `Fuera de horario de captura (${horarioOperacion.aperturaTexto} a ${horarioOperacion.cierreTexto} hrs). No se permiten modificaciones.`;
});
const capturaBloqueada = computed(() => reporteCerrado.value || capturaFueraHorario.value);
const usuarioPuedeCerrarDiaContable = computed(() => sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE', 'ADMINISTRADOR']));

const conceptosVisibles = computed(() => {
    const filasAdicionales = (conceptosAdicionalesSeleccionados.value || [])
        .map((fila) => {
            const concepto = conceptosActivos.value.find((item) => item.id === fila.conceptoId);
            if (!concepto) {
                return null;
            }

            return {
                ...concepto,
                __filaId: fila.filaId,
                __conceptoId: concepto.id,
                __origenFila: fila.origen || 'adicional'
            };
        })
        .filter(Boolean);

    const conceptosConFilasAdicionales = new Set(filasAdicionales.map((fila) => Number(fila.__conceptoId || 0)));

    const filasRecurrentesBase = conceptosRecurrentes.value
        .filter((concepto) => !conceptosConFilasAdicionales.has(concepto.id))
        .map((concepto) => ({
            ...concepto,
            __filaId: `REC-${concepto.id}`,
            __conceptoId: concepto.id,
            __origenFila: 'recurrente'
        }));

    return [...filasRecurrentesBase, ...filasAdicionales].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es-MX'));
});

const fechaContableSeleccionadaIso = computed(() => {
    if (!(fechaContableSeleccionada.value instanceof Date) || Number.isNaN(fechaContableSeleccionada.value.getTime())) {
        return '';
    }
    const anio = fechaContableSeleccionada.value.getFullYear();
    const mes = String(fechaContableSeleccionada.value.getMonth() + 1).padStart(2, '0');
    const dia = String(fechaContableSeleccionada.value.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
});

const fechaContableCierre = computed(() => {
    const fechaDesdeReporte = String(reporteActual.value?.fecha_contable || '').trim();
    if (fechaDesdeReporte) {
        return fechaDesdeReporte;
    }
    return String(fechaContableSeleccionadaIso.value || '').trim();
});

const fechaContableActivaEtiqueta = computed(() => {
    const fechaSeleccionada = String(fechaContableSeleccionadaIso.value || '').trim();
    if (fechaSeleccionada) {
        return fechaSeleccionada;
    }
    return String(reporteActual.value?.fecha_contable || 'Sin definir').trim();
});

const puedeCerrarDiaContable = computed(() => {
    return Boolean(
        sucursalId.value
        && fechaContableCierre.value
        && !reporteCerrado.value
        && !capturaFueraHorario.value
        && usuarioPuedeCerrarDiaContable.value
    );
});

// 1) Para qué sirve: resolver valor inicial de cada detalle parametrizado según su tipo.
// 2) Cómo funciona: prioriza valor_defecto y aplica conversiones para INT/DECIMAL/BOOLEAN.
// 3) Qué hace: evita campos vacíos o con tipo incorrecto al iniciar captura.
// 4) Cómo editarla: agrega nuevas ramas si se incorporan tipos de detalle adicionales.
function obtenerValorDefectoDetalle(detalle) {
    if (detalle.valor_defecto !== null && detalle.valor_defecto !== undefined && detalle.valor_defecto !== '') {
        if (detalle.tipo_valor === 'INT') {
            return Number.isFinite(Number(detalle.valor_defecto)) ? Number(detalle.valor_defecto) : 0;
        }
        if (detalle.tipo_valor === 'DECIMAL') {
            return Number.isFinite(Number(detalle.valor_defecto)) ? Number(detalle.valor_defecto) : 0;
        }
        if (detalle.tipo_valor === 'BOOLEAN') {
            return String(detalle.valor_defecto).toLowerCase() === 'true';
        }
        return detalle.valor_defecto;
    }

    if (detalle.tipo_valor === 'BOOLEAN') return false;
    if (detalle.tipo_valor === 'INT') return 0;
    if (detalle.tipo_valor === 'DECIMAL') return null;
    return '';
}

// 1) Para qué sirve: crear el estado reactivo base de captura para cada concepto.
// 2) Cómo funciona: inicializa monto, detalles, metadatos de guardado y firma.
// 3) Qué hace: estandariza estructura usada por todas las filas de la tabla.
// 4) Cómo editarla: agrega aquí nuevos flags/campos de UI para que nazcan con valor controlado.
function crearEstadoInicialCaptura() {
    const detalles = {};
    for (const detalle of detallesActivos.value) {
        detalles[detalle.clave] = obtenerValorDefectoDetalle(detalle);
    }

    return {
        conceptoId: null,
        idMovimiento: null,
        monto: null,
        detalles,
        notas: '',
        archivoRespaldo: null,
        archivoRespaldoUrl: '',
        archivoRespaldoNombre: '',
        guardando: false,
        guardadoReciente: false,
        errorGuardado: '',
        ultimaHoraGuardado: '',
        firmaGuardada: ''
    };
}

// 1) Para qué sirve: limpiar montos en foco para facilitar captura directa.
// 2) Cómo funciona: si el valor de monto o detalle decimal es 0 lo vuelve null.
// 3) Qué hace: evita que el usuario tenga que borrar manualmente 0.00.
// 4) Cómo editarla: reutiliza este patrón en nuevos campos monetarios.
function limpiarMontoEnFoco(idFila, idConcepto, claveDetalle = null) {
    const estado = obtenerEstadoCaptura(idFila, idConcepto);

    if (claveDetalle) {
        const valorDetalle = Number(estado.detalles?.[claveDetalle]);
        if (Number.isFinite(valorDetalle) && valorDetalle === 0) {
            estado.detalles[claveDetalle] = null;
        }
        return;
    }

    const valorMonto = Number(estado.monto);
    if (Number.isFinite(valorMonto) && valorMonto === 0) {
        estado.monto = null;
    }
}

// 1) Para qué sirve: capturar cambios numéricos en vivo antes del debounce de guardado.
// 2) Cómo funciona: toma valor emitido por InputNumber, actualiza estado y programa guardado.
// 3) Qué hace: evita depender del blur para persistir montos y decimales.
// 4) Cómo editarla: reutiliza claveDetalle en nuevos campos numéricos de la tabla.
function manejarEntradaNumerica(evento, idFila, idConcepto, claveDetalle = null) {
    if (capturaBloqueada.value) {
        return;
    }

    const estado = obtenerEstadoCaptura(idFila, idConcepto);
    const valorEvento = evento && Object.prototype.hasOwnProperty.call(evento, 'value')
        ? evento.value
        : undefined;

    if (valorEvento !== undefined) {
        if (claveDetalle) {
            estado.detalles[claveDetalle] = valorEvento;
        } else {
            estado.monto = valorEvento;
        }
    }

    programarGuardado(idFila);
}

// 1) Para qué sirve: construir snapshot de detalles listo para enviar al backend.
// 2) Cómo funciona: recorre detalles activos y convierte cada valor con mapearDetalleParaEnvio.
// 3) Qué hace: asegura estructura consistente en detalles_snapshot.
// 4) Cómo editarla: ajusta mapeo si backend requiere claves extra por detalle.
function construirDetallesSnapshotDesdeEstado(estado) {
    const detallesSnapshot = {};
    for (const detalle of detallesActivos.value) {
        const valorActual = estado.detalles?.[detalle.clave];
        detallesSnapshot[detalle.clave] = mapearDetalleParaEnvio(detalle, valorActual);
    }
    return detallesSnapshot;
}

// 1) Para qué sirve: generar una firma estable del estado editable de una fila.
// 2) Cómo funciona: serializa concepto, monto, notas y snapshot a JSON string.
// 3) Qué hace: permite detectar cambios y evitar guardados innecesarios.
// 4) Cómo editarla: incluye nuevos campos en la firma si deben disparar autoguardado.
function construirFirmaEstado(estado) {
    const firma = {
        concepto: Number(estado?.conceptoId || 0),
        monto: normalizarNumero(estado.monto),
        notas: estado.notas || '',
        detalles_snapshot: construirDetallesSnapshotDesdeEstado(estado)
    };
    return JSON.stringify(firma);
}

// 1) Para qué sirve: generar identificador único de fila para capturas repetidas por concepto.
// 2) Cómo funciona: concatena prefijo, concepto y consecutivo incremental local.
// 3) Qué hace: permite múltiples filas del mismo concepto sin colisión de estado.
// 4) Cómo editarla: cambia formato si se requiere trazabilidad distinta en UI.
function generarIdentificadorFilaConcepto(idConcepto, prefijo = 'CAP') {
    consecutivoFilaCaptura.value += 1;
    return `${prefijo}-${idConcepto}-${consecutivoFilaCaptura.value}`;
}

// 1) Para qué sirve: registrar una fila adicional de captura para un concepto.
// 2) Cómo funciona: agrega descriptor de fila y prepara su estado reactivo.
// 3) Qué hace: habilita capturas múltiples del mismo concepto en una categoría.
// 4) Cómo editarla: agrega metadata extra por fila si se requiere en reportes UI.
function agregarFilaConceptoSeleccionado(idConcepto, origen = 'manual', filaId = null) {
    const identificadorFila = filaId || generarIdentificadorFilaConcepto(idConcepto, 'ADD');

    if (!conceptosAdicionalesSeleccionados.value.some((fila) => fila.filaId === identificadorFila)) {
        conceptosAdicionalesSeleccionados.value.push({
            filaId: identificadorFila,
            conceptoId: Number(idConcepto),
            origen
        });
    }

    obtenerEstadoCaptura(identificadorFila, Number(idConcepto));
    return identificadorFila;
}

// 1) Para qué sirve: agregar otra captura del mismo concepto desde la tabla.
// 2) Cómo funciona: crea una nueva fila sólo cuando la categoría tiene detalles parametrizados.
// 3) Qué hace: permite múltiples gastos/ingresos del mismo concepto con distintos detalles.
// 4) Cómo editarla: cambia condición de habilitación si negocio define otra regla.
function agregarOtraCapturaConcepto(idConcepto) {
    if (capturaBloqueada.value || !categoriaPermiteConceptosDuplicados.value) {
        return;
    }

    agregarFilaConceptoSeleccionado(idConcepto, 'duplicado');
}

// 1) Para qué sirve: eliminar una fila de captura de forma segura desde la tabla.
// 2) Cómo funciona: confirma acción, borra backend si hay movimiento y limpia estado local.
// 3) Qué hace: permite revertir capturas adicionales o erróneas sin recargar la pantalla.
// 4) Cómo editarla: centraliza aquí reglas adicionales de bloqueo por rol/estado.
async function eliminarFilaCaptura(fila) {
    if (capturaBloqueada.value) {
        return;
    }

    const idFila = fila?.__filaId;
    const idConcepto = Number(fila?.__conceptoId || 0);
    if (!idFila || !idConcepto) {
        return;
    }

    const estado = obtenerEstadoCaptura(idFila, idConcepto);
    const idMovimiento = Number(estado.idMovimiento || 0);

    const mensajeConfirmacion = idMovimiento > 0
        ? 'Se eliminará esta captura y su movimiento guardado en base de datos. ¿Deseas continuar?'
        : 'Se eliminará esta fila de captura. ¿Deseas continuar?';

    if (!window.confirm(mensajeConfirmacion)) {
        return;
    }

    estado.errorGuardado = '';
    estado.guardando = true;
    cargandoGuardado.value = true;

    try {
        if (idMovimiento > 0) {
            await eliminarMovimientoDiario(idMovimiento);
            movimientosExistentes.value = (movimientosExistentes.value || []).filter(
                (movimiento) => Number(movimiento.id) !== idMovimiento
            );
        }

        if (temporizadoresGuardado.has(idFila)) {
            clearTimeout(temporizadoresGuardado.get(idFila));
            temporizadoresGuardado.delete(idFila);
        }

        if (temporizadoresEstado.has(idFila)) {
            clearTimeout(temporizadoresEstado.get(idFila));
            temporizadoresEstado.delete(idFila);
        }

        conceptosAdicionalesSeleccionados.value = conceptosAdicionalesSeleccionados.value.filter(
            (item) => item.filaId !== idFila
        );
        delete capturasPorConcepto[idFila];
    } catch (error) {
        estado.errorGuardado = error?.response?.data?.message || 'No se pudo eliminar la captura seleccionada.';
        mensajePantalla.value = estado.errorGuardado;
    } finally {
        if (capturasPorConcepto[idFila]) {
            capturasPorConcepto[idFila].guardando = false;
        }
        cargandoGuardado.value = Object.values(capturasPorConcepto).some((item) => item.guardando);
    }
}

// 1) Para qué sirve: extraer nombre de archivo desde una ruta o URL completa.
// 2) Cómo funciona: separa por '/' y toma el último segmento.
// 3) Qué hace: muestra nombre legible de evidencia adjunta en UI.
// 4) Cómo editarla: añade compatibilidad para separador '\\' si se reciben rutas locales.
function obtenerNombreArchivoDesdeRuta(rutaArchivo) {
    if (!rutaArchivo || typeof rutaArchivo !== 'string') {
        return '';
    }
    const segmentos = rutaArchivo.split('/');
    return segmentos[segmentos.length - 1] || '';
}

// 1) Para qué sirve: formatear la hora de guardado para mostrarla en estado de fila.
// 2) Cómo funciona: convierte ISO a Date y aplica locale es-MX en 24 horas.
// 3) Qué hace: entrega etiqueta de hora consistente para feedback al usuario.
// 4) Cómo editarla: cambia formato si UX requiere fecha+hora o formato relativo.
function formatearHoraGuardado(fechaIso) {
    if (!fechaIso) {
        return '';
    }

    const fecha = new Date(fechaIso);
    if (Number.isNaN(fecha.getTime())) {
        return '';
    }

    return fecha.toLocaleTimeString('es-MX', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

// 1) Para qué sirve: obtener o inicializar el estado reactivo de un concepto.
// 2) Cómo funciona: crea estado al vuelo y calcula firma inicial guardada.
// 3) Qué hace: evita acceso a estados indefinidos en render y eventos.
// 4) Cómo editarla: centraliza aquí cualquier inicialización adicional por concepto.
function obtenerEstadoCaptura(idFila, idConcepto = null) {
    if (!capturasPorConcepto[idFila]) {
        capturasPorConcepto[idFila] = crearEstadoInicialCaptura();
    }

    if (idConcepto !== null && idConcepto !== undefined) {
        capturasPorConcepto[idFila].conceptoId = Number(idConcepto);
    }

    if (!capturasPorConcepto[idFila].firmaGuardada) {
        capturasPorConcepto[idFila].firmaGuardada = construirFirmaEstado(capturasPorConcepto[idFila]);
    }

    return capturasPorConcepto[idFila];
}

// 1) Para qué sirve: cargar datos existentes de movimiento al estado de captura.
// 2) Cómo funciona: mapea monto, notas, archivo y detalles_snapshot hacia la fila.
// 3) Qué hace: permite editar capturas previas sin perder contexto visual.
// 4) Cómo editarla: agrega campos nuevos del movimiento para hidratación completa.
function hidratarCapturaDesdeMovimiento(movimiento) {
    const filaId = `MOV-${movimiento.id}`;
    agregarFilaConceptoSeleccionado(movimiento.concepto, 'movimiento', filaId);

    const estado = obtenerEstadoCaptura(filaId, movimiento.concepto);
    estado.idMovimiento = movimiento.id;
    if (esCategoriaDolares.value && movimiento.monto_divisa !== null && movimiento.monto_divisa !== undefined) {
        estado.monto = Number(movimiento.monto_divisa || 0);
    } else {
        estado.monto = Number(movimiento.monto || 0);
    }
    estado.notas = movimiento.notas || '';
    estado.archivoRespaldo = null;
    estado.archivoRespaldoUrl = movimiento.archivo_respaldo_url || '';
    estado.archivoRespaldoNombre = obtenerNombreArchivoDesdeRuta(movimiento.archivo_respaldo || movimiento.archivo_respaldo_url || '');
    estado.ultimaHoraGuardado = formatearHoraGuardado(movimiento.actualizado_en || movimiento.creado_en);

    const snapshot = movimiento.detalles_snapshot || {};
    for (const detalle of detallesActivos.value) {
        if (Object.prototype.hasOwnProperty.call(snapshot, detalle.clave)) {
            estado.detalles[detalle.clave] = snapshot[detalle.clave];
        }
    }

    estado.firmaGuardada = construirFirmaEstado(estado);
}

// 1) Para qué sirve: convertir valor de detalle al tipo esperado por backend.
// 2) Cómo funciona: evalúa tipo_valor y transforma a número, booleano, ISO o texto.
// 3) Qué hace: previene validaciones fallidas por tipos incompatibles.
// 4) Cómo editarla: añade soporte para nuevos tipos definidos en DetalleParametrizado.
function mapearDetalleParaEnvio(detalle, valor) {
    if (detalle.tipo_valor === 'INT') {
        return Number.isFinite(Number(valor)) ? Number(valor) : 0;
    }
    if (detalle.tipo_valor === 'DECIMAL') {
        return Number.isFinite(Number(valor)) ? Number(valor) : 0;
    }
    if (detalle.tipo_valor === 'BOOLEAN') {
        return !!valor;
    }
    if (detalle.tipo_valor === 'DATE' || detalle.tipo_valor === 'DATETIME') {
        if (!valor) return '';
        if (valor instanceof Date) return valor.toISOString();
        return valor;
    }
    return valor || '';
}

// 1) Para qué sirve: normalizar números capturados en diferentes formatos regionales.
// 2) Cómo funciona: interpreta coma/punto como miles o decimal y convierte a Number.
// 3) Qué hace: garantiza cálculos y envíos numéricos confiables.
// 4) Cómo editarla: ajusta reglas de parsing si se adopta otro estándar de entrada.
function normalizarNumero(valor) {
    if (typeof valor === 'number') {
        return Number.isFinite(valor) ? valor : 0;
    }

    if (typeof valor === 'string') {
        const texto = valor.trim();
        if (!texto) return 0;

        let valorNormalizado = texto;
        const tieneComa = texto.includes(',');
        const tienePunto = texto.includes('.');

        if (tieneComa && tienePunto) {
            if (texto.lastIndexOf(',') > texto.lastIndexOf('.')) {
                valorNormalizado = texto.replace(/\./g, '').replace(',', '.');
            } else {
                valorNormalizado = texto.replace(/,/g, '');
            }
        } else if (tieneComa) {
            valorNormalizado = texto.replace(/\./g, '').replace(',', '.');
        }

        const numero = Number(valorNormalizado);
        return Number.isFinite(numero) ? numero : 0;
    }

    const numero = Number(valor);
    return Number.isFinite(numero) ? numero : 0;
}

// 1) Para qué sirve: unificar conversión de montos capturados a la moneda de vista previa.
// 2) Cómo funciona: normaliza monto; en categoría DOLARES aplica tasa actual a MXN.
// 3) Qué hace: asegura cálculos consistentes entre tabla y tarjetas resumen.
// 4) Cómo editarla: agrega reglas aquí si se requieren redondeos especiales.
function convertirMontoCapturaAMonedaVistaPrevia(montoCapturado) {
    const montoNormalizado = normalizarNumero(montoCapturado || 0);
    if (!esCategoriaDolares.value) {
        return montoNormalizado;
    }
    return montoNormalizado * tasaCambioDolares.value;
}

// 1) Para qué sirve: resumir en vivo ingresos/egresos del día según lo capturado en pantalla.
// 2) Cómo funciona: recorre filas visibles, clasifica por tipo de concepto y acumula montos.
// 3) Qué hace: alimenta tarjeta diaria y ajustes reactivos de la tarjeta mensual.
// 4) Cómo editarla: agrega más métricas aquí si se requieren indicadores adicionales.
function calcularResumenMovimientosDia() {
    let ingresos = 0;
    let egresos = 0;

    for (const concepto of conceptosVisibles.value) {
        const idFila = String(concepto?.__filaId || '').trim();
        if (!idFila) {
            continue;
        }

        const estadoCaptura = capturasPorConcepto[idFila];
        const montoCalculado = normalizarNumero(
            convertirMontoCapturaAMonedaVistaPrevia(estadoCaptura?.monto)
        );

        if (!montoCalculado) {
            continue;
        }

        const tipoConcepto = String(concepto?.tipo || '').trim().toUpperCase();
        if (tipoConcepto === 'INGRESO') {
            ingresos += montoCalculado;
            continue;
        }

        if (tipoConcepto === 'EGRESO') {
            egresos += montoCalculado;
        }
    }

    return {
        ingresos: normalizarNumero(ingresos),
        egresos: normalizarNumero(egresos),
        resultadoNeto: normalizarNumero(ingresos - egresos)
    };
}

// 1) Para qué sirve: fijar referencia base del día ya persistido al cargar la pantalla.
// 2) Cómo funciona: toma el resumen actual y lo guarda como línea base para ajustes mensuales.
// 3) Qué hace: evita duplicar montos en resumen mensual cuando se edita sin recargar.
// 4) Cómo editarla: invócala tras cargas iniciales adicionales que hidraten capturas.
function actualizarResumenDiaBasePersistido() {
    const resumenActual = calcularResumenMovimientosDia();
    resumenDiaBasePersistido.ingresos = normalizarNumero(resumenActual.ingresos || 0);
    resumenDiaBasePersistido.egresos = normalizarNumero(resumenActual.egresos || 0);
}

// 1) Para qué sirve: calcular monto mostrado en vista previa monetaria.
// 2) Cómo funciona: usa monto directo o conversión por tasa cuando categoría es DOLARES.
// 3) Qué hace: refleja al usuario el valor final en MXN de forma inmediata.
// 4) Cómo editarla: cambia fórmula si negocio introduce comisiones o redondeo especial.
function calcularMontoVistaPrevia(idFila) {
    const estado = obtenerEstadoCaptura(idFila);
    return convertirMontoCapturaAMonedaVistaPrevia(estado.monto);
}

// 1) Para qué sirve: cerrar el día contable visible en la pantalla de captura.
// 2) Cómo funciona: confirma la acción y llama endpoint cerrar-actual por sucursal/fecha.
// 3) Qué hace: bloquea por completo la captura del día para no permitir cambios.
// 4) Cómo editarla: agrega validación adicional previa si negocio exige checklist de cierre.
async function cerrarDiaDesdeCaptura() {
    const fechaObjetivoCierre = fechaContableCierre.value;
    if (!sucursalId.value || !puedeCerrarDiaContable.value || !fechaObjetivoCierre) {
        return;
    }

    const confirmado = window.confirm(`Vas a cerrar el día contable ${fechaObjetivoCierre}. Esta acción no cerrará otros días abiertos. ¿Deseas continuar?`);
    if (!confirmado) {
        return;
    }

    cerrandoDiaContable.value = true;
    mensajeCierreDiaContable.value = '';
    try {
        await cerrarDiaContableActual({
            sucursal_id: sucursalId.value,
            fecha_contable: fechaObjetivoCierre
        });
        mensajeCierreDiaContable.value = `Cierre de día ejecutado correctamente para ${fechaObjetivoCierre}. El día contable ha quedado bloqueado.`;
        await cargarPantalla();
    } catch (error) {
        mensajeCierreDiaContable.value = error?.response?.data?.message || 'No se pudo completar el cierre de día.';
    } finally {
        cerrandoDiaContable.value = false;
    }
}

// 1) Para qué sirve: limpiar monto manual en foco para facilitar captura del saldo inicial.
// 2) Cómo funciona: si el valor actual es 0 lo vuelve null al enfocar.
// 3) Qué hace: evita que el usuario borre manualmente el 0.00 en la entrada.
// 4) Cómo editarla: reutiliza patrón si agregas más campos monetarios de configuración.
function limpiarSaldoInicialManualEnFoco() {
    const valorActual = normalizarNumero(montoSaldoInicialManual.value || 0);
    if (valorActual === 0) {
        montoSaldoInicialManual.value = null;
    }
}

// 1) Para qué sirve: consultar estado mensual del saldo inicial para la categoría actual.
// 2) Cómo funciona: llama endpoint dedicado con sucursal/categoría/fecha contable seleccionada.
// 3) Qué hace: habilita flujo manual inicial o muestra arrastre automático bloqueado.
// 4) Cómo editarla: incorpora más indicadores cuando backend amplíe el payload.
async function cargarSaldoInicialCategoriaMensual() {
    saldoInicialCategoriaMensual.value = null;
    mensajeSaldoInicialCategoria.value = '';

    if (!categoriaUsaSaldoInicialMensual.value) {
        return;
    }

    if (!sucursalId.value || !idCategoriaActual.value || !fechaContableSeleccionadaIso.value) {
        return;
    }

    try {
        const { data } = await obtenerSaldoInicialCategoriaMensual(
            sucursalId.value,
            idCategoriaActual.value,
            fechaContableSeleccionadaIso.value
        );

        saldoInicialCategoriaMensual.value = data?.data || null;
        montoSaldoInicialManual.value = normalizarNumero(data?.data?.saldo_inicial || 0);

        if (saldoInicialCategoriaMensual.value?.estado_generacion === 'GENERADO_AUTOMATICO') {
            mensajeSaldoInicialCategoria.value = 'Se aplicó arrastre automático del mes anterior para esta categoría.';
        } else if (saldoInicialCategoriaMensual.value?.requiere_captura_manual) {
            mensajeSaldoInicialCategoria.value = 'No existe arrastre previo. Debes capturar manualmente el saldo inicial de este mes.';
        }
    } catch (error) {
        saldoInicialCategoriaMensual.value = null;
        mensajeSaldoInicialCategoria.value = error?.response?.data?.message || 'No se pudo obtener el saldo inicial mensual de la categoría.';
    }
}

// 1) Para qué sirve: fijar manualmente el primer saldo inicial mensual de una categoría.
// 2) Cómo funciona: envía sucursal/categoría/fecha/monto al endpoint manual y recarga estado.
// 3) Qué hace: guarda o actualiza el saldo inicial manual.
// 4) Cómo editarla: agrega doble confirmación si la operación requiere control adicional.
async function guardarSaldoInicialCategoriaManual() {
    if (capturaBloqueada.value || !permiteCapturaManualSaldoInicial.value) {
        return;
    }

    const montoManual = normalizarNumero(montoSaldoInicialManual.value || 0);
    capturandoSaldoInicialManual.value = true;
    mensajeSaldoInicialCategoria.value = '';

    try {
        const payload = {
            sucursal_id: sucursalId.value,
            categoria_id: idCategoriaActual.value,
            fecha_contable: fechaContableSeleccionadaIso.value,
            saldo_inicial: montoManual
        };
        await establecerSaldoInicialCategoriaManual(payload);
        await cargarSaldoInicialCategoriaMensual();
        mensajeSaldoInicialCategoria.value = 'Saldo inicial manual guardado correctamente para este mes.';
    } catch (error) {
        mensajeSaldoInicialCategoria.value = error?.response?.data?.message || 'No fue posible guardar el saldo inicial manual.';
    } finally {
        capturandoSaldoInicialManual.value = false;
    }
}

// 1) Para qué sirve: cargar todos los datos iniciales de la pantalla de captura.
// 2) Cómo funciona: valida contexto, consulta categoría/reporte/configuración y movimientos.
// 3) Qué hace: prepara estado base para autoguardado y render dinámico de tabla.
// 4) Cómo editarla: agrega nuevas fuentes en Promise.all si la pantalla requiere más contexto.
async function cargarPantalla() {
    cargando.value = true;
    mensajePantalla.value = '';

    conceptosAdicionalesSeleccionados.value = [];
    consecutivoFilaCaptura.value = 0;
    saldoInicialCategoriaMensual.value = null;
    mensajeSaldoInicialCategoria.value = '';
    montoSaldoInicialManual.value = 0;
    resumenDiaBasePersistido.ingresos = 0;
    resumenDiaBasePersistido.egresos = 0;

    try {
        if (!sucursalId.value) {
            mensajePantalla.value = 'Tu usuario no tiene una sucursal asignada. Solicita al administrador configurar tu sucursal.';
            return;
        }

        if (!idCategoriaActual.value) {
            mensajePantalla.value = 'No se encontró la categoría operativa solicitada.';
            return;
        }

        if (!fechaContableSeleccionadaIso.value) {
            mensajePantalla.value = 'Selecciona un día contable válido para continuar con la captura.';
            return;
        }

        const [respuestaCategoria, respuestaReporte, respuestaConfiguraciones] = await Promise.all([
            obtenerCategoriaOperativa(idCategoriaActual.value),
            obtenerReporteDiarioPorFecha(sucursalId.value, fechaContableSeleccionadaIso.value),
            listarConfiguracionesGlobales()
        ]);

        categoria.value = respuestaCategoria.data?.data || null;
        reporteActual.value = respuestaReporte.data?.data || null;
        const configuraciones = Array.isArray(respuestaConfiguraciones?.data?.data) ? respuestaConfiguraciones.data.data : [];

        actualizarHorarioOperacionDesdeConfiguraciones(configuraciones);

        const configuracionUsd = configuraciones.find((item) => ['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD'].includes(String(item.clave || '').toUpperCase()));
        tasaCambioDolaresConfiguracion.value = normalizarNumero(configuracionUsd?.valor_tipado ?? configuracionUsd?.valor ?? 0);

        if (!categoria.value) {
            mensajePantalla.value = 'No se pudo cargar la categoría operativa.';
            return;
        }

        await cargarSaldoInicialCategoriaMensual();

        const { data } = await listarMovimientosDiarios({
            reporte_id: reporteActual.value?.id,
            categoria_id: categoria.value.id
        });

        movimientosExistentes.value = Array.isArray(data?.data) ? data.data : [];

        for (const movimiento of movimientosExistentes.value) {
            hidratarCapturaDesdeMovimiento(movimiento);
        }

        actualizarResumenDiaBasePersistido();
    } catch (error) {
        mensajePantalla.value = error?.response?.data?.message || 'Ocurrió un error al cargar la captura operativa.';
    } finally {
        cargando.value = false;
    }
}

// 1) Para qué sirve: agregar manualmente conceptos no recurrentes a la tabla visible.
// 2) Cómo funciona: inserta id seleccionado si no existe e inicializa su estado.
// 3) Qué hace: habilita captura puntual de conceptos eventuales.
// 4) Cómo editarla: cambia criterio de inserción si quieres limitar cantidad o tipo.
function agregarConceptoNoRecurrente() {
    if (capturaBloqueada.value) {
        return;
    }

    if (!conceptoNoRecurrenteSeleccionado.value) {
        return;
    }

    const idConcepto = Number(conceptoNoRecurrenteSeleccionado.value);
    const yaExisteFila = conceptosAdicionalesSeleccionados.value.some((fila) => fila.conceptoId === idConcepto);

    if (!categoriaPermiteConceptosDuplicados.value && yaExisteFila) {
        conceptoNoRecurrenteSeleccionado.value = null;
        return;
    }

    agregarFilaConceptoSeleccionado(idConcepto, 'manual');
    conceptoNoRecurrenteSeleccionado.value = null;
}

// 1) Para qué sirve: capturar archivo de evidencia y programar autoguardado.
// 2) Cómo funciona: toma primer archivo del input y lo asigna al estado del concepto.
// 3) Qué hace: sincroniza respaldo documental en la misma fila de captura.
// 4) Cómo editarla: valida tipo/tamaño de archivo aquí antes de guardar.
function manejarArchivoConcepto(evento, idFila) {
    if (capturaBloqueada.value) {
        return;
    }

    const archivo = evento?.target?.files?.[0] || null;
    const estado = obtenerEstadoCaptura(idFila);
    estado.archivoRespaldo = archivo;
    estado.archivoRespaldoNombre = archivo?.name || estado.archivoRespaldoNombre || '';
    programarGuardado(idFila);
}

// 1) Para qué sirve: aplicar debounce al autoguardado por fila.
// 2) Cómo funciona: limpia temporizador previo y programa guardarFila en 1 segundo.
// 3) Qué hace: reduce llamadas repetitivas mientras el usuario escribe.
// 4) Cómo editarla: ajusta milisegundos según balance entre inmediatez y carga de red.
function programarGuardado(idFila) {
    if (capturaBloqueada.value) {
        return;
    }

    const estado = obtenerEstadoCaptura(idFila);
    estado.errorGuardado = '';

    if (temporizadoresGuardado.has(idFila)) {
        clearTimeout(temporizadoresGuardado.get(idFila));
    }

    const temporizador = setTimeout(() => {
        guardarFila(idFila);
    }, 1000);

    temporizadoresGuardado.set(idFila, temporizador);
}

// 1) Para qué sirve: persistir cambios de una fila de captura en backend.
// 2) Cómo funciona: valida cambios por firma, arma payload JSON/FormData y llama captura-rapida.
// 3) Qué hace: crea/actualiza movimiento y actualiza estado visual de guardado.
// 4) Cómo editarla: incorpora campos nuevos al payload y a la firma para sincronización correcta.
async function guardarFila(idFila) {
    if (!sucursalId.value || capturaBloqueada.value) {
        return;
    }

    const estado = obtenerEstadoCaptura(idFila);
    const idConcepto = Number(estado.conceptoId || 0);
    if (!idConcepto) {
        estado.errorGuardado = 'No se pudo identificar el concepto de la fila para guardar.';
        return;
    }

    const firmaActual = construirFirmaEstado(estado);
    const hayArchivoNuevo = estado.archivoRespaldo instanceof File;

    if (!hayArchivoNuevo && estado.firmaGuardada === firmaActual) {
        estado.errorGuardado = '';
        return;
    }

    estado.guardando = true;
    cargandoGuardado.value = true;

    try {
        const concepto = conceptosActivos.value.find((item) => item.id === idConcepto);
        const detallesSnapshot = construirDetallesSnapshotDesdeEstado(estado);

        let payload = {
            concepto: idConcepto,
            sucursal_id: sucursalId.value,
            fecha_contable: fechaContableSeleccionadaIso.value,
            monto: normalizarNumero(estado.monto),
            detalles_snapshot: detallesSnapshot,
            notas: estado.notas || ''
        };

        if (estado.idMovimiento) {
            payload.movimiento_id = estado.idMovimiento;
        }

        if (concepto?.requiere_imagen && estado.archivoRespaldo instanceof File) {
            const formulario = new FormData();
            formulario.append('concepto', String(idConcepto));
            formulario.append('sucursal_id', String(sucursalId.value));
            formulario.append('fecha_contable', fechaContableSeleccionadaIso.value);
            formulario.append('monto', String(normalizarNumero(estado.monto)));
            formulario.append('detalles_snapshot', JSON.stringify(detallesSnapshot));
            formulario.append('notas', estado.notas || '');
            if (estado.idMovimiento) {
                formulario.append('movimiento_id', String(estado.idMovimiento));
            }
            formulario.append('archivo_respaldo', estado.archivoRespaldo);
            payload = formulario;
        }

        const { data } = await guardarCapturaRapida(payload);
        const movimiento = data?.data;
        if (movimiento?.id) {
            estado.idMovimiento = movimiento.id;
        }
        estado.archivoRespaldoUrl = movimiento?.archivo_respaldo_url || estado.archivoRespaldoUrl || '';
        estado.archivoRespaldoNombre = obtenerNombreArchivoDesdeRuta(movimiento?.archivo_respaldo || movimiento?.archivo_respaldo_url || estado.archivoRespaldoNombre);
        estado.archivoRespaldo = null;
        estado.firmaGuardada = construirFirmaEstado(estado);

        estado.errorGuardado = '';
        estado.guardadoReciente = true;
        estado.ultimaHoraGuardado = formatearHoraGuardado(movimiento?.actualizado_en || movimiento?.creado_en) || formatearHoraGuardado(new Date().toISOString());

        if (temporizadoresEstado.has(idFila)) {
            clearTimeout(temporizadoresEstado.get(idFila));
        }

        const temporizadorEstado = setTimeout(() => {
            const estadoActual = capturasPorConcepto[idFila];
            if (estadoActual && !estadoActual.guardando && !estadoActual.errorGuardado) {
                estadoActual.guardadoReciente = false;
            }
            temporizadoresEstado.delete(idFila);
        }, 3000);

        temporizadoresEstado.set(idFila, temporizadorEstado);
    } catch (error) {
        estado.errorGuardado = error?.response?.data?.message || 'No se pudo guardar la captura.';
    } finally {
        estado.guardando = false;
        cargandoGuardado.value = Object.values(capturasPorConcepto).some((item) => item.guardando);
    }
}

// 1) Para qué sirve: construir etiqueta visual del estado de sincronización por fila.
// 2) Cómo funciona: evalúa flags guardando/error/guardadoReciente con prioridad.
// 3) Qué hace: devuelve texto y severidad para componente Tag/estado.
// 4) Cómo editarla: personaliza estados y mensajes si UX requiere más granularidad.
function etiquetaEstadoFila(idFila) {
    const estado = obtenerEstadoCaptura(idFila);
    if (estado.guardando) return { valor: 'Guardando...', severidad: 'warn' };
    if (estado.errorGuardado) return { valor: 'Error al guardar', severidad: 'danger' };
    if (estado.guardadoReciente) {
        const hora = estado.ultimaHoraGuardado ? ` ${estado.ultimaHoraGuardado}` : '';
        return { valor: `Guardado${hora}`, severidad: 'success' };
    }
    if (estado.ultimaHoraGuardado) return { valor: `Ultimo guardado ${estado.ultimaHoraGuardado}`, severidad: 'info' };
    return { valor: 'Listo', severidad: 'secondary' };
}

// 1) Para qué sirve: reaccionar al cambio de categoría en ruta y recargar contexto.
// 2) Cómo funciona: limpia timers/estado previo y ejecuta cargarPantalla nuevamente.
// 3) Qué hace: evita fugas de estado entre categorías operativas.
// 4) Cómo editarla: añade limpieza adicional si se agregan nuevos recursos temporales.
watch(idCategoriaActual, async () => {
    for (const temporizador of temporizadoresGuardado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresGuardado.clear();

    for (const temporizador of temporizadoresEstado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresEstado.clear();

    for (const clave of Object.keys(capturasPorConcepto)) {
        delete capturasPorConcepto[clave];
    }

    conceptosAdicionalesSeleccionados.value = [];
    consecutivoFilaCaptura.value = 0;
    await cargarPantalla();
});

watch(fechaContableSeleccionadaIso, async (nuevaFecha, fechaAnterior) => {
    if (!nuevaFecha || nuevaFecha === fechaAnterior) {
        return;
    }

    for (const temporizador of temporizadoresGuardado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresGuardado.clear();

    for (const temporizador of temporizadoresEstado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresEstado.clear();

    for (const clave of Object.keys(capturasPorConcepto)) {
        delete capturasPorConcepto[clave];
    }

    conceptosAdicionalesSeleccionados.value = [];
    consecutivoFilaCaptura.value = 0;
    await cargarPantalla();
});

// 1) Para qué sirve: inicializar la pantalla al montar el componente.
// 2) Cómo funciona: invoca cargarPantalla en el ciclo de vida onMounted.
// 3) Qué hace: muestra datos iniciales al abrir la vista.
// 4) Cómo editarla: agrega tareas de inicialización extra antes/después de cargarPantalla.
onMounted(async () => {
    actualizarMinutoActualCliente();
    intervaloMinutosCliente.value = setInterval(() => {
        actualizarMinutoActualCliente();
    }, 15000);

    fechaContableSeleccionada.value = new Date(fechaContableMaxima);
    await cargarPantalla();
});

// 1) Para qué sirve: liberar recursos temporales al salir de la vista.
// 2) Cómo funciona: limpia todos los timeouts de guardado y estado.
// 3) Qué hace: previene ejecuciones tardías y memory leaks.
// 4) Cómo editarla: incluye cancelación de requests si se implementa AbortController.
onBeforeUnmount(() => {
    for (const temporizador of temporizadoresGuardado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresGuardado.clear();

    for (const temporizador of temporizadoresEstado.values()) {
        clearTimeout(temporizador);
    }
    temporizadoresEstado.clear();

    if (intervaloMinutosCliente.value) {
        clearInterval(intervaloMinutosCliente.value);
        intervaloMinutosCliente.value = null;
    }
});
</script>

<template>
    <section class="space-y-4">
        <div class="card">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <h1 class="text-2xl font-semibold">Captura operativa automatizada</h1>
                    <p class="text-surface-500 mt-1">Se dibuja con base en la categoría operativa y guarda automáticamente al dejar de escribir 1 segundo.</p>
                </div>
                <div class="w-full lg:w-auto min-w-72">
                    <label class="block text-sm font-semibold mb-2">Día contable <span class="text-red-500">*</span></label>
                    <DatePicker
                        v-model="fechaContableSeleccionada"
                        dateFormat="yy-mm-dd"
                        :minDate="fechaContableMinima"
                        :maxDate="fechaContableMaxima"
                        :manualInput="false"
                        class="w-full"
                    />
                    <small class="text-surface-500 block mt-1">El día donde se realiza la captura operativa. Verifica que sea el correcto.</small>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <Tag v-if="categoria" severity="info" :value="`Categoría: ${categoria.nombre}`" />
                    <Tag v-if="reporteActual" severity="contrast" :value="`Día contable: ${reporteActual.fecha_contable}`" />
                    <Tag v-if="reporteActual" :severity="reporteActual.estado_reporte === 'CERRADO' ? 'danger' : 'success'" :value="`Estado: ${reporteActual.estado_reporte}`" />
                    <Tag v-if="cargandoGuardado" severity="warn" value="Sincronizando cambios" />
                    <Button
                        icon="pi pi-lock"
                        label="Cierre de día"
                        severity="danger"
                        :loading="cerrandoDiaContable"
                        :disabled="!puedeCerrarDiaContable"
                        @click="cerrarDiaDesdeCaptura"
                    />
                </div>
            </div>
        </div>

        <Message v-if="mensajeCierreDiaContable" severity="success" :closable="false">{{ mensajeCierreDiaContable }}</Message>
        <Message v-if="capturaFueraHorario" severity="error" :closable="false">{{ mensajeBloqueoHorario }}</Message>

        <Message v-if="mensajePantalla" severity="warn" :closable="false">{{ mensajePantalla }}</Message>
        <Message v-else-if="reporteCerrado" severity="error" :closable="false">El día contable seleccionado está cerrado y no admite modificaciones.</Message>

        <div v-else class="card space-y-4">
            <div v-if="categoriaUsaSaldoInicialMensual" class="rounded-xl border border-surface-200 bg-surface-50 p-4 space-y-3">
                <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-lg font-semibold">Saldo inicial mensual de categoría</h3>
                    <small>formula de saldo inicial [saldo_inicial = - fondos fijos - perdidas - por comprobar + sobrantes]</small>
                    <Tag severity="info" :value="`Origen: ${origenSaldoInicialCategoria}`" />
                    <Tag
                        :severity="requiereCapturaManualSaldoInicial ? 'warn' : 'success'"
                        :value="requiereCapturaManualSaldoInicial ? 'Captura manual requerida' : 'Saldo inicial definido'"
                    />
                </div>

                <Message v-if="mensajeSaldoInicialCategoria" :severity="requiereCapturaManualSaldoInicial ? 'warn' : 'info'" :closable="false">
                    {{ mensajeSaldoInicialCategoria }}
                </Message>

                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Saldo inicial</small>
                        <MontoMonedaColoreado :monto="saldoInicialCategoriaMes" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Ingresos del mes</small>
                        <MontoMonedaColoreado :monto="ingresosCategoriaMes" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Egresos del mes</small>
                        <MontoMonedaColoreado :monto="egresosCategoriaMes" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Resultado neto del mes</small>
                        <MontoMonedaColoreado :monto="resultadoNetoCategoriaMes" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">{{ etiquetaQuintaTarjetaSaldoMensual }}</small>
                        <MontoMonedaColoreado :monto="montoQuintaTarjetaSaldoMensual" />
                    </div>
                </div>

                <div v-if="permiteCapturaManualSaldoInicial" class="grid grid-cols-1 md:grid-cols-3 gap-3 items-end border border-amber-300 bg-amber-50 rounded-lg p-3">
                    <div class="md:col-span-2">
                        <label class="block text-sm font-semibold mb-2">
                            Captura manual saldo inicial mensual <span class="text-red-500">*</span>
                        </label>
                        <InputNumber
                            v-model="montoSaldoInicialManual"
                            mode="decimal"
                            locale="en-US"
                            :minFractionDigits="2"
                            :maxFractionDigits="2"
                            :min="0"
                            :useGrouping="true"
                            class="w-full"
                            :disabled="capturaBloqueada || capturandoSaldoInicialManual"
                            placeholder="0.00"
                            @focus="limpiarSaldoInicialManualEnFoco"
                        />
                        <div class="mt-2">
                            <small class="text-surface-500 block mb-1">Vista previa monetaria</small>
                            <MontoMonedaColoreado :monto="normalizarNumero(montoSaldoInicialManual || 0)" />
                        </div>
                    </div>
                    <Button
                        icon="pi pi-save"
                        :label="requiereCapturaManualSaldoInicial ? 'Guardar saldo inicial' : 'Actualizar saldo inicial'"
                        class="w-full"
                        :loading="capturandoSaldoInicialManual"
                        :disabled="capturaBloqueada || capturandoSaldoInicialManual"
                        @click="guardarSaldoInicialCategoriaManual"
                    />
                </div>
            </div>

            <div class="rounded-xl border border-surface-200 bg-surface-50 p-4 space-y-3">
                <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-lg font-semibold">Saldo diario del día contable</h3>
                    <Tag severity="contrast" :value="`Día contable: ${fechaContableActivaEtiqueta}`" />
                    <Tag severity="info" value="Calculadora reactiva en pantalla" />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Ingresos del día</small>
                        <MontoMonedaColoreado :monto="ingresosCategoriaDia" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Egresos del día</small>
                        <MontoMonedaColoreado :monto="egresosCategoriaDia" />
                    </div>
                    <div class="rounded-lg border border-surface-200 bg-white p-3 space-y-1">
                        <small class="text-surface-500 block">Resultado neto del día</small>
                        <MontoMonedaColoreado :monto="resultadoNetoCategoriaDia" />
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
                <div class="lg:col-span-2">
                    <label class="block text-sm font-semibold mb-2">Agregar concepto a captura (opcional)</label>
                    <Select
                        v-model="conceptoNoRecurrenteSeleccionado"
                        :options="conceptosNoRecurrentesDisponibles"
                        optionLabel="nombre"
                        optionValue="id"
                        placeholder="Selecciona un concepto para agregar"
                        class="w-full"
                        :disabled="capturaBloqueada"
                        filter
                        filterPlaceholder="Buscar opción..."
                    />
                    <small v-if="categoriaPermiteConceptosDuplicados" class="text-surface-500 block mt-1">
                        Esta categoria tiene detalles parametrizados: puedes agregar el mismo concepto las veces necesarias.
                    </small>
                </div>
                <div class="flex items-end">
                    <Button
                        icon="pi pi-plus"
                        label="Agregar concepto"
                        class="w-full"
                        :disabled="!conceptoNoRecurrenteSeleccionado || capturaBloqueada"
                        @click="agregarConceptoNoRecurrente"
                    />
                </div>
            </div>

            <DataTable
                :value="conceptosVisibles"
                dataKey="__filaId"
                size="small"
                :loading="cargando"
                stripedRows
                responsiveLayout="scroll"
                class="w-full"
            >
                <Column field="nombre" header="Concepto" style="min-width: 16rem">
                    <template #body="slotProps">
                        <div class="flex flex-col gap-1">
                            <span class="font-semibold">{{ slotProps.data.nombre }}</span>
                            <div class="flex flex-wrap gap-1">
                                <Tag :severity="slotProps.data.tipo === 'INGRESO' ? 'success' : 'danger'" :value="slotProps.data.tipo" />
                                <Tag v-if="slotProps.data.__origenFila === 'recurrente'" severity="secondary" value="Recurrente base" />
                                <Tag v-else severity="contrast" value="Captura adicional" />
                                <Button
                                    v-if="categoriaPermiteConceptosDuplicados"
                                    icon="pi pi-plus"
                                    size="small"
                                    text
                                    severity="info"
                                    :disabled="capturaBloqueada"
                                    @click="agregarOtraCapturaConcepto(slotProps.data.__conceptoId)"
                                />
                                <Button
                                    v-if="slotProps.data.__origenFila !== 'recurrente'"
                                    icon="pi pi-trash"
                                    size="small"
                                    text
                                    severity="danger"
                                    :disabled="capturaBloqueada"
                                    @click="eliminarFilaCaptura(slotProps.data)"
                                />
                            </div>
                        </div>
                    </template>
                </Column>

                <Column field="monto" :header="esCategoriaDolares ? 'Monto (USD)' : 'Monto'" style="min-width: 18rem">
                    <template #body="slotProps">
                        <div class="space-y-2">
                            <div class="grid grid-cols-2 gap-3">
                                <InputNumber
                                    v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).monto"
                                    mode="decimal"
                                    locale="en-US"
                                    :minFractionDigits="2"
                                    :maxFractionDigits="2"
                                    class="w-full"
                                    :disabled="capturaBloqueada"
                                    placeholder="0.00"
                                    @focus="limpiarMontoEnFoco(slotProps.data.__filaId, slotProps.data.__conceptoId)"
                                    @input="manejarEntradaNumerica($event, slotProps.data.__filaId, slotProps.data.__conceptoId)"
                                />
                                <div class="rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 flex items-center justify-start">
                                    <MontoMonedaColoreado :monto="calcularMontoVistaPrevia(slotProps.data.__filaId)" />
                                </div>
                            </div>
                            <small v-if="esCategoriaDolares" class="text-surface-500 block">
                                Vista previa en MXN (tasa USD: {{ tasaCambioDolares.toFixed(4) }}).
                            </small>
                        </div>
                    </template>
                </Column>

                <Column
                    v-for="detalle in detallesActivos"
                    :key="detalle.id"
                    :field="`detalle-${detalle.clave}`"
                    :header="detalle.nombre"
                    style="min-width: 12rem"
                >
                    <template #body="slotProps">
                        <div class="space-y-2">
                            <InputText
                                v-if="detalle.tipo_valor === 'TEXT'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                class="w-full"
                                :disabled="capturaBloqueada"
                                :placeholder="detalle.requerido ? 'Dato obligatorio' : 'Dato opcional'"
                                @input="programarGuardado(slotProps.data.__filaId)"
                            />

                            <InputNumber
                                v-else-if="detalle.tipo_valor === 'DECIMAL'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                mode="decimal"
                                locale="en-US"
                                :minFractionDigits="2"
                                :maxFractionDigits="2"
                                class="w-full"
                                :disabled="capturaBloqueada"
                                placeholder="0.00"
                                @focus="limpiarMontoEnFoco(slotProps.data.__filaId, slotProps.data.__conceptoId, detalle.clave)"
                                @input="manejarEntradaNumerica($event, slotProps.data.__filaId, slotProps.data.__conceptoId, detalle.clave)"
                            />

                            <InputNumber
                                v-else-if="detalle.tipo_valor === 'INT'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                mode="decimal"
                                locale="en-US"
                                :minFractionDigits="0"
                                :maxFractionDigits="0"
                                class="w-full"
                                :disabled="capturaBloqueada"
                                placeholder="0"
                                @input="manejarEntradaNumerica($event, slotProps.data.__filaId, slotProps.data.__conceptoId, detalle.clave)"
                            />

                            <ToggleSwitch
                                v-else-if="detalle.tipo_valor === 'BOOLEAN'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                :disabled="capturaBloqueada"
                                @change="programarGuardado(slotProps.data.__filaId)"
                            />

                            <DatePicker
                                v-else-if="detalle.tipo_valor === 'DATE'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                dateFormat="yy-mm-dd"
                                class="w-full"
                                :disabled="capturaBloqueada"
                                @date-select="programarGuardado(slotProps.data.__filaId)"
                            />

                            <DatePicker
                                v-else-if="detalle.tipo_valor === 'DATETIME'"
                                v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).detalles[detalle.clave]"
                                dateFormat="yy-mm-dd"
                                showTime
                                hourFormat="24"
                                class="w-full"
                                :disabled="capturaBloqueada"
                                @date-select="programarGuardado(slotProps.data.__filaId)"
                            />
                        </div>
                    </template>
                </Column>

                <Column field="notas" header="Notas" style="min-width: 14rem">
                    <template #body="slotProps">
                        <InputText
                            v-model="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).notas"
                            class="w-full"
                            :disabled="capturaBloqueada"
                            placeholder="Nota opcional"
                            @input="programarGuardado(slotProps.data.__filaId)"
                        />
                    </template>
                </Column>

                <Column v-if="hayConceptosConEvidencia" header="Archivo" style="min-width: 16rem">
                    <template #body="slotProps">
                        <div v-if="slotProps.data.requiere_imagen" class="space-y-2">
                            <input
                                type="file"
                                accept="image/*,.pdf"
                                class="w-full text-sm"
                                :disabled="capturaBloqueada"
                                @change="manejarArchivoConcepto($event, slotProps.data.__filaId)"
                            />
                            <small class="text-surface-500 block">Opcional: puedes dejarlo en blanco.</small>
                            <small v-if="obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).archivoRespaldoNombre" class="text-primary-600 block">
                                Archivo actual: {{ obtenerEstadoCaptura(slotProps.data.__filaId, slotProps.data.__conceptoId).archivoRespaldoNombre }}
                            </small>
                        </div>
                        <small v-else class="text-surface-500">No aplica</small>
                    </template>
                </Column>

                <Column header="Estado" style="min-width: 10rem">
                    <template #body="slotProps">
                        <Tag :value="etiquetaEstadoFila(slotProps.data.__filaId).valor" :severity="etiquetaEstadoFila(slotProps.data.__filaId).severidad" />
                    </template>
                </Column>
            </DataTable>
        </div>
    </section>
</template>




