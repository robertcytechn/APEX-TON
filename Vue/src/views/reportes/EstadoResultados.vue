<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { listarSucursalesReporte, obtenerEstadoResultados, obtenerTipoCambioUsdMxnActual } from '@/service/estadoResultadosServicio';
import { useSesionStore } from '@/stores/sesion';
import { crearNombreArchivoExportacion } from '@/utils/nombresExportacion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const sucursales = ref([]);
const reportesPorMes = ref({});
const mensajeError = ref('');
const usandoDolares = ref(false);
const cargandoTipoCambio = ref(false);
const tipoCambioUsdMxn = ref(null);
const actualizadoTipoCambio = ref('');
const fuenteTipoCambio = ref('Sin consulta');
const mensajeTipoCambio = ref('');
const exportandoExcel = ref(false);
const exportandoPdf = ref(false);
const mensajeExitoExportacion = ref('');
const mensajeErrorExportacion = ref('');
const referenciaTablaEstadoResultados = ref(null);

const fechaActual = new Date();
const filtroSucursalId = ref(sesionStore.usuario?.sucursal_id || null);
const filtroAnio = ref(fechaActual.getFullYear());

const puedeVerControlesAvanzados = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));
const sucursalAsignadaId = computed(() => Number(sesionStore.usuario?.sucursal_id || 0));

const mesesAnio = [
    { valor: 1, nombre: 'ENERO', abreviatura: 'ENE' },
    { valor: 2, nombre: 'FEBRERO', abreviatura: 'FEB' },
    { valor: 3, nombre: 'MARZO', abreviatura: 'MAR' },
    { valor: 4, nombre: 'ABRIL', abreviatura: 'ABR' },
    { valor: 5, nombre: 'MAYO', abreviatura: 'MAY' },
    { valor: 6, nombre: 'JUNIO', abreviatura: 'JUN' },
    { valor: 7, nombre: 'JULIO', abreviatura: 'JUL' },
    { valor: 8, nombre: 'AGOSTO', abreviatura: 'AGO' },
    { valor: 9, nombre: 'SEPTIEMBRE', abreviatura: 'SEP' },
    { valor: 10, nombre: 'OCTUBRE', abreviatura: 'OCT' },
    { valor: 11, nombre: 'NOVIEMBRE', abreviatura: 'NOV' },
    { valor: 12, nombre: 'DICIEMBRE', abreviatura: 'DIC' }
];

const sucursalSeleccionada = computed(() => {
    return sucursales.value.find((sucursal) => Number(sucursal.id) === Number(filtroSucursalId.value)) || null;
});

const simboloMoneda = computed(() => (usandoDolares.value ? 'US$' : '$'));

const etiquetaActualizacionTipoCambio = computed(() => {
    if (!actualizadoTipoCambio.value) {
        return 'Actualizado: sin fecha reportada por la fuente';
    }
    return `Actualizado: ${actualizadoTipoCambio.value}`;
});

const etiquetaFuenteTipoCambio = computed(() => `Fuente TC: ${fuenteTipoCambio.value}`);

const textoCasinoEnCurso = computed(() => {
    return sucursalSeleccionada.value?.nombre || 'Sin casino asignado';
});

const textoAnioEnCurso = computed(() => `Año en curso: ${fechaActual.getFullYear()}`);

const tipoCambioFormateado = computed(() => {
    const valor = Number(tipoCambioUsdMxn.value || 0);
    if (!Number.isFinite(valor) || valor <= 0) {
        return '--';
    }
    return valor.toLocaleString('es-MX', {
        minimumFractionDigits: 4,
        maximumFractionDigits: 4,
    });
});

const etiquetaFuenteAnual = computed(() => {
    const fuentes = mesesAnio
        .map((mes) => String(reportesPorMes.value?.[mes.valor]?.fuente || ''))
        .filter((fuente) => fuente);

    if (!fuentes.length) {
        return 'Sin datos';
    }

    const unicas = [...new Set(fuentes)];
    if (unicas.length === 1) {
        return unicas[0] === 'snapshot_historico' ? 'Historico cerrado' : 'Tiempo real';
    }

    return 'Mixto (historico y tiempo real)';
});

const hayInformacionExportable = computed(() => Array.isArray(gruposRubrosAnuales.value) && gruposRubrosAnuales.value.length > 0);

// 1) Para que sirve: convertir montos de MXN a USD cuando se activa modo dolares.
// 2) Como funciona: divide entre tipo de cambio vigente y valida valores numericos.
// 3) Que hace: mantiene la misma tabla anual en dos monedas.
// 4) Como editarla: cambia formula si se agregan reglas especiales de conversion.
function montoConvertido(monto) {
    const valor = Number(monto || 0);
    if (!usandoDolares.value) {
        return valor;
    }

    const tipoCambio = Number(tipoCambioUsdMxn.value || 0);
    if (!Number.isFinite(tipoCambio) || tipoCambio <= 0) {
        return valor;
    }

    return valor / tipoCambio;
}

// 1) Para que sirve: normalizar texto para ordenamientos por nombre de padre/rubro.
// 2) Como funciona: elimina acentos y usa mayusculas sin espacios extra.
// 3) Que hace: evita inconsistencias al ordenar secciones del estado anual.
// 4) Como editarla: agrega reglas de reemplazo si aparecen nuevos caracteres.
function normalizarTexto(valor) {
    return String(valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .toUpperCase();
}

const resumenMensual = computed(() => {
    const mapa = {};

    for (const mes of mesesAnio) {
        const reporte = reportesPorMes.value?.[mes.valor] || {};
        const ingresos = Number(reporte.total_ingresos || 0);
        const egresos = Number(reporte.total_egresos || 0);
        const neto = Number(reporte.resultado_neto || ingresos - egresos);
        const saldoInicio = Number(reporte.saldo_arrastre_inicio || 0);
        const saldoFinal = Number(
            reporte.saldo_proyectado_fin ?? reporte.saldo_arrastre_fin ?? saldoInicio + neto
        );

        mapa[mes.valor] = {
            ingresos,
            egresos,
            neto,
            saldoInicio,
            saldoFinal,
            ingresosNoConsiderados: Number(reporte.total_ingresos_no_considerados || 0),
            egresosNoConsiderados: Number(reporte.total_egresos_no_considerados || 0),
            netoNoConsiderado: Number(reporte.resultado_neto_no_considerado || 0),
        };
    }

    return mapa;
});

const resumenAnual = computed(() => {
    const base = {
        totalIngresos: 0,
        totalEgresos: 0,
        totalNeto: 0,
        saldoInicio: 0,
        saldoFinal: 0,
        totalIngresosNoConsiderados: 0,
        totalEgresosNoConsiderados: 0,
        totalNetoNoConsiderado: 0,
    };

    let primerMesConDatos = null;
    let ultimoMesConDatos = null;

    for (const mes of mesesAnio) {
        const mensual = resumenMensual.value[mes.valor] || {};

        base.totalIngresos += Number(mensual.ingresos || 0);
        base.totalEgresos += Number(mensual.egresos || 0);
        base.totalNeto += Number(mensual.neto || 0);
        base.totalIngresosNoConsiderados += Number(mensual.ingresosNoConsiderados || 0);
        base.totalEgresosNoConsiderados += Number(mensual.egresosNoConsiderados || 0);
        base.totalNetoNoConsiderado += Number(mensual.netoNoConsiderado || 0);

        if (reportesPorMes.value?.[mes.valor]) {
            if (primerMesConDatos === null) {
                primerMesConDatos = mes.valor;
            }
            ultimoMesConDatos = mes.valor;
        }
    }

    if (primerMesConDatos !== null) {
        base.saldoInicio = Number(resumenMensual.value[primerMesConDatos]?.saldoInicio || 0);
    }

    if (ultimoMesConDatos !== null) {
        base.saldoFinal = Number(resumenMensual.value[ultimoMesConDatos]?.saldoFinal || 0);
    } else {
        base.saldoFinal = base.saldoInicio + base.totalNeto;
    }

    return base;
});

const rubrosAnuales = computed(() => {
    const mapa = new Map();

    for (const mes of mesesAnio) {
        const reporteMes = reportesPorMes.value?.[mes.valor];
        const rubrosMes = Array.isArray(reporteMes?.por_rubro) ? reporteMes.por_rubro : [];

        for (const rubroMes of rubrosMes) {
            const rubroId = String(rubroMes?.rubro_id ?? `SIN_RUBRO_${rubroMes?.rubro_nombre || 'RUBRO'}`);
            const tipoMovimiento = String(rubroMes?.rubro_tipo || 'INGRESO').toUpperCase() === 'EGRESO' ? 'EGRESO' : 'INGRESO';
            const montoMes = tipoMovimiento === 'EGRESO'
                ? Number(rubroMes?.total_egresos || 0)
                : Number(rubroMes?.total_ingresos || 0);

            if (!mapa.has(rubroId)) {
                const valoresIniciales = {};
                for (const itemMes of mesesAnio) {
                    valoresIniciales[itemMes.valor] = 0;
                }

                mapa.set(rubroId, {
                    rubro_id: rubroId,
                    rubro_nombre: String(rubroMes?.rubro_nombre || 'SIN RUBRO CONTABLE'),
                    rubro_padre: String(rubroMes?.rubro_padre || 'SIN GRUPO'),
                    tipo_movimiento: tipoMovimiento,
                    considerar_en_totales: Boolean(rubroMes?.rubro_padre_considerar_en_estado_resultados ?? true),
                    valores: valoresIniciales,
                });
            }

            const fila = mapa.get(rubroId);
            fila.tipo_movimiento = tipoMovimiento;
            fila.considerar_en_totales = Boolean(rubroMes?.rubro_padre_considerar_en_estado_resultados ?? fila.considerar_en_totales);
            fila.valores[mes.valor] = montoMes;
        }
    }

    const filas = Array.from(mapa.values());

    return filas.sort((a, b) => {
        const padreA = normalizarTexto(a.rubro_padre);
        const padreB = normalizarTexto(b.rubro_padre);
        if (padreA !== padreB) {
            return padreA.localeCompare(padreB, 'es-MX');
        }
        return String(a.rubro_nombre || '').localeCompare(String(b.rubro_nombre || ''), 'es-MX');
    });
});

const gruposRubrosAnuales = computed(() => {
    const mapa = new Map();

    for (const rubro of rubrosAnuales.value) {
        const padre = String(rubro.rubro_padre || 'SIN GRUPO').trim() || 'SIN GRUPO';
        if (!mapa.has(padre)) {
            const totalesPorMes = {};
            for (const mes of mesesAnio) {
                totalesPorMes[mes.valor] = 0;
            }

            mapa.set(padre, {
                padre,
                rubros: [],
                totalesPorMes,
                considerarEnTotales: false,
            });
        }

        const grupo = mapa.get(padre);
        grupo.rubros.push(rubro);
        grupo.considerarEnTotales = grupo.considerarEnTotales || Boolean(rubro.considerar_en_totales);

        for (const mes of mesesAnio) {
            grupo.totalesPorMes[mes.valor] += Number(rubro.valores[mes.valor] || 0);
        }
    }

    const ordenPreferido = ['INGRESOS', 'GASTOS', 'EGRESOS', 'OTROS INGRESOS'];

    return Array.from(mapa.values())
        .map((grupo) => {
            grupo.rubros.sort((a, b) => String(a.rubro_nombre || '').localeCompare(String(b.rubro_nombre || ''), 'es-MX'));
            return grupo;
        })
        .sort((a, b) => {
            const indiceA = ordenPreferido.indexOf(normalizarTexto(a.padre));
            const indiceB = ordenPreferido.indexOf(normalizarTexto(b.padre));

            const prioridadA = indiceA === -1 ? 999 : indiceA;
            const prioridadB = indiceB === -1 ? 999 : indiceB;
            if (prioridadA !== prioridadB) {
                return prioridadA - prioridadB;
            }

            return normalizarTexto(a.padre).localeCompare(normalizarTexto(b.padre), 'es-MX');
        });
});

// 1) Para que sirve: cargar catalogo de sucursales activas para filtros.
// 2) Como funciona: consulta API, filtra estado ACTIVO y ordena alfabeticamente.
// 3) Que hace: prepara selector de casino para consulta anual.
// 4) Como editarla: agrega criterios de acceso por rol si backend lo expone.
const cargarSucursales = async () => {
    const { data } = await listarSucursalesReporte();
    const listado = Array.isArray(data?.data) ? data.data : [];
    sucursales.value = listado
        .filter((sucursal) => sucursal.estado === 'ACTIVO')
        .sort((a, b) => (a.nombre || '').localeCompare(b.nombre || '', 'es-MX'));

    if (!puedeVerControlesAvanzados.value) {
        filtroSucursalId.value = sucursalAsignadaId.value || null;
        return;
    }

    if (!filtroSucursalId.value && sucursales.value.length) {
        filtroSucursalId.value = sucursales.value[0].id;
    }
};

// 1) Para que sirve: consultar estado de resultados para los 12 meses del anio.
// 2) Como funciona: ejecuta 12 consultas mensuales al endpoint actual y consolida en memoria.
// 3) Que hace: alimenta la maquetacion anual tipo Excel sin cambiar logica del backend.
// 4) Como editarla: cambia Promise.all por paginacion si negocio exige otra estrategia.
const cargarEstadoResultadosAnual = async () => {
    mensajeError.value = '';
    limpiarMensajesExportacion();

    if (!puedeVerControlesAvanzados.value) {
        filtroSucursalId.value = sucursalAsignadaId.value || null;
        filtroAnio.value = fechaActual.getFullYear();
        usandoDolares.value = false;
    }

    if (!filtroSucursalId.value) {
        reportesPorMes.value = {};
        mensajeError.value = puedeVerControlesAvanzados.value
            ? 'Selecciona un casino para consultar el estado de resultados.'
            : 'Tu usuario no tiene un casino asignado. Solicita apoyo al administrador.';
        return;
    }

    const anioConsulta = Number(filtroAnio.value || fechaActual.getFullYear());
    if (!Number.isFinite(anioConsulta) || anioConsulta < 2000 || anioConsulta > 2100) {
        filtroAnio.value = fechaActual.getFullYear();
    } else {
        filtroAnio.value = anioConsulta;
    }

    cargando.value = true;
    try {
        const resultados = await Promise.all(
            mesesAnio.map(async (mes) => {
                try {
                    const { data } = await obtenerEstadoResultados({
                        sucursal_id: filtroSucursalId.value,
                        anio: filtroAnio.value,
                        mes: mes.valor,
                    });
                    return {
                        mes: mes.valor,
                        data: data?.data || null,
                        error: null,
                    };
                } catch (errorMes) {
                    return {
                        mes: mes.valor,
                        data: null,
                        error: errorMes,
                    };
                }
            })
        );

        const mapaMeses = {};
        const mesesConError = [];

        for (const resultado of resultados) {
            mapaMeses[resultado.mes] = resultado.data;
            if (resultado.error) {
                mesesConError.push(resultado.mes);
            }
        }

        reportesPorMes.value = mapaMeses;

        if (mesesConError.length === 12) {
            throw new Error('No se pudo consultar ningun mes del anio seleccionado.');
        }

        if (mesesConError.length > 0) {
            const etiquetasMeses = mesesConError
                .map((mesError) => mesesAnio.find((mes) => mes.valor === mesError)?.nombre || String(mesError))
                .join(', ');
            mensajeError.value = `Algunos meses no pudieron consultarse: ${etiquetasMeses}.`;
        }
    } catch (error) {
        reportesPorMes.value = {};
        mensajeError.value = error?.response?.data?.message || error?.message || 'No se pudo obtener el estado de resultados anual.';
    } finally {
        cargando.value = false;
    }
};

// 1) Para que sirve: activar visualizacion en dolares con tipo de cambio en vivo.
// 2) Como funciona: consulta servicio externo y guarda metadatos de fuente.
// 3) Que hace: habilita conversion monetaria informativa para todo el anio.
// 4) Como editarla: agrega estrategia de fallback si se suman nuevas fuentes.
const activarModoDolares = async () => {
    mensajeTipoCambio.value = '';
    cargandoTipoCambio.value = true;

    try {
        const respuesta = await obtenerTipoCambioUsdMxnActual();
        tipoCambioUsdMxn.value = Number(respuesta.tipoCambio);
        actualizadoTipoCambio.value = respuesta.actualizadoEn || '';
        fuenteTipoCambio.value = respuesta.fuente || 'No especificada';
        usandoDolares.value = true;
    } catch (error) {
        usandoDolares.value = false;
        mensajeTipoCambio.value = error?.message || 'No se pudo consultar el tipo de cambio.';
    } finally {
        cargandoTipoCambio.value = false;
    }
};

// 1) Para que sirve: alternar entre vista en MXN y USD.
// 2) Como funciona: desactiva USD si esta activo o consulta tipo de cambio para activarlo.
// 3) Que hace: simplifica el cambio de moneda para el tablero anual.
// 4) Como editarla: agrega persistencia si negocio requiere recordar preferencia.
const cambiarModoMoneda = async () => {
    if (usandoDolares.value) {
        usandoDolares.value = false;
        return;
    }

    await activarModoDolares();
};

// 1) Para que sirve: limpiar alertas de exportacion antes de iniciar una nueva descarga.
// 2) Como funciona: reinicia mensajes de exito y error de exportaciones.
// 3) Que hace: evita mostrar estados obsoletos al usuario.
// 4) Como editarla: agrega nuevos campos si se suman mas tipos de alertas.
function limpiarMensajesExportacion() {
    mensajeExitoExportacion.value = '';
    mensajeErrorExportacion.value = '';
}

// 1) Para que sirve: convertir una fecha Date a formato ISO local YYYY-MM-DD.
// 2) Como funciona: compone anio, mes y dia con relleno de ceros.
// 3) Que hace: homologa metadata de exportacion para encabezados y nombres de archivo.
// 4) Como editarla: centraliza cambios de formato si se requiere otro estandar.
function obtenerFechaIsoLocal(fecha) {
    const fechaValida = fecha instanceof Date && !Number.isNaN(fecha.getTime()) ? fecha : new Date();
    const anio = String(fechaValida.getFullYear());
    const mes = String(fechaValida.getMonth() + 1).padStart(2, '0');
    const dia = String(fechaValida.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

// 1) Para que sirve: formatear fechas ISO a texto legible para reportes exportados.
// 2) Como funciona: parsea la fecha en zona local y aplica locale es-MX.
// 3) Que hace: presenta fechas consistentes en Excel y PDF.
// 4) Como editarla: ajusta locale o formato si direccion solicita otro estandar.
function formatearFechaIso(fechaIso) {
    const texto = String(fechaIso || '').trim();
    if (!texto) {
        return '--';
    }

    const partes = texto.split('-').map((segmento) => Number(segmento));
    if (partes.length !== 3 || partes.some((parte) => !Number.isInteger(parte))) {
        return '--';
    }

    const fecha = new Date(partes[0], partes[1] - 1, partes[2]);
    return fecha.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    });
}

// 1) Para que sirve: obtener el rango anual visible en la pantalla actual.
// 2) Como funciona: construye fechas inicio/fin con base en el filtro de anio.
// 3) Que hace: aporta periodo estandar para metadata y naming de archivos.
// 4) Como editarla: cambia limites si negocio requiere periodos fiscales distintos.
function obtenerRangoAnualIsoExportacion() {
    const anioActual = fechaActual.getFullYear();
    const anioSeleccionado = Number(filtroAnio.value || anioActual);
    const anioSeguro = Number.isFinite(anioSeleccionado) ? anioSeleccionado : anioActual;

    return {
        fechaInicio: `${anioSeguro}-01-01`,
        fechaFin: `${anioSeguro}-12-31`,
    };
}

// 1) Para que sirve: construir etiqueta textual del periodo anual exportado.
// 2) Como funciona: toma rango ISO y lo convierte a formato legible.
// 3) Que hace: contextualiza la salida en encabezados de documentos.
// 4) Como editarla: agrega trimestre o corte contable si se solicita.
function obtenerPeriodoAnualTextoExportacion() {
    const rango = obtenerRangoAnualIsoExportacion();
    return `${formatearFechaIso(rango.fechaInicio)} al ${formatearFechaIso(rango.fechaFin)}`;
}

// 1) Para que sirve: resolver nombre de casino visible para metadata de exportacion.
// 2) Como funciona: toma sucursal seleccionada y aplica fallback seguro.
// 3) Que hace: evita archivos sin identificador de casino.
// 4) Como editarla: cambia fallback si se define nomenclatura corporativa distinta.
function obtenerNombreCasinoExportacion() {
    return String(sucursalSeleccionada.value?.nombre || 'sin_casino');
}

// 1) Para que sirve: convertir valores a numero seguro en salidas exportables.
// 2) Como funciona: valida Number finito y retorna 0 ante valores invalidos.
// 3) Que hace: previene celdas NaN o errores de formato.
// 4) Como editarla: agrega redondeo fijo si contabilidad lo requiere.
function convertirNumeroExportacion(valor) {
    const numero = Number(valor || 0);
    return Number.isFinite(numero) ? numero : 0;
}

// 1) Para que sirve: dar formato monetario uniforme en los textos del PDF.
// 2) Como funciona: aplica Intl.NumberFormat con dos decimales.
// 3) Que hace: mantiene coherencia visual con la interfaz.
// 4) Como editarla: cambia locale o precision para otro pais o regla.
function formatearMontoExportacion(valor) {
    return new Intl.NumberFormat('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(convertirNumeroExportacion(valor));
}

// 1) Para que sirve: recortar texto largo en celdas del PDF para no desbordar.
// 2) Como funciona: limita longitud y agrega puntos suspensivos.
// 3) Que hace: mejora legibilidad en columnas estrechas.
// 4) Como editarla: ajusta largo maximo cuando cambien anchos de columna.
function truncarTexto(valor, longitudMaxima) {
    const texto = String(valor ?? '');
    if (texto.length <= longitudMaxima) {
        return texto;
    }
    return `${texto.slice(0, Math.max(0, longitudMaxima - 3))}...`;
}

// 1) Para que sirve: generar una estructura plana de filas para exportacion anual.
// 2) Como funciona: recorre grupos/rubros y agrega resumenes mensuales/anuales.
// 3) Que hace: centraliza la fuente de datos para Excel y PDF.
// 4) Como editarla: incorpora nuevas filas de negocio sin duplicar logica.
function construirFilasPlanoEstadoResultadosExportacion() {
    const filas = [];

    for (const grupo of gruposRubrosAnuales.value) {
        filas.push({
            tipo: 'GRUPO',
            padre: String(grupo?.padre || ''),
            rubro: '',
            valoresMes: null,
            totalAnual: null,
        });

        for (const rubro of grupo?.rubros || []) {
            const valoresMes = {};
            for (const mes of mesesAnio) {
                valoresMes[mes.valor] = convertirNumeroExportacion(montoConvertido(rubro?.valores?.[mes.valor] || 0));
            }

            filas.push({
                tipo: 'RUBRO',
                padre: '',
                rubro: String(rubro?.rubro_nombre || 'SIN RUBRO CONTABLE'),
                valoresMes,
                totalAnual: null,
            });
        }

        const valoresTotalesGrupo = {};
        for (const mes of mesesAnio) {
            valoresTotalesGrupo[mes.valor] = convertirNumeroExportacion(montoConvertido(grupo?.totalesPorMes?.[mes.valor] || 0));
        }

        filas.push({
            tipo: 'TOTAL_GRUPO',
            padre: '',
            rubro: `Total ${String(grupo?.padre || '')}`,
            valoresMes: valoresTotalesGrupo,
            totalAnual: null,
        });
    }

    const valoresIngresos = {};
    const valoresEgresos = {};
    const valoresNeto = {};
    for (const mes of mesesAnio) {
        valoresIngresos[mes.valor] = convertirNumeroExportacion(montoConvertido(resumenMensual.value?.[mes.valor]?.ingresos || 0));
        valoresEgresos[mes.valor] = convertirNumeroExportacion(montoConvertido(resumenMensual.value?.[mes.valor]?.egresos || 0));
        valoresNeto[mes.valor] = convertirNumeroExportacion(montoConvertido(resumenMensual.value?.[mes.valor]?.neto || 0));
    }

    filas.push({
        tipo: 'RESUMEN_INGRESOS',
        padre: '',
        rubro: 'TOTAL INGRESOS',
        valoresMes: valoresIngresos,
        totalAnual: null,
    });

    filas.push({
        tipo: 'RESUMEN_EGRESOS',
        padre: '',
        rubro: 'TOTAL GASTOS / EGRESOS',
        valoresMes: valoresEgresos,
        totalAnual: null,
    });

    filas.push({
        tipo: 'RESUMEN_NETO',
        padre: '',
        rubro: 'GANANCIA / PERDIDA',
        valoresMes: valoresNeto,
        totalAnual: null,
    });

    filas.push({
        tipo: 'TOTAL_ANUAL_FINAL',
        padre: '',
        rubro: 'TOTAL ANUAL ACUMULADO (GANANCIA / PERDIDA)',
        valoresMes: null,
        totalAnual: convertirNumeroExportacion(montoConvertido(resumenAnual.value?.totalNeto || 0)),
    });

    return filas;
}

// 1) Para que sirve: identificar el tipo visual de fila para estilos de Excel.
// 2) Como funciona: evalua clases CSS de la fila HTML original.
// 3) Que hace: permite replicar paleta y jerarquia del reporte en la hoja exportada.
// 4) Como editarla: agrega nuevos tipos cuando se incorporen filas especiales.
function obtenerTipoFilaEstiloExcel(indiceFila, filaDom) {
    if (indiceFila === 0) {
        return 'ENCABEZADO';
    }
    if (!filaDom) {
        return 'NORMAL';
    }
    if (filaDom.classList.contains('fila-padre')) {
        return 'PADRE';
    }
    if (filaDom.classList.contains('fila-total-grupo')) {
        return 'TOTAL_GRUPO';
    }
    if (filaDom.classList.contains('fila-ingresos')) {
        return 'RESUMEN_INGRESOS';
    }
    if (filaDom.classList.contains('fila-egresos')) {
        return 'RESUMEN_EGRESOS';
    }
    if (filaDom.classList.contains('fila-neto')) {
        return 'RESUMEN_NETO';
    }
    if (filaDom.classList.contains('fila-total-anual-final')) {
        return 'TOTAL_ANUAL_FINAL';
    }
    if (filaDom.classList.contains('fila-rubro')) {
        return 'RUBRO';
    }
    return 'NORMAL';
}

// 1) Para que sirve: mapear paleta y tipografia por tipo de fila en Excel.
// 2) Como funciona: devuelve configuracion de fondo, texto y peso de fuente.
// 3) Que hace: mejora legibilidad y evita exportaciones planas en blanco.
// 4) Como editarla: ajusta colores para alinearse a identidad visual futura.
function obtenerPaletaFilaExcel(tipoFila) {
    const paletas = {
        ENCABEZADO: { fondo: '0F172A', texto: 'FFFFFF', negrita: true, cursiva: false },
        PADRE: { fondo: 'CFE0F4', texto: '1E40AF', negrita: true, cursiva: true },
        TOTAL_GRUPO: { fondo: 'E5EDF8', texto: '1E3A8A', negrita: true, cursiva: false },
        RESUMEN_INGRESOS: { fondo: 'EEFBF4', texto: '166534', negrita: true, cursiva: false },
        RESUMEN_EGRESOS: { fondo: 'FFF1F2', texto: '9F1239', negrita: true, cursiva: false },
        RESUMEN_NETO: { fondo: 'E9F0FC', texto: '1E3A8A', negrita: true, cursiva: false },
        TOTAL_ANUAL_FINAL: { fondo: 'DBEAFE', texto: '1E3A8A', negrita: true, cursiva: false },
        RUBRO: { fondo: 'FFFFFF', texto: '0F172A', negrita: false, cursiva: false },
        NORMAL: { fondo: 'FFFFFF', texto: '1E293B', negrita: false, cursiva: false },
    };
    return paletas[tipoFila] || paletas.NORMAL;
}

// 1) Para que sirve: generar borde estandar para todas las celdas exportadas.
// 2) Como funciona: define trazo fino uniforme en los cuatro lados.
// 3) Que hace: mejora separacion visual y lectura tabular en Excel.
// 4) Como editarla: cambia grosor o color si diseno corporativo lo requiere.
function obtenerBordeBaseExcel() {
    return {
        top: { style: 'thin', color: { rgb: 'CBD5E1' } },
        right: { style: 'thin', color: { rgb: 'CBD5E1' } },
        bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
        left: { style: 'thin', color: { rgb: 'CBD5E1' } },
    };
}

// 1) Para que sirve: aplicar estilos visuales en la hoja de Excel generada.
// 2) Como funciona: recorre celdas segun rango y toma referencia de clases HTML.
// 3) Que hace: replica apariencia del reporte (colores, bordes y alineacion).
// 4) Como editarla: ajusta anchos, alturas o formato monetario segun necesidad.
function aplicarEstilosHojaExcelEstadoResultados(XLSX, hojaEstadoAnual, tablaHtml) {
    const referencia = String(hojaEstadoAnual?.['!ref'] || '').trim();
    if (!referencia) {
        return;
    }

    const rango = XLSX.utils.decode_range(referencia);
    const totalColumnas = (rango.e.c - rango.s.c) + 1;
    const filasDom = Array.from(tablaHtml.querySelectorAll('tr'));

    hojaEstadoAnual['!cols'] = [
        { wch: 14 },
        { wch: 34 },
        ...mesesAnio.map(() => ({ wch: 14 })),
    ];
    hojaEstadoAnual['!rows'] = filasDom.map((_, indice) => ({ hpt: indice === 0 ? 22 : 19 }));

    for (let indiceFila = 0; indiceFila <= rango.e.r; indiceFila += 1) {
        const filaDom = filasDom[indiceFila];
        const tipoFila = obtenerTipoFilaEstiloExcel(indiceFila, filaDom);
        const paleta = obtenerPaletaFilaExcel(tipoFila);

        for (let indiceColumna = 0; indiceColumna < totalColumnas; indiceColumna += 1) {
            const referenciaCelda = XLSX.utils.encode_cell({ r: indiceFila, c: indiceColumna });
            if (!hojaEstadoAnual[referenciaCelda]) {
                hojaEstadoAnual[referenciaCelda] = { t: 's', v: '' };
            }

            const celda = hojaEstadoAnual[referenciaCelda];
            const esEncabezado = tipoFila === 'ENCABEZADO';
            const esMonto = indiceColumna >= 2;

            celda.s = {
                font: {
                    name: 'Calibri',
                    sz: 10,
                    bold: Boolean(paleta.negrita),
                    italic: Boolean(paleta.cursiva),
                    color: { rgb: paleta.texto },
                },
                fill: {
                    patternType: 'solid',
                    fgColor: { rgb: paleta.fondo },
                    bgColor: { rgb: paleta.fondo },
                },
                border: obtenerBordeBaseExcel(),
                alignment: {
                    horizontal: esEncabezado ? 'center' : (esMonto ? 'right' : 'left'),
                    vertical: 'center',
                    wrapText: !esMonto,
                },
            };

            if (!esEncabezado && esMonto && tipoFila !== 'PADRE') {
                celda.z = '#,##0.00';
            }
        }
    }
}

// 1) Para que sirve: exportar el estado de resultados anual a Excel nativo.
// 2) Como funciona: clona la tabla HTML renderizada y la convierte con table_to_sheet.
// 3) Que hace: asegura que el Excel salga igual que la tabla visible en pantalla.
// 4) Como editarla: manten la exportacion ligada al ref de tabla si cambia el template.
async function exportarExcelEstadoResultadosAnual() {
    if (!hayInformacionExportable.value) {
        mensajeErrorExportacion.value = 'No hay datos en pantalla para exportar a Excel.';
        return;
    }

    exportandoExcel.value = true;
    limpiarMensajesExportacion();

    try {
        const moduloXlsx = await import('xlsx-js-style');
        const XLSX = moduloXlsx?.default || moduloXlsx;
        const libro = XLSX.utils.book_new();
        const nombreCasino = obtenerNombreCasinoExportacion();
        const tabla = referenciaTablaEstadoResultados.value;
        if (!tabla) {
            throw new Error('No se encontro la tabla anual para exportar.');
        }

        const tablaClon = tabla.cloneNode(true);
        const hojaEstadoAnual = XLSX.utils.table_to_sheet(tablaClon, {
            raw: false,
        });
        aplicarEstilosHojaExcelEstadoResultados(XLSX, hojaEstadoAnual, tablaClon);

        XLSX.utils.book_append_sheet(libro, hojaEstadoAnual, 'Estado_Anual');

        const rango = obtenerRangoAnualIsoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estado_resultados',
            tipo: 'anual',
            casino: nombreCasino,
            fechaInicio: rango.fechaInicio,
            fechaFin: rango.fechaFin,
            extension: 'xlsx',
        });

        XLSX.writeFile(libro, nombreArchivo);
        mensajeExitoExportacion.value = 'Exportacion Excel completada correctamente con estilos y tabla completa.';
    } catch (error) {
        mensajeErrorExportacion.value = error?.message || 'No se pudo exportar el archivo Excel.';
    } finally {
        exportandoExcel.value = false;
    }
}

// 1) Para que sirve: definir color de fondo por tipo de fila en PDF vectorial.
// 2) Como funciona: mapea cada tipo de fila a una tonalidad consistente.
// 3) Que hace: conserva jerarquia visual del reporte anual.
// 4) Como editarla: ajusta paleta segun lineamientos de diseno.
function colorFondoFilaPdf(tipoFila) {
    const tipo = String(tipoFila || '');
    if (tipo === 'GRUPO') {
        return '#cfe0f4';
    }
    if (tipo === 'TOTAL_GRUPO') {
        return '#e5edf8';
    }
    if (tipo === 'RESUMEN_INGRESOS') {
        return '#eefbf4';
    }
    if (tipo === 'RESUMEN_EGRESOS') {
        return '#fff1f2';
    }
    if (tipo === 'RESUMEN_NETO') {
        return '#e9f0fc';
    }
    if (tipo === 'TOTAL_ANUAL_FINAL') {
        return '#dbeafe';
    }
    return '#ffffff';
}

// 1) Para que sirve: convertir un color hexadecimal a componentes RGB.
// 2) Como funciona: interpreta pares hexadecimales y valida formato.
// 3) Que hace: permite aplicar paleta de filas en jsPDF.
// 4) Como editarla: amplia soporte si se agregan formatos cortos de color.
function convertirHexARgb(hexadecimal) {
    const color = String(hexadecimal || '').trim().replace('#', '');
    if (!/^[0-9a-fA-F]{6}$/.test(color)) {
        return { r: 255, g: 255, b: 255 };
    }

    return {
        r: Number.parseInt(color.slice(0, 2), 16),
        g: Number.parseInt(color.slice(2, 4), 16),
        b: Number.parseInt(color.slice(4, 6), 16),
    };
}

// 1) Para que sirve: dibujar una pagina completa del PDF anual en jsPDF.
// 2) Como funciona: renderiza encabezado, metadata y tabla con lineas vectoriales.
// 3) Que hace: genera PDF nitido sin depender de conversion SVG.
// 4) Como editarla: ajusta anchos/alto de filas si cambia el layout del reporte.
function dibujarPaginaPdfEstadoResultados({
    documento,
    filasPagina,
    numeroPagina,
    totalPaginas,
    anchoPagina,
    altoPagina,
    margen,
    fechaExportacion,
    periodo,
    casino,
    moneda,
    totalAnual,
}) {
    const anchoContenido = anchoPagina - (margen * 2);
    const anchoPadre = 108;
    const anchoRubro = 220;
    const anchoMesBase = Math.floor((anchoContenido - anchoPadre - anchoRubro) / mesesAnio.length);
    const anchosMes = mesesAnio.map(() => anchoMesBase);
    const anchoMesesActual = anchosMes.reduce((acumulado, valor) => acumulado + valor, 0);
    const faltanteMeses = anchoContenido - anchoPadre - anchoRubro - anchoMesesActual;
    if (anchosMes.length > 0) {
        anchosMes[anchosMes.length - 1] += faltanteMeses;
    }

    const anchosColumnas = [anchoPadre, anchoRubro, ...anchosMes];
    const altoFila = 18;
    const altoEncabezadoTabla = 22;
    const inicioTablaY = margen + 112;
    documento.setFillColor(255, 255, 255);
    documento.rect(0, 0, anchoPagina, altoPagina, 'F');

    documento.setTextColor(15, 23, 42);
    documento.setFont('helvetica', 'bold');
    documento.setFontSize(16);
    documento.text('Estado de Resultados Anual', margen, margen + 16);

    documento.setTextColor(51, 65, 85);
    documento.setFont('helvetica', 'normal');
    documento.setFontSize(10);
    documento.text(`Fecha de exportacion: ${fechaExportacion}`, margen, margen + 36);
    documento.text(`Periodo: ${periodo}`, margen, margen + 52);
    documento.text(`Casino: ${casino}`, margen, margen + 68);
    documento.text(`Moneda visible: ${moneda}`, margen, margen + 84);
    documento.text(`Total anual: ${formatearMontoExportacion(totalAnual)}`, anchoPagina - margen, margen + 52, { align: 'right' });
    documento.text(`Pagina ${numeroPagina} de ${totalPaginas}`, anchoPagina - margen, margen + 68, { align: 'right' });

    documento.setFillColor(15, 23, 42);
    documento.rect(margen, inicioTablaY, anchoContenido, altoEncabezadoTabla, 'F');

    const encabezados = ['PADRE', 'RUBRO', ...mesesAnio.map((mes) => mes.abreviatura)];
    let cursorXEncabezado = margen;
    documento.setTextColor(255, 255, 255);
    documento.setFont('helvetica', 'bold');
    documento.setFontSize(9);
    for (let indice = 0; indice < encabezados.length; indice += 1) {
        const anchoColumna = anchosColumnas[indice];
        const textoEncabezado = encabezados[indice];
        const esMonto = indice >= 2;
        const xTexto = esMonto ? cursorXEncabezado + anchoColumna - 5 : cursorXEncabezado + 5;
        if (esMonto) {
            documento.text(textoEncabezado, xTexto, inicioTablaY + 15, { align: 'right' });
        } else {
            documento.text(textoEncabezado, xTexto, inicioTablaY + 15);
        }
        cursorXEncabezado += anchoColumna;
    }

    filasPagina.forEach((fila, indiceFila) => {
        const yFila = inicioTablaY + altoEncabezadoTabla + (indiceFila * altoFila);
        const tipoFila = String(fila?.tipo || '');
        const colorFondo = convertirHexARgb(colorFondoFilaPdf(tipoFila));
        const pesoTexto = ['GRUPO', 'TOTAL_GRUPO', 'RESUMEN_INGRESOS', 'RESUMEN_EGRESOS', 'RESUMEN_NETO', 'TOTAL_ANUAL_FINAL'].includes(tipoFila)
            ? '700'
            : '500';

        documento.setFillColor(colorFondo.r, colorFondo.g, colorFondo.b);
        documento.rect(margen, yFila, anchoContenido, altoFila, 'F');

        if (tipoFila === 'GRUPO') {
            documento.setTextColor(30, 64, 175);
        } else {
            documento.setTextColor(30, 41, 59);
        }
        documento.setFont('helvetica', pesoTexto === '700' ? 'bold' : 'normal');
        documento.setFontSize(8.2);

        const valores = [
            truncarTexto(fila?.padre || '', 18),
            truncarTexto(fila?.rubro || '', 44),
            ...mesesAnio.map((mes) => {
                if (!fila?.valoresMes) {
                    return '';
                }
                return formatearMontoExportacion(fila.valoresMes[mes.valor]);
            }),
        ];

        if (tipoFila === 'TOTAL_ANUAL_FINAL' && valores.length > 2) {
            valores[valores.length - 1] = formatearMontoExportacion(fila?.totalAnual || 0);
        }

        let cursorX = margen;
        for (let indiceColumna = 0; indiceColumna < valores.length; indiceColumna += 1) {
            const anchoColumna = anchosColumnas[indiceColumna];
            const esMonto = indiceColumna >= 2;
            const xTexto = esMonto ? cursorX + anchoColumna - 5 : cursorX + 5;
            const texto = String(valores[indiceColumna] || '');
            if (esMonto) {
                documento.text(texto, xTexto, yFila + 12.5, { align: 'right' });
            } else {
                documento.text(texto, xTexto, yFila + 12.5);
            }
            cursorX += anchoColumna;
        }
    });

    const altoTabla = altoEncabezadoTabla + (filasPagina.length * altoFila);
    const yFinalTabla = inicioTablaY + altoTabla;
    documento.setDrawColor(148, 163, 184);
    documento.rect(margen, inicioTablaY, anchoContenido, altoTabla);

    let cursorXLinea = margen;
    anchosColumnas.forEach((anchoColumna) => {
        cursorXLinea += anchoColumna;
        documento.setDrawColor(203, 213, 225);
        documento.line(cursorXLinea, inicioTablaY, cursorXLinea, yFinalTabla);
    });

    for (let indiceFila = 0; indiceFila <= filasPagina.length; indiceFila += 1) {
        const yLinea = inicioTablaY + altoEncabezadoTabla + (indiceFila * altoFila);
        documento.setDrawColor(226, 232, 240);
        documento.line(margen, yLinea, margen + anchoContenido, yLinea);
    }
}

// 1) Para que sirve: exportar el estado anual a PDF multipagina en vector directo.
// 2) Como funciona: dibuja cada pagina en jsPDF sin conversion intermedia a SVG.
// 3) Que hace: evita errores de dependencias ESM y mantiene nitidez en la salida.
// 4) Como editarla: ajusta formato, orientacion o densidad de filas por pagina.
async function exportarPdfEstadoResultadosAnual() {
    if (!hayInformacionExportable.value) {
        mensajeErrorExportacion.value = 'No hay datos en pantalla para exportar a PDF.';
        return;
    }

    exportandoPdf.value = true;
    limpiarMensajesExportacion();

    try {
        const { jsPDF } = await import('jspdf');

        const documento = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a3' });
        const anchoPagina = documento.internal.pageSize.getWidth();
        const altoPagina = documento.internal.pageSize.getHeight();
        const margen = 22;
        const altoFila = 18;
        const altoEncabezadoTabla = 22;
        const inicioTablaY = margen + 112;
        const altoDisponibleTabla = altoPagina - margen - inicioTablaY;
        const filasPorPagina = Math.max(1, Math.floor((altoDisponibleTabla - altoEncabezadoTabla) / altoFila));

        const filasExportacion = construirFilasPlanoEstadoResultadosExportacion();
        const totalPaginas = Math.max(1, Math.ceil(filasExportacion.length / filasPorPagina));
        const fechaExportacion = formatearFechaIso(obtenerFechaIsoLocal(new Date()));
        const periodo = obtenerPeriodoAnualTextoExportacion();
        const casino = obtenerNombreCasinoExportacion();
        const moneda = usandoDolares.value ? 'USD (conversion informativa)' : 'MXN';
        const totalAnual = convertirNumeroExportacion(montoConvertido(resumenAnual.value?.totalNeto || 0));

        for (let indicePagina = 0; indicePagina < totalPaginas; indicePagina += 1) {
            if (indicePagina > 0) {
                documento.addPage();
            }

            const inicio = indicePagina * filasPorPagina;
            const fin = inicio + filasPorPagina;
            const filasPagina = filasExportacion.slice(inicio, fin);

            dibujarPaginaPdfEstadoResultados({
                documento,
                filasPagina,
                numeroPagina: indicePagina + 1,
                totalPaginas,
                anchoPagina,
                altoPagina,
                margen,
                fechaExportacion,
                periodo,
                casino,
                moneda,
                totalAnual,
            });
        }

        const rango = obtenerRangoAnualIsoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estado_resultados',
            tipo: 'anual_pdf',
            casino,
            fechaInicio: rango.fechaInicio,
            fechaFin: rango.fechaFin,
            extension: 'pdf',
        });

        documento.save(nombreArchivo);
        mensajeExitoExportacion.value = 'Exportacion PDF completada correctamente.';
    } catch (error) {
        mensajeErrorExportacion.value = error?.message || 'No se pudo exportar el PDF.';
    } finally {
        exportandoPdf.value = false;
    }
}

onMounted(async () => {
    await cargarSucursales();
    await cargarEstadoResultadosAnual();
});
</script>

<template>
    <section class="estado-anual max-w-[96vw] mx-auto space-y-4 pb-8">
        <div class="card border border-slate-200 rounded-xl p-4 md:p-5 space-y-4">
            <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <div>
                    <h1 class="text-2xl font-extrabold text-slate-800">Estado de Resultados</h1>
                </div>
                <div class="flex flex-wrap items-center gap-2 text-xs md:text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                    <span class="font-semibold text-slate-700">Casino:</span>
                    <span class="font-bold text-primary-700">{{ sucursalSeleccionada?.nombre || 'N/A' }}</span>
                    <span class="text-slate-300">|</span>
                    <span class="font-semibold text-slate-700">Año:</span>
                    <span class="font-bold text-slate-900">{{ filtroAnio }}</span>
                    <span class="text-slate-300">|</span>
                    <span class="font-semibold text-slate-700">Fuente:</span>
                    <span class="font-bold text-slate-900">{{ etiquetaFuenteAnual }}</span>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div v-if="puedeVerControlesAvanzados">
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">Casino <span class="text-red-500">*</span></label>
                    <Select
                        v-model="filtroSucursalId"
                        :options="sucursales"
                        optionLabel="nombre"
                        optionValue="id"
                        placeholder="Selecciona casino"
                        class="w-full"
                        filter
                        filterPlaceholder="Buscar..."
                        @change="cargarEstadoResultadosAnual"
                    />
                </div>

                <div v-else>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">Casino visible</label>
                    <div class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 font-semibold">
                        {{ textoCasinoEnCurso }}
                    </div>
                </div>

                <div v-if="puedeVerControlesAvanzados">
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">Año <span class="text-red-500">*</span></label>
                    <InputNumber
                        v-model="filtroAnio"
                        :useGrouping="false"
                        :min="2020"
                        :max="2100"
                        class="w-full"
                        placeholder="Ej. 2026"
                        @blur="cargarEstadoResultadosAnual"
                    />
                </div>

                <div v-else>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">Periodo visible</label>
                    <div class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 font-semibold">
                        {{ textoAnioEnCurso }}
                    </div>
                </div>

                <div class="flex flex-wrap items-end gap-2">
                    <Button
                        icon="pi pi-refresh"
                        label="Actualizar"
                        :loading="cargando"
                        @click="cargarEstadoResultadosAnual"
                    />
                    <Button
                        v-if="puedeVerControlesAvanzados"
                        :icon="usandoDolares ? 'pi pi-money-bill' : 'pi pi-dollar'"
                        :label="usandoDolares ? 'Ver en MXN' : 'Convertir a USD'"
                        outlined
                        :loading="cargandoTipoCambio"
                        @click="cambiarModoMoneda"
                    />
                    <Button
                        icon="pi pi-file-excel"
                        label="Exportar Excel"
                        severity="success"
                        outlined
                        :loading="exportandoExcel"
                        :disabled="!hayInformacionExportable || cargando || exportandoPdf"
                        @click="exportarExcelEstadoResultadosAnual"
                    />
                    <Button
                        icon="pi pi-file-pdf"
                        label="Exportar PDF"
                        severity="danger"
                        outlined
                        :loading="exportandoPdf"
                        :disabled="!hayInformacionExportable || cargando || exportandoExcel"
                        @click="exportarPdfEstadoResultadosAnual"
                    />
                </div>
            </div>

            <div v-if="puedeVerControlesAvanzados" class="text-xs text-slate-500 flex flex-wrap gap-3">
                <span>1 USD = {{ tipoCambioFormateado }} MXN</span>
                <span>{{ etiquetaActualizacionTipoCambio }}</span>
                <span>{{ etiquetaFuenteTipoCambio }}</span>
            </div>
        </div>

        <Message v-if="mensajeTipoCambio" severity="warn" :closable="false">{{ mensajeTipoCambio }}</Message>
        <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>
        <Message v-if="mensajeExitoExportacion" severity="success" :closable="false">{{ mensajeExitoExportacion }}</Message>
        <Message v-if="mensajeErrorExportacion" severity="error" :closable="false">{{ mensajeErrorExportacion }}</Message>

        <div v-if="!cargando && gruposRubrosAnuales.length" class="card border border-slate-200 rounded-xl p-0 overflow-visible">
            <div class="contenedor-tabla-anual">
                <table ref="referenciaTablaEstadoResultados" class="tabla-excel-anual min-w-[1120px] w-full">
                    <thead>
                        <tr>
                            <th class="columna-padre">Padre</th>
                            <th class="columna-rubro">Rubro contable</th>
                            <th
                                v-for="mes in mesesAnio"
                                :key="`enc-${mes.valor}`"
                                class="columna-mes"
                                :title="mes.nombre"
                            >
                                {{ mes.abreviatura }}
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        <template v-for="grupo in gruposRubrosAnuales" :key="grupo.padre">
                            <tr class="fila-padre">
                                <td :colspan="mesesAnio.length + 2">
                                    <span class="font-bold">{{ grupo.padre }}</span>
                                    <span
                                        class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                                        :class="grupo.considerarEnTotales ? 'tag-impacta' : 'tag-informativo'"
                                    >
                                        {{ grupo.considerarEnTotales ? 'Impacta total' : 'Solo informativo' }}
                                    </span>
                                </td>
                            </tr>

                            <tr
                                v-for="rubro in grupo.rubros"
                                :key="`${grupo.padre}-${rubro.rubro_id}`"
                                class="fila-rubro"
                            >
                                <td class="celda-padre-vacia"></td>
                                <td class="celda-rubro" :title="rubro.rubro_nombre">{{ rubro.rubro_nombre }}</td>

                                <td v-for="mes in mesesAnio" :key="`${rubro.rubro_id}-${mes.valor}`" class="celda-monto">
                                    <MontoMonedaColoreado
                                        :monto="montoConvertido(rubro.valores[mes.valor] || 0)"
                                        :moneda="simboloMoneda"
                                    />
                                </td>
                            </tr>

                            <tr class="fila-total-grupo">
                                <td class="celda-padre-vacia"></td>
                                <td class="celda-rubro-total">Total {{ grupo.padre }}</td>

                                <td v-for="mes in mesesAnio" :key="`tot-${grupo.padre}-${mes.valor}`" class="celda-monto font-bold">
                                    <MontoMonedaColoreado
                                        :monto="montoConvertido(grupo.totalesPorMes[mes.valor] || 0)"
                                        :moneda="simboloMoneda"
                                    />
                                </td>
                            </tr>
                        </template>
                    </tbody>

                    <tfoot>
                        <tr class="fila-resumen fila-ingresos">
                            <td :colspan="2">TOTAL INGRESOS</td>
                            <td v-for="mes in mesesAnio" :key="`sum-ing-${mes.valor}`" class="celda-monto">
                                <MontoMonedaColoreado :monto="montoConvertido(resumenMensual[mes.valor]?.ingresos || 0)" :moneda="simboloMoneda" />
                            </td>
                        </tr>

                        <tr class="fila-resumen fila-egresos">
                            <td :colspan="2">TOTAL GASTOS / EGRESOS</td>
                            <td v-for="mes in mesesAnio" :key="`sum-egr-${mes.valor}`" class="celda-monto">
                                <MontoMonedaColoreado :monto="montoConvertido(resumenMensual[mes.valor]?.egresos || 0)" :moneda="simboloMoneda" />
                            </td>
                        </tr>

                        <tr class="fila-resumen fila-neto">
                            <td :colspan="2">GANANCIA / PERDIDA</td>
                            <td v-for="mes in mesesAnio" :key="`sum-net-${mes.valor}`" class="celda-monto font-black">
                                <span :class="Number(resumenMensual[mes.valor]?.neto || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'">
                                    <MontoMonedaColoreado :monto="montoConvertido(resumenMensual[mes.valor]?.neto || 0)" :moneda="simboloMoneda" />
                                </span>
                            </td>
                        </tr>

                        <tr class="fila-resumen fila-total-anual-final">
                            <td :colspan="mesesAnio.length + 1">TOTAL ANUAL ACUMULADO (GANANCIA / PERDIDA)</td>
                            <td class="celda-monto font-black">
                                <span :class="Number(resumenAnual.totalNeto || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'">
                                    <MontoMonedaColoreado :monto="montoConvertido(resumenAnual.totalNeto || 0)" :moneda="simboloMoneda" />
                                </span>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <div v-if="!cargando && !gruposRubrosAnuales.length" class="card rounded-xl p-10 text-center border border-dashed border-slate-300 bg-slate-50">
            <i class="pi pi-folder-open text-4xl text-slate-300 mb-4"></i>
            <h3 class="text-lg font-bold text-slate-700 mb-1">Sin informacion anual</h3>
            <p class="text-slate-500 text-sm">No se encontraron movimientos para el año y casino seleccionados.</p>
        </div>
    </section>
</template>

<style scoped>
.estado-anual {
    font-family: var(--font-family, system-ui, sans-serif);
}

.contenedor-tabla-anual {
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-gutter: stable both-edges;
    padding-bottom: 0.35rem;
}

.contenedor-tabla-anual::-webkit-scrollbar {
    height: 10px;
}

.contenedor-tabla-anual::-webkit-scrollbar-thumb {
    background: #94a3b8;
    border-radius: 999px;
}

.contenedor-tabla-anual::-webkit-scrollbar-track {
    background: #e2e8f0;
    border-radius: 999px;
}

.tabla-excel-anual {
    border-collapse: collapse;
    background: #ffffff;
    table-layout: fixed;
}

.tabla-excel-anual th,
.tabla-excel-anual td {
    border: 1px solid #cbd5e1;
    padding: 0.3rem 0.35rem;
    font-size: 11px;
    white-space: nowrap;
}

.tabla-excel-anual thead th {
    background: #f8fafc;
    color: #d97706;
    font-weight: 800;
    text-transform: uppercase;
    text-align: center;
}

.columna-padre {
    width: 104px;
    min-width: 104px;
    color: #1e3a8a !important;
}

.columna-rubro {
    width: 190px;
    min-width: 190px;
    color: #1e3a8a !important;
    text-align: left !important;
}

.columna-mes {
    width: 66px;
    min-width: 66px;
}

.fila-padre td {
    background: #cfe0f4;
    color: #1e40af;
    font-style: italic;
}

.celda-padre-vacia {
    background: #f8fafc;
}

.celda-rubro {
    text-align: left;
    font-weight: 600;
    color: #0f172a;
    max-width: 190px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.celda-rubro-total {
    text-align: left;
    font-weight: 800;
    color: #1e3a8a;
    max-width: 190px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.celda-monto {
    text-align: right;
    overflow: hidden;
}

.celda-monto :deep(span.inline-flex) {
    font-size: 10.5px;
    line-height: 1.05;
}

.fila-rubro:hover {
    background: #f8fafc;
}

.fila-total-grupo td {
    background: #e5edf8;
}

.fila-resumen td {
    font-weight: 800;
    border-top: 2px solid #2563eb;
}

.fila-ingresos td {
    background: #eefbf4;
}

.fila-egresos td {
    background: #fff1f2;
}

.fila-neto td {
    background: #e9f0fc;
    border-top: 3px solid #1d4ed8;
}

.fila-total-anual-final td {
    background: #dbeafe;
    border-top: 3px solid #1e40af;
}

.fila-total-anual-final td:first-child {
    text-align: right;
    color: #1e3a8a;
}

.tag-impacta {
    background: #dcfce7;
    border: 1px solid #86efac;
    color: #166534;
}

.tag-informativo {
    background: #fef3c7;
    border: 1px solid #fcd34d;
    color: #92400e;
}

@media (max-width: 1366px) {
    .tabla-excel-anual th,
    .tabla-excel-anual td {
        padding: 0.25rem 0.3rem;
        font-size: 10px;
    }

    .columna-padre {
        width: 96px;
        min-width: 96px;
    }

    .columna-rubro {
        width: 168px;
        min-width: 168px;
    }

    .columna-mes {
        width: 60px;
        min-width: 60px;
    }

    .celda-rubro,
    .celda-rubro-total {
        max-width: 168px;
    }

    .celda-monto :deep(span.inline-flex) {
        font-size: 9.6px;
    }

    .tabla-excel-anual {
        min-width: 980px;
    }
}

@media (max-width: 1024px) {
    .tabla-excel-anual th,
    .tabla-excel-anual td {
        padding: 0.22rem 0.26rem;
        font-size: 9px;
    }

    .columna-padre {
        width: 88px;
        min-width: 88px;
    }

    .columna-rubro {
        width: 150px;
        min-width: 150px;
    }

    .columna-mes {
        width: 56px;
        min-width: 56px;
    }

    .celda-rubro,
    .celda-rubro-total {
        max-width: 150px;
    }

    .celda-monto :deep(span.inline-flex) {
        font-size: 9px;
    }

    .tabla-excel-anual {
        min-width: 900px;
    }
}

@media (max-width: 768px) {
    .tabla-excel-anual {
        min-width: 840px;
    }

    .fila-padre td {
        font-size: 9px;
    }

    .fila-total-anual-final td:first-child {
        font-size: 9px;
    }
}
</style>
