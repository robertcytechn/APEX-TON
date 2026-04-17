<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { obtenerEstadisticasOperativas } from '@/service/estadoResultadosServicio';
import { useSesionStore } from '@/stores/sesion';
import { crearNombreArchivoExportacion } from '@/utils/nombresExportacion';
import ComponenteGraficas from 'vue3-apexcharts';
import { computed, onMounted, reactive, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const datosEstadisticas = ref(null);
const mensajeError = ref('');
const mensajeExito = ref('');
const exportandoExcel = ref(false);
const exportandoPdf = ref(false);
const claveBloqueExportacion = ref('FLUJO');

const referenciaGraficaFlujo = ref(null);
const referenciaGraficaDistribucion = ref(null);
const referenciaGraficaCategorias = ref(null);
const referenciaGraficaConceptos = ref(null);
const referenciaGraficaSucursales = ref(null);
const referenciaGraficaSemanal = ref(null);

const detalleDrilldown = reactive({
    visible: false,
    titulo: '',
    subtitulo: '',
    filas: []
});

const periodoRapidoActivo = ref(30);
const vistaDetalleActiva = ref('CATEGORIAS');

const filtrosBusquedaTablas = reactive({
    categorias: '',
    rubros: '',
    conceptos: ''
});

const fechaHoy = new Date();
const fechaMaxima = new Date(fechaHoy.getFullYear(), fechaHoy.getMonth(), fechaHoy.getDate() - 1);
const fechaInicioPredeterminada = new Date(fechaHoy.getFullYear(), fechaHoy.getMonth(), fechaHoy.getDate() - 29);

const filtros = reactive({
    modoFecha: 'RANGO',
    fechaUnica: new Date(fechaMaxima),
    fechaInicio: new Date(fechaInicioPredeterminada),
    fechaFin: new Date(fechaMaxima),
    sucursalId: null,
    categoriaIds: [],
    tipoConcepto: 'TODOS'
});

const opcionesModoFecha = [
    { label: 'Rango de fechas', value: 'RANGO' },
    { label: 'Un solo dia', value: 'DIA' }
];

const periodosRapidos = [
    { label: '7 dias', dias: 7 },
    { label: '30 dias', dias: 30 },
    { label: '90 dias', dias: 90 },
    { label: '180 dias', dias: 180 }
];

const vistasDetalle = [
    { label: 'Categorias', value: 'CATEGORIAS' },
    { label: 'Rubros', value: 'RUBROS' },
    { label: 'Conceptos', value: 'CONCEPTOS' }
];

const puedeVerEstadisticas = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));

const catalogos = computed(() => datosEstadisticas.value?.catalogos || {});
const resumenGeneral = computed(() => datosEstadisticas.value?.resumen_general || {});
const comparativoAnterior = computed(() => datosEstadisticas.value?.comparativo_periodo_anterior || {});
const series = computed(() => datosEstadisticas.value?.series || {});
const filtrosAplicados = computed(() => datosEstadisticas.value?.filtros_aplicados || {});

const opcionesSucursales = computed(() => {
    const sucursales = Array.isArray(catalogos.value?.sucursales) ? catalogos.value.sucursales : [];
    return sucursales.map((sucursal) => ({
        label: `${sucursal.nombre} (${sucursal.clave})`,
        value: sucursal.id
    }));
});

const opcionesCategorias = computed(() => {
    const categorias = Array.isArray(catalogos.value?.categorias) ? catalogos.value.categorias : [];
    return categorias.map((categoria) => ({
        label: `${categoria.nombre} (${categoria.clave})`,
        value: categoria.id
    }));
});

const opcionesTipoConcepto = computed(() => {
    const tipos = Array.isArray(catalogos.value?.tipos_concepto) ? catalogos.value.tipos_concepto : [];
    if (!tipos.length) {
        return [
            { label: 'Todos', value: 'TODOS' },
            { label: 'Ingresos', value: 'INGRESO' },
            { label: 'Egresos', value: 'EGRESO' }
        ];
    }
    return tipos;
});

const totalMovimientos = computed(() => Number(resumenGeneral.value?.total_movimientos || 0));
const totalIngresos = computed(() => Number(resumenGeneral.value?.total_ingresos || 0));
const totalEgresos = computed(() => Number(resumenGeneral.value?.total_egresos || 0));
const resultadoNeto = computed(() => Number(resumenGeneral.value?.resultado_neto || 0));
const montoPromedioPorMovimiento = computed(() => Number(resumenGeneral.value?.ticket_promedio || 0));
const promedioDiarioNeto = computed(() => Number(resumenGeneral.value?.promedio_diario_neto || 0));
const totalMontosOperacion = computed(() => totalIngresos.value + totalEgresos.value);
const hayInformacionExportable = computed(() => Boolean(datosEstadisticas.value) && totalMovimientos.value > 0);

const movimientosIngreso = computed(() => {
    const distribucion = Array.isArray(resumenGeneral.value?.distribucion_tipo)
        ? resumenGeneral.value.distribucion_tipo
        : [];
    const itemIngreso = distribucion.find((item) => String(item?.tipo || '').toUpperCase() === 'INGRESO');
    return Number(itemIngreso?.movimientos || 0);
});

const movimientosEgreso = computed(() => {
    const distribucion = Array.isArray(resumenGeneral.value?.distribucion_tipo)
        ? resumenGeneral.value.distribucion_tipo
        : [];
    const itemEgreso = distribucion.find((item) => String(item?.tipo || '').toUpperCase() === 'EGRESO');
    return Number(itemEgreso?.movimientos || 0);
});

const montoPromedioMovimientoIngreso = computed(() => {
    if (movimientosIngreso.value <= 0) {
        return 0;
    }
    return totalIngresos.value / movimientosIngreso.value;
});

const montoPromedioMovimientoEgreso = computed(() => {
    if (movimientosEgreso.value <= 0) {
        return 0;
    }
    return totalEgresos.value / movimientosEgreso.value;
});

const diasPeriodo = computed(() => Number(filtrosAplicados.value?.dias_periodo || 0));
const diasConMovimientos = computed(() => Number(filtrosAplicados.value?.dias_con_movimientos || 0));

const margenNetoPorcentaje = computed(() => {
    if (totalIngresos.value <= 0) {
        return 0;
    }
    return (resultadoNeto.value / totalIngresos.value) * 100;
});

const razonIngresosEgresos = computed(() => {
    if (totalEgresos.value <= 0) {
        return null;
    }
    return totalIngresos.value / totalEgresos.value;
});

const promedioMovimientosDia = computed(() => {
    if (!diasPeriodo.value) {
        return 0;
    }
    return totalMovimientos.value / diasPeriodo.value;
});

const intensidadOperativa = computed(() => {
    if (!diasPeriodo.value) {
        return 0;
    }
    return (diasConMovimientos.value / diasPeriodo.value) * 100;
});

const seriePorDia = computed(() => (Array.isArray(series.value?.por_dia) ? series.value.por_dia : []));
const seriePorCategoria = computed(() => (Array.isArray(series.value?.por_categoria) ? series.value.por_categoria : []));
const seriePorRubro = computed(() => (Array.isArray(series.value?.por_rubro) ? series.value.por_rubro : []));
const seriePorSucursal = computed(() => (Array.isArray(series.value?.por_sucursal) ? series.value.por_sucursal : []));
const topConceptos = computed(() => (Array.isArray(series.value?.top_conceptos) ? series.value.top_conceptos : []));

const tablaCategorias = computed(() => {
    return [...seriePorCategoria.value]
        .map((item) => {
            const ingresos = Number(item.ingresos || 0);
            const egresos = Number(item.egresos || 0);
            const movimientos = Number(item.movimientos || 0);
            return {
                ...item,
                ingresos,
                egresos,
                neto: Number(item.neto || 0),
                movimientos,
                promedio_monto: movimientos > 0 ? (ingresos + egresos) / movimientos : 0
            };
        })
        .sort((a, b) => Math.abs(Number(b.neto || 0)) - Math.abs(Number(a.neto || 0)));
});

const tablaRubros = computed(() => {
    return [...seriePorRubro.value]
        .map((item) => {
            const ingresos = Number(item.ingresos || 0);
            const egresos = Number(item.egresos || 0);
            const movimientos = Number(item.movimientos || 0);
            return {
                ...item,
                ingresos,
                egresos,
                neto: Number(item.neto || 0),
                movimientos,
                promedio_monto: movimientos > 0 ? (ingresos + egresos) / movimientos : 0
            };
        })
        .sort((a, b) => Math.abs(Number(b.neto || 0)) - Math.abs(Number(a.neto || 0)));
});

const tablaConceptos = computed(() => {
    return [...topConceptos.value]
        .map((item) => {
            const montoTotal = Number(item.monto_total || 0);
            const movimientos = Number(item.movimientos || 0);
            return {
                ...item,
                monto_total: montoTotal,
                movimientos,
                monto_promedio: movimientos > 0 ? montoTotal / movimientos : 0
            };
        })
        .sort((a, b) => Number(b.monto_total || 0) - Number(a.monto_total || 0));
});

const categoriaMayorImpacto = computed(() => tablaCategorias.value[0] || null);
const rubroMayorImpacto = computed(() => tablaRubros.value[0] || null);
const conceptoPrincipal = computed(() => tablaConceptos.value[0] || null);

const mejorDia = computed(() => resumenGeneral.value?.mejor_dia || null);
const peorDia = computed(() => resumenGeneral.value?.peor_dia || null);

const sinResultados = computed(() => totalMovimientos.value === 0 && !cargando.value);

const etiquetasFiltrosActivos = computed(() => {
    const etiquetas = [];

    if (filtros.modoFecha === 'DIA') {
        etiquetas.push(`Fecha: ${formatearFecha(filtrosAplicados.value.fecha || fechaAFormatoIso(filtros.fechaUnica))}`);
    } else {
        etiquetas.push(`Rango: ${formatearFecha(filtrosAplicados.value.fecha_inicio || fechaAFormatoIso(filtros.fechaInicio))} a ${formatearFecha(filtrosAplicados.value.fecha_fin || fechaAFormatoIso(filtros.fechaFin))}`);
    }

    if (filtrosAplicados.value.sucursal_id) {
        const sucursal = opcionesSucursales.value.find((item) => Number(item.value) === Number(filtrosAplicados.value.sucursal_id));
        etiquetas.push(`Casino: ${sucursal?.label || filtrosAplicados.value.sucursal_id}`);
    } else {
        etiquetas.push('Casino: Todos');
    }

    if (Array.isArray(filtrosAplicados.value.categoria_ids) && filtrosAplicados.value.categoria_ids.length) {
        etiquetas.push(`Categorias filtradas: ${filtrosAplicados.value.categoria_ids.length}`);
    } else {
        etiquetas.push('Categorias: Todas');
    }

    etiquetas.push(`Tipo: ${filtrosAplicados.value.tipo_concepto || 'TODOS'}`);
    etiquetas.push(`Dias del periodo: ${diasPeriodo.value}`);
    etiquetas.push(`Dias con movimientos: ${diasConMovimientos.value}`);

    return etiquetas;
});

const insightsClave = computed(() => {
    const insights = [];

    if (categoriaMayorImpacto.value) {
        insights.push(`Mayor impacto por categoria: ${categoriaMayorImpacto.value.categoria_nombre} (${categoriaMayorImpacto.value.categoria_clave || 'SIN CLAVE'}).`);
    }

    if (rubroMayorImpacto.value) {
        insights.push(`Rubro dominante del periodo: ${rubroMayorImpacto.value.rubro_nombre_con_padre || rubroMayorImpacto.value.rubro_nombre}.`);
    }

    if (conceptoPrincipal.value) {
        insights.push(`Concepto principal por monto: ${conceptoPrincipal.value.concepto_nombre}.`);
    }

    if (mejorDia.value?.fecha) {
        insights.push(`Mejor dia de flujo neto: ${formatearFecha(mejorDia.value.fecha)}.`);
    }

    if (peorDia.value?.fecha) {
        insights.push(`Dia de mayor presion operativa: ${formatearFecha(peorDia.value.fecha)}.`);
    }

    if (!insights.length) {
        insights.push('Sin información suficiente para generar insights del periodo actual.');
    }

    return insights;
});

const tablaCategoriasFiltrada = computed(() => {
    return filtrarColeccionPorTexto(tablaCategorias.value, filtrosBusquedaTablas.categorias, [
        'categoria_clave',
        'categoria_nombre'
    ]);
});

const tablaRubrosFiltrada = computed(() => {
    return filtrarColeccionPorTexto(tablaRubros.value, filtrosBusquedaTablas.rubros, [
        'rubro_nombre',
        'rubro_padre_nombre',
        'rubro_nombre_con_padre'
    ]);
});

const tablaConceptosFiltrada = computed(() => {
    return filtrarColeccionPorTexto(tablaConceptos.value, filtrosBusquedaTablas.conceptos, [
        'concepto_nombre',
        'categoria_nombre',
        'categoria_clave',
        'concepto_tipo'
    ]);
});

const seriesFlujoDiario = computed(() => [
    {
        name: 'Ingresos',
        type: 'area',
        data: seriePorDia.value.map((item) => Number(item.ingresos || 0))
    },
    {
        name: 'Egresos',
        type: 'area',
        data: seriePorDia.value.map((item) => Number(item.egresos || 0))
    },
    {
        name: 'Neto',
        type: 'line',
        data: seriePorDia.value.map((item) => Number(item.neto || 0))
    }
]);

const opcionesFlujoDiario = computed(() => ({
    chart: {
        type: 'line',
        events: {
            dataPointSelection: (_evento, _contexto, configuracion) => {
                abrirDrilldownDesdeDia(configuracion?.dataPointIndex);
            }
        },
        toolbar: {
            show: true,
            tools: {
                download: true,
                selection: true,
                zoom: true,
                zoomin: true,
                zoomout: true,
                pan: true,
                reset: true
            }
        },
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif',
        animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 500
        }
    },
    colors: ['#14b8a6', '#f97316', '#0f172a'],
    stroke: {
        width: [3, 3, 3],
        curve: 'smooth'
    },
    fill: {
        type: ['gradient', 'gradient', 'solid'],
        gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.3,
            opacityTo: 0.05,
            stops: [0, 100]
        }
    },
    dataLabels: {
        enabled: false
    },
    markers: {
        size: 0,
        hover: {
            sizeOffset: 4
        }
    },
    xaxis: {
        categories: seriePorDia.value.map((item) => formatearFechaCorta(item.fecha)),
        labels: {
            rotate: -45,
            trim: true
        }
    },
    yaxis: {
        labels: {
            formatter: (valor) => formatearMonedaCompacta(valor)
        }
    },
    tooltip: {
        shared: true,
        intersect: false,
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    },
    legend: {
        position: 'top'
    },
    grid: {
        borderColor: '#e2e8f0'
    }
}));

const distribucionTipo = computed(() => (Array.isArray(resumenGeneral.value?.distribucion_tipo) ? resumenGeneral.value.distribucion_tipo : []));

const seriesDistribucionTipo = computed(() => distribucionTipo.value.map((item) => Number(item.monto || 0)));

const opcionesDistribucionTipo = computed(() => ({
    chart: {
        type: 'donut',
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif'
    },
    labels: distribucionTipo.value.map((item) => String(item.tipo || 'SIN TIPO')),
    colors: ['#0ea5e9', '#f97316'],
    legend: {
        position: 'bottom'
    },
    dataLabels: {
        enabled: true,
        formatter: (valor) => `${Number(valor || 0).toFixed(1)}%`
    },
    plotOptions: {
        pie: {
            donut: {
                size: '62%',
                labels: {
                    show: true,
                    total: {
                        show: true,
                        label: 'Total operado',
                        formatter: () => formatearMoneda(totalMontosOperacion.value)
                    }
                }
            }
        }
    },
    tooltip: {
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    }
}));

const categoriasTopImpacto = computed(() => {
    return [...tablaCategorias.value].slice(0, 10);
});

const seriesCategoriasImpacto = computed(() => [
    {
        name: 'Ingresos',
        type: 'column',
        data: categoriasTopImpacto.value.map((item) => Number(item.ingresos || 0))
    },
    {
        name: 'Egresos',
        type: 'column',
        data: categoriasTopImpacto.value.map((item) => Number(item.egresos || 0))
    },
    {
        name: 'Neto',
        type: 'line',
        data: categoriasTopImpacto.value.map((item) => Number(item.neto || 0))
    }
]);

const opcionesCategoriasImpacto = computed(() => ({
    chart: {
        type: 'line',
        events: {
            dataPointSelection: (_evento, _contexto, configuracion) => {
                abrirDrilldownDesdeCategoria(configuracion?.dataPointIndex);
            }
        },
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif',
        toolbar: { show: true }
    },
    colors: ['#14b8a6', '#fb7185', '#1e293b'],
    stroke: {
        width: [0, 0, 3],
        curve: 'smooth'
    },
    plotOptions: {
        bar: {
            columnWidth: '58%',
            borderRadius: 4
        }
    },
    dataLabels: {
        enabled: false
    },
    xaxis: {
        categories: categoriasTopImpacto.value.map((item) => item.categoria_clave || item.categoria_nombre || 'SIN CATEGORIA')
    },
    yaxis: {
        labels: {
            formatter: (valor) => formatearMonedaCompacta(valor)
        }
    },
    legend: {
        position: 'top'
    },
    tooltip: {
        shared: true,
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    },
    grid: {
        borderColor: '#e2e8f0'
    }
}));

const conceptosTreemap = computed(() => {
    const principales = [...tablaConceptos.value]
        .filter((item) => Number(item.monto_total || 0) > 0)
        .slice(0, 12)
        .map((item) => ({
            ...item,
            es_fallback_categoria: false,
            valor_treemap: Number(item.monto_total || 0)
        }));

    if (principales.length) {
        return principales;
    }

    return [...tablaCategorias.value]
        .filter((item) => Math.abs(Number(item.neto || 0)) > 0)
        .slice(0, 12)
        .map((item) => ({
            concepto_nombre: item.categoria_nombre,
            categoria_nombre: item.categoria_nombre,
            categoria_clave: item.categoria_clave,
            concepto_tipo: 'MIXTO',
            movimientos: Number(item.movimientos || 0),
            monto_total: Math.abs(Number(item.neto || 0)),
            monto_promedio: Number(item.promedio_monto || 0),
            es_fallback_categoria: true,
            valor_treemap: Math.abs(Number(item.neto || 0))
        }));
});

const seriesTopConceptosTreemap = computed(() => [
    {
        data: conceptosTreemap.value.map((item) => ({
            x: item.concepto_nombre,
            y: Number(item.valor_treemap || item.monto_total || 0)
        }))
    }
]);

const opcionesTopConceptosTreemap = computed(() => ({
    chart: {
        type: 'treemap',
        events: {
            dataPointSelection: (_evento, _contexto, configuracion) => {
                abrirDrilldownDesdeConceptoTreemap(configuracion?.dataPointIndex);
            }
        },
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif',
        toolbar: { show: false }
    },
    colors: ['#0f766e', '#1d4ed8', '#ea580c', '#9333ea', '#0ea5e9', '#65a30d'],
    legend: {
        show: false
    },
    dataLabels: {
        enabled: true,
        style: {
            fontSize: '12px',
            fontWeight: 600
        },
        formatter: (texto, opciones) => {
            const valor = opciones?.value;
            return `${texto} ${formatearMonedaCompacta(valor)}`;
        }
    },
    noData: {
        text: 'Sin datos de conceptos para el periodo seleccionado.',
        align: 'center',
        verticalAlign: 'middle'
    },
    tooltip: {
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    },
    plotOptions: {
        treemap: {
            distributed: true,
            enableShades: true,
            shadeIntensity: 0.45
        }
    }
}));

const sucursalesOrdenadas = computed(() => {
    return [...seriePorSucursal.value].sort((a, b) => Math.abs(Number(b.neto || 0)) - Math.abs(Number(a.neto || 0)));
});

const seriesSucursales = computed(() => [
    {
        name: 'Ingresos',
        type: 'column',
        data: sucursalesOrdenadas.value.map((item) => Number(item.ingresos || 0))
    },
    {
        name: 'Egresos',
        type: 'column',
        data: sucursalesOrdenadas.value.map((item) => Number(item.egresos || 0))
    },
    {
        name: 'Neto',
        type: 'line',
        data: sucursalesOrdenadas.value.map((item) => Number(item.neto || 0))
    }
]);

const opcionesGraficaSucursales = computed(() => ({
    chart: {
        type: 'line',
        events: {
            dataPointSelection: (_evento, _contexto, configuracion) => {
                abrirDrilldownDesdeSucursal(configuracion?.dataPointIndex);
            }
        },
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif',
        toolbar: { show: true }
    },
    colors: ['#22c55e', '#ef4444', '#0f172a'],
    stroke: {
        width: [0, 0, 3],
        curve: 'smooth'
    },
    plotOptions: {
        bar: {
            columnWidth: '50%',
            borderRadius: 4
        }
    },
    dataLabels: {
        enabled: false
    },
    xaxis: {
        categories: sucursalesOrdenadas.value.map((item) => item.sucursal_nombre || 'SIN SUCURSAL')
    },
    yaxis: {
        labels: {
            formatter: (valor) => formatearMonedaCompacta(valor)
        }
    },
    tooltip: {
        shared: true,
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    },
    legend: {
        position: 'top'
    },
    grid: {
        borderColor: '#e2e8f0'
    }
}));

const diasSemanaOrden = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'];

const resumenSemanal = computed(() => {
    const acumulados = {
        Lun: { neto: 0, movimientos: 0 },
        Mar: { neto: 0, movimientos: 0 },
        Mie: { neto: 0, movimientos: 0 },
        Jue: { neto: 0, movimientos: 0 },
        Vie: { neto: 0, movimientos: 0 },
        Sab: { neto: 0, movimientos: 0 },
        Dom: { neto: 0, movimientos: 0 }
    };

    for (const item of seriePorDia.value) {
        const fecha = fechaIsoAFecha(item.fecha);
        if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) {
            continue;
        }

        const indice = fecha.getDay();
        const mapaDia = { 1: 'Lun', 2: 'Mar', 3: 'Mie', 4: 'Jue', 5: 'Vie', 6: 'Sab', 0: 'Dom' };
        const claveDia = mapaDia[indice];
        if (!claveDia) {
            continue;
        }

        acumulados[claveDia].neto += Number(item.neto || 0);
        acumulados[claveDia].movimientos += Number(item.movimientos || 0);
    }

    return diasSemanaOrden.map((dia) => ({
        dia,
        neto: acumulados[dia].neto,
        movimientos: acumulados[dia].movimientos
    }));
});

const seriesPulsoSemanal = computed(() => [
    {
        name: 'Neto acumulado',
        data: resumenSemanal.value.map((item) => ({
            x: item.dia,
            y: Number(item.neto || 0)
        }))
    }
]);

const opcionesPulsoSemanal = computed(() => ({
    chart: {
        type: 'heatmap',
        foreColor: '#334155',
        fontFamily: 'Segoe UI, sans-serif',
        toolbar: { show: false }
    },
    dataLabels: {
        enabled: true,
        formatter: (valor) => formatearMonedaCompacta(valor)
    },
    stroke: {
        width: 1,
        colors: ['#ffffff']
    },
    plotOptions: {
        heatmap: {
            shadeIntensity: 0.55,
            colorScale: {
                ranges: [
                    { from: -999999999, to: -1, color: '#dc2626', name: 'Neto negativo' },
                    { from: 0, to: 0, color: '#94a3b8', name: 'Neto neutro' },
                    { from: 1, to: 999999999, color: '#16a34a', name: 'Neto positivo' }
                ]
            }
        }
    },
    tooltip: {
        y: {
            formatter: (valor) => formatearMoneda(valor)
        }
    },
    xaxis: {
        labels: {
            style: {
                fontWeight: 600
            }
        }
    }
}));

// 1) Para qué sirve: convertir Date a YYYY-MM-DD para filtros del backend.
// 2) Cómo funciona: extrae año, mes y día con relleno de dos dígitos.
// 3) Qué hace: normaliza el contrato de fechas para consultas analíticas.
// 4) Cómo editarla: ajusta formato si backend cambia el estándar de fecha.
function fechaAFormatoIso(fecha) {
    if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) {
        return '';
    }
    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

// 1) Para qué sirve: crear Date segura desde string ISO evitando timezone shifts.
// 2) Cómo funciona: agrega hora fija local y valida fecha resultante.
// 3) Qué hace: estabiliza conversiones para etiquetas y comparativos por día.
// 4) Cómo editarla: cambia hora fija si se define otra convención operativa.
function fechaIsoAFecha(valorIso) {
    if (!valorIso) {
        return null;
    }
    const fecha = new Date(`${valorIso}T12:00:00`);
    if (Number.isNaN(fecha.getTime())) {
        return null;
    }
    return fecha;
}

// 1) Para qué sirve: formatear fecha en representación legible para usuarios.
// 2) Cómo funciona: parsea ISO y aplica locale es-MX con formato completo.
// 3) Qué hace: mejora lectura de periodos en tarjetas y encabezados.
// 4) Cómo editarla: cambia estilo de salida según lineamiento de UX.
function formatearFecha(fechaIso) {
    const fecha = fechaIsoAFecha(fechaIso);
    if (!fecha) {
        return 'N/A';
    }
    return fecha.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// 1) Para qué sirve: formatear fecha corta para ejes de gráficas.
// 2) Cómo funciona: renderiza solo día y mes para reducir saturación visual.
// 3) Qué hace: mantiene legibilidad en series con periodos largos.
// 4) Cómo editarla: habilita año cuando se consulten rangos anuales amplios.
function formatearFechaCorta(fechaIso) {
    const fecha = fechaIsoAFecha(fechaIso);
    if (!fecha) {
        return 'N/A';
    }
    return fecha.toLocaleDateString('es-MX', {
        month: '2-digit',
        day: '2-digit'
    });
}

// 1) Para qué sirve: mostrar montos en moneda MXN con formato consistente.
// 2) Cómo funciona: usa Intl.NumberFormat con separadores mexicanos.
// 3) Qué hace: estandariza tooltips y etiquetas numéricas en gráficos.
// 4) Cómo editarla: ajusta moneda si se agrega soporte multimoneda.
function formatearMoneda(valor) {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number.isFinite(numero) ? numero : 0);
}

// 1) Para qué sirve: abreviar montos grandes en ejes de visualización.
// 2) Cómo funciona: activa notation compact manteniendo estilo monetario.
// 3) Qué hace: evita saturación de texto en gráficas densas.
// 4) Cómo editarla: incrementa precisión si se necesita mayor detalle.
function formatearMonedaCompacta(valor) {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'MXN',
        notation: 'compact',
        minimumFractionDigits: 0,
        maximumFractionDigits: 1
    }).format(Number.isFinite(numero) ? numero : 0);
}

// 1) Para qué sirve: formatear números enteros y decimales para KPIs no monetarios.
// 2) Cómo funciona: aplica locale es-MX y define número de decimales.
// 3) Qué hace: entrega consistencia visual en todo el tablero.
// 4) Cómo editarla: cambia precisión por métrica cuando negocio lo pida.
function formatearNumero(valor, decimales = 0) {
    const numero = Number(valor || 0);
    return new Intl.NumberFormat('es-MX', {
        minimumFractionDigits: decimales,
        maximumFractionDigits: decimales
    }).format(Number.isFinite(numero) ? numero : 0);
}

// 1) Para qué sirve: convertir variaciones porcentuales en texto legible.
// 2) Cómo funciona: maneja casos sin base y agrega signo positivo/negativo.
// 3) Qué hace: clarifica cambios frente al periodo comparativo previo.
// 4) Cómo editarla: ajusta etiquetas si se requiere visión más conservadora.
function formatearVariacion(valor) {
    if (valor === null || valor === undefined) {
        return 'Sin base';
    }
    const numero = Number(valor);
    if (!Number.isFinite(numero)) {
        return 'N/A';
    }
    const signo = numero > 0 ? '+' : '';
    return `${signo}${numero.toFixed(2)}%`;
}

// 1) Para qué sirve: aplicar color semántico a variaciones porcentuales.
// 2) Cómo funciona: evalúa signo del porcentaje y clasifica estilo textual.
// 3) Qué hace: acelera interpretación ejecutiva de mejoras o deterioros.
// 4) Cómo editarla: adapta paleta según guía visual institucional.
function claseVariacion(valor) {
    if (valor === null || valor === undefined) {
        return 'text-slate-500';
    }
    const numero = Number(valor);
    if (!Number.isFinite(numero)) {
        return 'text-slate-500';
    }
    if (numero > 0) return 'text-emerald-700';
    if (numero < 0) return 'text-red-700';
    return 'text-slate-700';
}

// 1) Para qué sirve: definir severidad visual del resultado neto consolidado.
// 2) Cómo funciona: asigna estado por signo del neto (positivo, neutro o negativo).
// 3) Qué hace: refuerza lectura rápida en tarjetas de resumen.
// 4) Cómo editarla: ajusta umbrales si se incorpora zona de tolerancia.
function severidadResultadoNeto() {
    if (resultadoNeto.value > 0) return 'success';
    if (resultadoNeto.value < 0) return 'danger';
    return 'warn';
}

// 1) Para qué sirve: normalizar texto para filtros de búsqueda de tablas.
// 2) Cómo funciona: remueve acentos y transforma a minúsculas.
// 3) Qué hace: permite búsquedas flexibles con variaciones de escritura.
// 4) Cómo editarla: añade nuevas reglas si aparecen caracteres especiales.
function normalizarTexto(valor) {
    return String(valor || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

// 1) Para qué sirve: filtrar una colección por texto libre en múltiples campos.
// 2) Cómo funciona: concatena campos indicados y compara con texto normalizado.
// 3) Qué hace: mejora exploración de datos en tablas ejecutivas.
// 4) Cómo editarla: agrega soporte por columnas numéricas si se requiere.
function filtrarColeccionPorTexto(coleccion, textoBusqueda, campos) {
    const texto = normalizarTexto(textoBusqueda);
    if (!texto) {
        return coleccion;
    }

    return coleccion.filter((elemento) => {
        const huella = campos
            .map((campo) => normalizarTexto(elemento?.[campo]))
            .join(' ');
        return huella.includes(texto);
    });
}

// 1) Para qué sirve: abrir modal de detalle analítico desde interacciones de gráficas.
// 2) Cómo funciona: recibe título/subtítulo y filas normalizadas para DataTable.
// 3) Qué hace: habilita drill-down de decisiones sobre puntos específicos.
// 4) Cómo editarla: agrega columnas extras si se requieren más dimensiones.
function abrirDrilldown(titulo, subtitulo, filas) {
    detalleDrilldown.titulo = titulo || 'Detalle';
    detalleDrilldown.subtitulo = subtitulo || '';
    detalleDrilldown.filas = Array.isArray(filas) ? filas : [];
    detalleDrilldown.visible = true;
}

// 1) Para qué sirve: cerrar modal de detalle analítico.
// 2) Cómo funciona: limpia estado reactivo y oculta el diálogo.
// 3) Qué hace: restablece navegación al tablero principal.
// 4) Cómo editarla: conserva estado previo si luego se requiere historial de drill-down.
function cerrarDrilldown() {
    detalleDrilldown.visible = false;
    detalleDrilldown.titulo = '';
    detalleDrilldown.subtitulo = '';
    detalleDrilldown.filas = [];
}

// 1) Para qué sirve: abrir detalle al seleccionar un punto de la serie diaria.
// 2) Cómo funciona: toma índice del punto y prepara resumen puntual del día.
// 3) Qué hace: permite explicar picos o caídas de flujo con un clic.
// 4) Cómo editarla: liga aquí futuras tablas de movimientos por día.
function abrirDrilldownDesdeDia(indice) {
    const posicion = Number(indice);
    if (!Number.isInteger(posicion) || posicion < 0 || posicion >= seriePorDia.value.length) {
        return;
    }

    const dia = seriePorDia.value[posicion];
    abrirDrilldown(
        `Detalle diario: ${formatearFecha(dia.fecha)}`,
        'Seleccionado desde la gráfica de flujo diario',
        [
            {
                etiqueta: 'Fecha',
                valor_texto: formatearFecha(dia.fecha),
                valor_monetario: null
            },
            {
                etiqueta: 'Ingresos',
                valor_texto: '',
                valor_monetario: Number(dia.ingresos || 0)
            },
            {
                etiqueta: 'Egresos',
                valor_texto: '',
                valor_monetario: Number(dia.egresos || 0)
            },
            {
                etiqueta: 'Neto',
                valor_texto: '',
                valor_monetario: Number(dia.neto || 0)
            },
            {
                etiqueta: 'Movimientos',
                valor_texto: formatearNumero(dia.movimientos || 0),
                valor_monetario: null
            }
        ]
    );
}

// 1) Para qué sirve: abrir detalle por categoría seleccionada en la gráfica.
// 2) Cómo funciona: filtra conceptos de la categoría y los ordena por monto.
// 3) Qué hace: permite navegar del agregado a lo operativo puntual.
// 4) Cómo editarla: agrega filtros por tipo de concepto si se requiere.
function abrirDrilldownDesdeCategoria(indice) {
    const posicion = Number(indice);
    if (!Number.isInteger(posicion) || posicion < 0 || posicion >= categoriasTopImpacto.value.length) {
        return;
    }

    const categoria = categoriasTopImpacto.value[posicion];
    const conceptosRelacionados = tablaConceptos.value
        .filter((item) => String(item.categoria_nombre || '') === String(categoria.categoria_nombre || ''))
        .slice(0, 30)
        .map((item) => ({
            etiqueta: item.concepto_nombre,
            valor_texto: `${item.concepto_tipo} | Movimientos: ${formatearNumero(item.movimientos || 0)}`,
            valor_monetario: Number(item.monto_total || 0)
        }));

    abrirDrilldown(
        `Drill-down categoría: ${categoria.categoria_nombre}`,
        `Clave ${categoria.categoria_clave || 'SIN CLAVE'} | ${formatearNumero(categoria.movimientos || 0)} movimientos`,
        conceptosRelacionados.length
            ? conceptosRelacionados
            : [
                {
                    etiqueta: 'Sin conceptos asociados',
                    valor_texto: 'No hay elementos para esta categoría con los filtros actuales.',
                    valor_monetario: null
                }
            ]
    );
}

// 1) Para qué sirve: abrir detalle desde selección de bloques del treemap.
// 2) Cómo funciona: usa índice del bloque para mostrar resumen del concepto/categoría.
// 3) Qué hace: convierte el mapa visual en navegación analítica concreta.
// 4) Cómo editarla: conecta aquí historial por concepto cuando exista endpoint dedicado.
function abrirDrilldownDesdeConceptoTreemap(indice) {
    const posicion = Number(indice);
    if (!Number.isInteger(posicion) || posicion < 0 || posicion >= conceptosTreemap.value.length) {
        return;
    }

    const concepto = conceptosTreemap.value[posicion];
    abrirDrilldown(
        `Drill-down concepto: ${concepto.concepto_nombre}`,
        concepto.es_fallback_categoria
            ? 'Vista de respaldo por categoría (no hubo conceptos con monto en el periodo).'
            : `Categoria: ${concepto.categoria_nombre || 'SIN CATEGORIA'}`,
        [
            {
                etiqueta: 'Categoria',
                valor_texto: `${concepto.categoria_nombre || 'SIN CATEGORIA'} (${concepto.categoria_clave || 'SIN CLAVE'})`,
                valor_monetario: null
            },
            {
                etiqueta: 'Tipo',
                valor_texto: concepto.concepto_tipo || 'MIXTO',
                valor_monetario: null
            },
            {
                etiqueta: 'Movimientos',
                valor_texto: formatearNumero(concepto.movimientos || 0),
                valor_monetario: null
            },
            {
                etiqueta: 'Monto total',
                valor_texto: '',
                valor_monetario: Number(concepto.monto_total || 0)
            },
            {
                etiqueta: 'Monto promedio',
                valor_texto: '',
                valor_monetario: Number(concepto.monto_promedio || 0)
            }
        ]
    );
}

// 1) Para qué sirve: abrir detalle cuando se selecciona una sucursal en gráfica.
// 2) Cómo funciona: toma índice y muestra resumen económico del casino elegido.
// 3) Qué hace: ayuda a comparar rápidamente desempeño por unidad operativa.
// 4) Cómo editarla: enlaza detalle por rubro/sucursal cuando haya endpoint específico.
function abrirDrilldownDesdeSucursal(indice) {
    const posicion = Number(indice);
    if (!Number.isInteger(posicion) || posicion < 0 || posicion >= sucursalesOrdenadas.value.length) {
        return;
    }

    const sucursal = sucursalesOrdenadas.value[posicion];
    abrirDrilldown(
        `Drill-down sucursal: ${sucursal.sucursal_nombre}`,
        'Seleccionado desde la gráfica de rendimiento por casino',
        [
            {
                etiqueta: 'Movimientos',
                valor_texto: formatearNumero(sucursal.movimientos || 0),
                valor_monetario: null
            },
            {
                etiqueta: 'Ingresos',
                valor_texto: '',
                valor_monetario: Number(sucursal.ingresos || 0)
            },
            {
                etiqueta: 'Egresos',
                valor_texto: '',
                valor_monetario: Number(sucursal.egresos || 0)
            },
            {
                etiqueta: 'Neto',
                valor_texto: '',
                valor_monetario: Number(sucursal.neto || 0)
            }
        ]
    );
}

// 1) Para qué sirve: construir catálogo centralizado de bloques exportables.
// 2) Cómo funciona: define metadatos, columnas, filas y referencia SVG por bloque.
// 3) Qué hace: habilita exportación completa o por bloque en Excel/PDF.
// 4) Cómo editarla: agrega nuevos bloques al dashboard sin duplicar lógica.
function construirCatalogoBloquesExportacion() {
    const base = [
        {
            clave: 'FLUJO',
            titulo: 'Flujo diario',
            referencia: referenciaGraficaFlujo,
            columnas: ['Fecha', 'Ingresos', 'Egresos', 'Neto', 'Movimientos'],
            filas: seriePorDia.value.map((item) => [
                formatearFecha(item.fecha),
                Number(item.ingresos || 0),
                Number(item.egresos || 0),
                Number(item.neto || 0),
                Number(item.movimientos || 0)
            ])
        },
        {
            clave: 'TIPO',
            titulo: 'Distribución por tipo',
            referencia: referenciaGraficaDistribucion,
            columnas: ['Tipo', 'Movimientos', 'Monto'],
            filas: distribucionTipo.value.map((item) => [
                item.tipo || 'SIN TIPO',
                Number(item.movimientos || 0),
                Number(item.monto || 0)
            ])
        },
        {
            clave: 'CATEGORIAS',
            titulo: 'Impacto por categoría',
            referencia: referenciaGraficaCategorias,
            columnas: ['Clave', 'Categoria', 'Movimientos', 'Ingresos', 'Egresos', 'Neto'],
            filas: tablaCategorias.value.map((item) => [
                item.categoria_clave || '',
                item.categoria_nombre || 'SIN CATEGORIA',
                Number(item.movimientos || 0),
                Number(item.ingresos || 0),
                Number(item.egresos || 0),
                Number(item.neto || 0)
            ])
        },
        {
            clave: 'CONCEPTOS',
            titulo: 'Mapa de conceptos principales',
            referencia: referenciaGraficaConceptos,
            columnas: ['Concepto', 'Categoria', 'Tipo', 'Movimientos', 'Monto total'],
            filas: conceptosTreemap.value.map((item) => [
                item.concepto_nombre || 'SIN CONCEPTO',
                item.categoria_nombre || 'SIN CATEGORIA',
                item.concepto_tipo || 'MIXTO',
                Number(item.movimientos || 0),
                Number(item.monto_total || 0)
            ])
        },
        {
            clave: 'SUCURSALES',
            titulo: 'Rendimiento por casino',
            referencia: referenciaGraficaSucursales,
            columnas: ['Sucursal', 'Movimientos', 'Ingresos', 'Egresos', 'Neto'],
            filas: sucursalesOrdenadas.value.map((item) => [
                item.sucursal_nombre || 'SIN SUCURSAL',
                Number(item.movimientos || 0),
                Number(item.ingresos || 0),
                Number(item.egresos || 0),
                Number(item.neto || 0)
            ])
        },
        {
            clave: 'PULSO',
            titulo: 'Pulso semanal',
            referencia: referenciaGraficaSemanal,
            columnas: ['Dia', 'Movimientos', 'Neto acumulado'],
            filas: resumenSemanal.value.map((item) => [
                item.dia,
                Number(item.movimientos || 0),
                Number(item.neto || 0)
            ])
        }
    ];

    return base.map((bloque) => ({
        ...bloque,
        totalFilas: Array.isArray(bloque.filas) ? bloque.filas.length : 0,
        tieneDatos: hayInformacionExportable.value && Array.isArray(bloque.filas) && bloque.filas.length > 0
    }));
}

const bloquesExportables = computed(() => construirCatalogoBloquesExportacion());

const opcionesBloquesExportables = computed(() => {
    return bloquesExportables.value.map((bloque) => ({
        label: `${bloque.titulo} (${formatearNumero(bloque.totalFilas || 0)})`,
        value: bloque.clave,
        disabled: !bloque.tieneDatos
    }));
});

const bloqueExportacionSeleccionado = computed(() => {
    return bloquesExportables.value.find((bloque) => bloque.clave === claveBloqueExportacion.value) || null;
});

const puedeExportarBloque = computed(() => {
    return Boolean(hayInformacionExportable.value && bloqueExportacionSeleccionado.value?.tieneDatos);
});

// 1) Para qué sirve: obtener secciones en orden vertical para exportación total.
// 2) Cómo funciona: transforma catálogo de bloques en payload de secciones.
// 3) Qué hace: reutiliza una sola fuente para Excel/PDF completo.
// 4) Cómo editarla: mantén el orden aquí si cambian prioridades directivas.
function construirSeccionesExportacionVertical() {
    return bloquesExportables.value.map((bloque) => ({
        titulo: bloque.titulo,
        columnas: bloque.columnas,
        filas: bloque.filas
    }));
}

// 1) Para qué sirve: generar hoja Excel con bloques de gráficas en disposición vertical.
// 2) Cómo funciona: inserta título, encabezados y filas por sección una debajo de otra.
// 3) Qué hace: facilita exportación legible y utilizable directamente en Excel.
// 4) Cómo editarla: ajusta espaciado/columnas según formato corporativo.
function construirHojaGraficasVertical(XLSX, secciones) {
    const filas = [];

    for (const seccion of secciones) {
        filas.push([seccion.titulo]);
        filas.push(seccion.columnas);
        if (Array.isArray(seccion.filas) && seccion.filas.length) {
            for (const fila of seccion.filas) {
                filas.push(fila);
            }
        } else {
            filas.push(['Sin datos para el periodo seleccionado.']);
        }
        filas.push([]);
    }

    return XLSX.utils.aoa_to_sheet(filas);
}

// 1) Para qué sirve: resolver nombre legible del casino aplicado al filtro actual.
// 2) Cómo funciona: busca la etiqueta en catálogo de sucursales por id filtrado.
// 3) Qué hace: unifica metadatos y nombres de archivo en exportaciones.
// 4) Cómo editarla: ajusta fallback si cambian reglas de sucursal global.
function obtenerCasinoExportacion() {
    const sucursalId = filtrosAplicados.value?.sucursal_id;
    if (!sucursalId) {
        return 'todos_los_casinos';
    }

    const sucursal = opcionesSucursales.value.find((item) => Number(item.value) === Number(sucursalId));
    return sucursal?.label || `sucursal_${sucursalId}`;
}

// 1) Para qué sirve: obtener rango de fechas aplicado para exportación de archivos.
// 2) Cómo funciona: prioriza fecha_inicio/fecha_fin y usa fecha única cuando aplique.
// 3) Qué hace: alimenta plantilla de nombres con periodo consistente.
// 4) Cómo editarla: amplía soporte si backend expone periodos adicionales.
function obtenerPeriodoExportacion() {
    const fechaUnica = String(filtrosAplicados.value?.fecha || '').trim();
    const fechaInicio = String(filtrosAplicados.value?.fecha_inicio || fechaUnica || '').trim();
    const fechaFin = String(filtrosAplicados.value?.fecha_fin || fechaUnica || fechaInicio || '').trim();
    return { fechaInicio, fechaFin };
}

// 1) Para qué sirve: exportar tablero en Excel con datasets y estructura vertical.
// 2) Cómo funciona: construye workbook con resumen y hojas analíticas.
// 3) Qué hace: entrega archivo abierto y funcional en Excel para dirección.
// 4) Cómo editarla: agrega nuevas hojas o fórmulas de negocio cuando se requiera.
async function exportarExcelEjecutivo() {
    if (!hayInformacionExportable.value) {
        mensajeError.value = 'No hay datos para exportar a Excel.';
        return;
    }

    exportandoExcel.value = true;
    mensajeExito.value = '';
    mensajeError.value = '';

    try {
        const XLSX = await import('xlsx');
        const libro = XLSX.utils.book_new();

        const hojaResumen = XLSX.utils.aoa_to_sheet([
            ['Tablero ejecutivo de estadisticas'],
            ['Fecha de exportacion', formatearFecha(fechaAFormatoIso(new Date()))],
            ['Periodo analizado', `${formatearFecha(filtrosAplicados.value.fecha_inicio)} al ${formatearFecha(filtrosAplicados.value.fecha_fin)}`],
            [],
            ['Indicador', 'Valor'],
            ['Ingresos totales', Number(totalIngresos.value || 0)],
            ['Egresos totales', Number(totalEgresos.value || 0)],
            ['Resultado neto', Number(resultadoNeto.value || 0)],
            ['Movimientos', Number(totalMovimientos.value || 0)],
            ['Monto promedio por movimiento (general)', Number(montoPromedioPorMovimiento.value || 0)],
            ['Monto promedio por movimiento (ingreso)', Number(montoPromedioMovimientoIngreso.value || 0)],
            ['Monto promedio por movimiento (egreso)', Number(montoPromedioMovimientoEgreso.value || 0)],
            ['Promedio diario neto', Number(promedioDiarioNeto.value || 0)],
            ['Margen neto (%)', Number(margenNetoPorcentaje.value || 0)],
            ['Intensidad operativa (%)', Number(intensidadOperativa.value || 0)]
        ]);

        const hojaCategorias = XLSX.utils.json_to_sheet(tablaCategorias.value);
        const hojaRubros = XLSX.utils.json_to_sheet(tablaRubros.value);
        const hojaConceptos = XLSX.utils.json_to_sheet(tablaConceptos.value);
        const hojaFlujo = XLSX.utils.json_to_sheet(seriePorDia.value);
        const hojaSucursales = XLSX.utils.json_to_sheet(sucursalesOrdenadas.value);

        const seccionesVerticales = construirSeccionesExportacionVertical();
        const hojaGraficasVertical = construirHojaGraficasVertical(XLSX, seccionesVerticales);

        XLSX.utils.book_append_sheet(libro, hojaResumen, 'Resumen');
        XLSX.utils.book_append_sheet(libro, hojaGraficasVertical, 'Graficas_Vertical');
        XLSX.utils.book_append_sheet(libro, hojaFlujo, 'Flujo_Diario');
        XLSX.utils.book_append_sheet(libro, hojaCategorias, 'Categorias');
        XLSX.utils.book_append_sheet(libro, hojaRubros, 'Rubros');
        XLSX.utils.book_append_sheet(libro, hojaConceptos, 'Conceptos');
        XLSX.utils.book_append_sheet(libro, hojaSucursales, 'Sucursales');

        const { fechaInicio, fechaFin } = obtenerPeriodoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estadisticas',
            tipo: 'tablero_ejecutivo',
            casino: obtenerCasinoExportacion(),
            fechaInicio,
            fechaFin,
            extension: 'xlsx'
        });
        XLSX.writeFile(libro, nombreArchivo);
        mensajeExito.value = 'Exportación Excel completada correctamente.';
    } catch (error) {
        mensajeError.value = error?.message || 'No se pudo exportar a Excel.';
    } finally {
        exportandoExcel.value = false;
    }
}

// 1) Para qué sirve: recuperar el SVG renderizado de cada gráfica.
// 2) Cómo funciona: localiza el nodo raíz del componente y busca etiqueta svg.
// 3) Qué hace: permite exportación PDF vectorial sin pérdida de calidad.
// 4) Cómo editarla: ajusta selector si cambia estructura del componente.
function obtenerSvgDesdeReferencia(referencia) {
    const instancia = referencia?.value;
    if (!instancia) {
        return null;
    }

    const raiz = instancia.$el || instancia;
    if (!raiz || typeof raiz.querySelector !== 'function') {
        return null;
    }

    return raiz.querySelector('svg');
}

// 1) Para qué sirve: convertir un elemento SVG en imagen PNG en memoria.
// 2) Cómo funciona: serializa el SVG, lo carga en Image y dibuja en canvas.
// 3) Qué hace: evita dependencia de svg2pdf para exportaciones PDF.
// 4) Cómo editarla: ajusta resolución de canvas si se requiere más nitidez.
async function convertirSvgElementoAPng(svg, anchoRenderPx, altoRenderPx) {
    const clon = svg.cloneNode(true);
    clon.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    if (anchoRenderPx) {
        clon.setAttribute('width', String(Math.max(1, Math.round(anchoRenderPx))));
    }
    if (altoRenderPx) {
        clon.setAttribute('height', String(Math.max(1, Math.round(altoRenderPx))));
    }

    const serializador = new XMLSerializer();
    const textoSvg = serializador.serializeToString(clon);
    const blob = new Blob([textoSvg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    try {
        const imagen = await new Promise((resolve, reject) => {
            const elemento = new Image();
            elemento.onload = () => resolve(elemento);
            elemento.onerror = () => reject(new Error('No se pudo convertir la gráfica SVG a imagen para PDF.'));
            elemento.src = url;
        });

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(anchoRenderPx || imagen.width || 1));
        canvas.height = Math.max(1, Math.round(altoRenderPx || imagen.height || 1));
        const contexto = canvas.getContext('2d');
        if (!contexto) {
            throw new Error('No se pudo inicializar el canvas para exportar PDF.');
        }

        contexto.fillStyle = '#ffffff';
        contexto.fillRect(0, 0, canvas.width, canvas.height);
        contexto.drawImage(imagen, 0, 0, canvas.width, canvas.height);

        return canvas.toDataURL('image/png');
    } finally {
        URL.revokeObjectURL(url);
    }
}

// 1) Para qué sirve: construir listado vertical de gráficas para exportación PDF.
// 2) Cómo funciona: define orden y referencia de cada visual del tablero.
// 3) Qué hace: garantiza PDF ordenado para lectura ejecutiva continua.
// 4) Cómo editarla: agrega o elimina gráficas según evolución del dashboard.
function obtenerBloquesPdfVerticales() {
    return bloquesExportables.value
        .filter((bloque) => bloque.tieneDatos)
        .map((bloque) => ({
            titulo: bloque.titulo,
            referencia: bloque.referencia
        }));
}

// 1) Para qué sirve: exportar PDF ejecutivo del tablero completo.
// 2) Cómo funciona: recorre gráficas, las convierte a PNG y las inserta en jsPDF.
// 3) Qué hace: evita errores de módulo en runtime al no usar svg2pdf.
// 4) Cómo editarla: incrementa resolución de render si se requiere más detalle.
async function exportarPdfVectorial() {
    if (!hayInformacionExportable.value) {
        mensajeError.value = 'No hay datos para exportar a PDF.';
        return;
    }

    exportandoPdf.value = true;
    mensajeExito.value = '';
    mensajeError.value = '';

    try {
        const { jsPDF } = await import('jspdf');

        const documento = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
        const anchoPagina = documento.internal.pageSize.getWidth();
        const altoPagina = documento.internal.pageSize.getHeight();
        const margen = 28;
        const anchoDisponible = anchoPagina - (margen * 2);

        let cursorY = margen;
        let graficasIncluidas = 0;

        documento.setFont('helvetica', 'bold');
        documento.setFontSize(13);
        documento.text('Reporte Ejecutivo de Estadisticas', margen, cursorY);
        cursorY += 18;
        documento.setFont('helvetica', 'normal');
        documento.setFontSize(10);
        documento.text(`Periodo: ${formatearFecha(filtrosAplicados.value.fecha_inicio)} al ${formatearFecha(filtrosAplicados.value.fecha_fin)}`, margen, cursorY);
        cursorY += 16;

        for (const bloque of obtenerBloquesPdfVerticales()) {
            const svg = obtenerSvgDesdeReferencia(bloque.referencia);
            if (!svg) {
                continue;
            }

            const anchoSvg = Number(svg?.viewBox?.baseVal?.width) || svg.getBoundingClientRect().width || 900;
            const altoSvg = Number(svg?.viewBox?.baseVal?.height) || svg.getBoundingClientRect().height || 320;
            const escala = anchoDisponible / anchoSvg;
            const altoRender = Math.max(150, altoSvg * escala);

            if (cursorY + altoRender + 36 > altoPagina - margen) {
                documento.addPage();
                cursorY = margen;
            }

            documento.setFont('helvetica', 'bold');
            documento.setFontSize(11);
            documento.text(bloque.titulo, margen, cursorY);

            const imagenGrafica = await convertirSvgElementoAPng(svg, anchoDisponible * 2, altoRender * 2);
            documento.addImage(imagenGrafica, 'PNG', margen, cursorY + 8, anchoDisponible, altoRender);

            graficasIncluidas += 1;
            cursorY += altoRender + 26;
        }

        if (!graficasIncluidas) {
            throw new Error('No se encontraron gráficas renderizadas para exportar en PDF.');
        }

        const { fechaInicio, fechaFin } = obtenerPeriodoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estadisticas',
            tipo: 'tablero_ejecutivo_pdf',
            casino: obtenerCasinoExportacion(),
            fechaInicio,
            fechaFin,
            extension: 'pdf'
        });
        documento.save(nombreArchivo);
        mensajeExito.value = 'Exportación PDF completada correctamente.';
    } catch (error) {
        mensajeError.value = error?.message || 'No se pudo exportar el PDF.';
    } finally {
        exportandoPdf.value = false;
    }
}

// 1) Para qué sirve: exportar un bloque puntual de analítica a Excel.
// 2) Cómo funciona: toma bloque seleccionado y construye un workbook dedicado.
// 3) Qué hace: permite a directivos descargar solo la sección que necesitan.
// 4) Cómo editarla: agrega metadatos adicionales si se requiere trazabilidad.
async function exportarExcelBloque() {
    if (!puedeExportarBloque.value || !bloqueExportacionSeleccionado.value) {
        mensajeError.value = 'No hay información suficiente en el bloque seleccionado para exportar.';
        return;
    }

    exportandoExcel.value = true;
    mensajeExito.value = '';
    mensajeError.value = '';

    try {
        const XLSX = await import('xlsx');
        const bloque = bloqueExportacionSeleccionado.value;
        const libro = XLSX.utils.book_new();

        const hojaBloque = XLSX.utils.aoa_to_sheet([
            [bloque.titulo],
            ['Periodo', `${formatearFecha(filtrosAplicados.value.fecha_inicio)} al ${formatearFecha(filtrosAplicados.value.fecha_fin)}`],
            ['Casino', obtenerCasinoExportacion()],
            [],
            bloque.columnas,
            ...bloque.filas
        ]);

        XLSX.utils.book_append_sheet(libro, hojaBloque, bloque.clave);

        const { fechaInicio, fechaFin } = obtenerPeriodoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estadisticas',
            tipo: `bloque_${String(bloque.clave || 'general').toLowerCase()}`,
            casino: obtenerCasinoExportacion(),
            fechaInicio,
            fechaFin,
            extension: 'xlsx'
        });
        XLSX.writeFile(libro, nombreArchivo);
        mensajeExito.value = `Exportación Excel del bloque "${bloque.titulo}" completada.`;
    } catch (error) {
        mensajeError.value = error?.message || 'No se pudo exportar el bloque a Excel.';
    } finally {
        exportandoExcel.value = false;
    }
}

// 1) Para qué sirve: exportar un bloque puntual a PDF.
// 2) Cómo funciona: convierte la gráfica SVG a PNG y la agrega en jsPDF.
// 3) Qué hace: mantiene exportación estable sin dependencia svg2pdf.
// 4) Cómo editarla: ajusta escala si se cambia formato de página.
async function exportarPdfVectorialBloque() {
    if (!puedeExportarBloque.value || !bloqueExportacionSeleccionado.value) {
        mensajeError.value = 'No hay información suficiente en el bloque seleccionado para exportar.';
        return;
    }

    exportandoPdf.value = true;
    mensajeExito.value = '';
    mensajeError.value = '';

    try {
        const { jsPDF } = await import('jspdf');

        const bloque = bloqueExportacionSeleccionado.value;
        const svg = obtenerSvgDesdeReferencia(bloque.referencia);
        if (!svg) {
            throw new Error('No se encontró la gráfica SVG del bloque seleccionado.');
        }

        const documento = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
        const anchoPagina = documento.internal.pageSize.getWidth();
        const altoPagina = documento.internal.pageSize.getHeight();
        const margen = 28;
        const anchoDisponible = anchoPagina - (margen * 2);

        const anchoSvg = Number(svg?.viewBox?.baseVal?.width) || svg.getBoundingClientRect().width || 900;
        const altoSvg = Number(svg?.viewBox?.baseVal?.height) || svg.getBoundingClientRect().height || 320;
        const escala = anchoDisponible / anchoSvg;
        const altoRender = Math.min(altoPagina - 90, Math.max(160, altoSvg * escala));

        documento.setFont('helvetica', 'bold');
        documento.setFontSize(13);
        documento.text(`Bloque: ${bloque.titulo}`, margen, margen + 6);
        documento.setFont('helvetica', 'normal');
        documento.setFontSize(10);
        documento.text(`Periodo: ${formatearFecha(filtrosAplicados.value.fecha_inicio)} al ${formatearFecha(filtrosAplicados.value.fecha_fin)}`, margen, margen + 22);

        const imagenGrafica = await convertirSvgElementoAPng(svg, anchoDisponible * 2, altoRender * 2);
        documento.addImage(imagenGrafica, 'PNG', margen, margen + 30, anchoDisponible, altoRender);

        const { fechaInicio, fechaFin } = obtenerPeriodoExportacion();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'estadisticas',
            tipo: `bloque_${String(bloque.clave || 'general').toLowerCase()}_pdf`,
            casino: obtenerCasinoExportacion(),
            fechaInicio,
            fechaFin,
            extension: 'pdf'
        });
        documento.save(nombreArchivo);
        mensajeExito.value = `Exportación PDF del bloque "${bloque.titulo}" completada.`;
    } catch (error) {
        mensajeError.value = error?.message || 'No se pudo exportar el bloque a PDF.';
    } finally {
        exportandoPdf.value = false;
    }
}

// 1) Para qué sirve: aplicar presets de rango rápido desde filtros analíticos.
// 2) Cómo funciona: calcula fecha inicio/fin sobre la fecha máxima permitida.
// 3) Qué hace: acelera consulta directiva para ventanas típicas de análisis.
// 4) Cómo editarla: agrega nuevos presets según necesidades del negocio.
function aplicarPeriodoRapido(dias) {
    const fechaFin = new Date(fechaMaxima);
    const fechaInicio = new Date(fechaMaxima);
    fechaInicio.setDate(fechaInicio.getDate() - (dias - 1));

    filtros.modoFecha = 'RANGO';
    filtros.fechaInicio = fechaInicio;
    filtros.fechaFin = fechaFin;
    periodoRapidoActivo.value = dias;
}

// 1) Para qué sirve: indicar que el usuario está en periodo personalizado.
// 2) Cómo funciona: limpia selección de preset rápido activo.
// 3) Qué hace: evita ambigüedad entre fechas manuales y presets.
// 4) Cómo editarla: integra lógica extra si se habilitan presets dinámicos.
function marcarPeriodoPersonalizado() {
    periodoRapidoActivo.value = null;
}

// 1) Para qué sirve: preparar payload de filtros para endpoint de estadísticas.
// 2) Cómo funciona: normaliza modo de fecha y filtros opcionales.
// 3) Qué hace: garantiza consistencia de consulta entre frontend y backend.
// 4) Cómo editarla: agrega nuevos parámetros cuando endpoint se expanda.
function construirParametrosConsulta() {
    const params = {
        tipo_concepto: filtros.tipoConcepto || 'TODOS'
    };

    if (filtros.modoFecha === 'DIA') {
        params.fecha = fechaAFormatoIso(filtros.fechaUnica);
    } else {
        params.fecha_inicio = fechaAFormatoIso(filtros.fechaInicio);
        params.fecha_fin = fechaAFormatoIso(filtros.fechaFin);
    }

    if (filtros.sucursalId) {
        params.sucursal_id = filtros.sucursalId;
    }

    if (Array.isArray(filtros.categoriaIds) && filtros.categoriaIds.length === 1) {
        params.categoria_id = filtros.categoriaIds[0];
    }

    if (Array.isArray(filtros.categoriaIds) && filtros.categoriaIds.length > 1) {
        params.categoria_ids = filtros.categoriaIds.join(',');
    }

    return params;
}

// 1) Para qué sirve: ejecutar la consulta de estadísticas con validaciones previas.
// 2) Cómo funciona: valida fechas/filtros, invoca API y actualiza estado reactivo.
// 3) Qué hace: alimenta KPIs, gráficos y tablas del tablero directivo.
// 4) Cómo editarla: integra cache o paginación si el volumen crece.
async function consultarEstadisticas() {
    if (!puedeVerEstadisticas.value) {
        mensajeError.value = 'No tienes permisos para consultar esta sección.';
        return;
    }

    const fechaDia = fechaAFormatoIso(filtros.fechaUnica);
    const fechaInicio = fechaAFormatoIso(filtros.fechaInicio);
    const fechaFin = fechaAFormatoIso(filtros.fechaFin);

    if (filtros.modoFecha === 'DIA' && !fechaDia) {
        mensajeError.value = 'Selecciona una fecha válida para consultar.';
        return;
    }

    if (filtros.modoFecha === 'RANGO') {
        if (!fechaInicio || !fechaFin) {
            mensajeError.value = 'Selecciona fecha inicio y fecha fin válidas.';
            return;
        }
        if (new Date(fechaInicio) > new Date(fechaFin)) {
            mensajeError.value = 'La fecha inicio no puede ser mayor a la fecha fin.';
            return;
        }
    }

    cargando.value = true;
    mensajeError.value = '';
    mensajeExito.value = '';

    try {
        const params = construirParametrosConsulta();
        const { data } = await obtenerEstadisticasOperativas(params);
        datosEstadisticas.value = data?.data || null;
    } catch (error) {
        datosEstadisticas.value = null;
        mensajeError.value = error?.response?.data?.message || 'No se pudieron cargar las estadísticas.';
    } finally {
        cargando.value = false;
    }
}

// 1) Para qué sirve: restablecer filtros y vista al preset inicial del tablero.
// 2) Cómo funciona: reinicia fechas, catálogo y filtros de tipo/categoría.
// 3) Qué hace: permite volver rápidamente al análisis base de 30 días.
// 4) Cómo editarla: actualiza preset inicial cuando cambien lineamientos.
async function limpiarFiltros() {
    mensajeError.value = '';
    mensajeExito.value = '';

    filtros.modoFecha = 'RANGO';
    filtros.fechaUnica = new Date(fechaMaxima);
    filtros.fechaInicio = new Date(fechaInicioPredeterminada);
    filtros.fechaFin = new Date(fechaMaxima);
    filtros.sucursalId = null;
    filtros.categoriaIds = [];
    filtros.tipoConcepto = 'TODOS';

    periodoRapidoActivo.value = 30;
    vistaDetalleActiva.value = 'CATEGORIAS';

    filtrosBusquedaTablas.categorias = '';
    filtrosBusquedaTablas.rubros = '';
    filtrosBusquedaTablas.conceptos = '';

    await consultarEstadisticas();
}

onMounted(async () => {
    if (puedeVerEstadisticas.value) {
        await consultarEstadisticas();
    }
});
</script>

<template>
    <section class="space-y-6 pb-10">
        <Message v-if="!puedeVerEstadisticas" severity="error" :closable="false">
            No tienes permisos para consultar este modulo.
        </Message>

        <template v-else>
            <div class="card rounded-3xl overflow-hidden border-0 p-0 shadow-sm">
                <div class="bg-gradient-to-r from-slate-900 via-slate-800 to-cyan-900 px-5 py-6 md:px-8 md:py-7 text-white">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                            <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight">Centro de Inteligencia Operativa</h1>
                            <p class="text-slate-200 mt-1">
                                Tablero directivo para analizar ingresos, egresos, neto y comportamiento por categoria, rubro,
                                concepto y casino.
                            </p>
                        </div>
                        <div class="flex flex-wrap items-center gap-2">
                            <Tag value="Exclusivo Director/Admin" severity="contrast" />
                            <Tag :severity="severidadResultadoNeto()" :value="`Estado neto: ${resultadoNeto >= 0 ? 'Favorable' : 'Presion operativa'}`" />
                            <Button
                                icon="pi pi-file-excel"
                                label="Exportar Excel"
                                severity="success"
                                :loading="exportandoExcel"
                                :disabled="!hayInformacionExportable || exportandoPdf"
                                @click="exportarExcelEjecutivo"
                            />
                            <Button
                                icon="pi pi-file-pdf"
                                label="Exportar PDF"
                                severity="danger"
                                :loading="exportandoPdf"
                                :disabled="!hayInformacionExportable || exportandoExcel"
                                @click="exportarPdfVectorial"
                            />
                            <Select
                                v-model="claveBloqueExportacion"
                                :options="opcionesBloquesExportables"
                                optionLabel="label"
                                optionValue="value"
                                optionDisabled="disabled"
                                class="w-full sm:w-72"
                                placeholder="Selecciona bloque"
                                :disabled="!hayInformacionExportable || exportandoExcel || exportandoPdf"
                            />
                            <Button
                                icon="pi pi-file-excel"
                                label="Excel bloque"
                                severity="success"
                                outlined
                                :loading="exportandoExcel"
                                :disabled="!puedeExportarBloque || exportandoPdf"
                                @click="exportarExcelBloque"
                            />
                            <Button
                                icon="pi pi-file-pdf"
                                label="PDF bloque"
                                severity="danger"
                                outlined
                                :loading="exportandoPdf"
                                :disabled="!puedeExportarBloque || exportandoExcel"
                                @click="exportarPdfVectorialBloque"
                            />
                            <Button
                                icon="pi pi-sync"
                                label="Actualizar tablero"
                                :loading="cargando"
                                @click="consultarEstadisticas"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div class="card rounded-2xl border border-surface-200 space-y-4">
                <div class="flex flex-col gap-2">
                    <h2 class="text-lg font-bold text-slate-800">Filtros analiticos avanzados</h2>
                    <p class="text-sm text-slate-500">Selecciona ventana de tiempo, casino, categorias y tipo para recalcular todos los indicadores.</p>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-semibold text-slate-700">Periodos rapidos:</span>
                    <Button
                        v-for="periodo in periodosRapidos"
                        :key="periodo.dias"
                        size="small"
                        :label="periodo.label"
                        :severity="periodoRapidoActivo === periodo.dias ? 'contrast' : 'secondary'"
                        :outlined="periodoRapidoActivo !== periodo.dias"
                        @click="aplicarPeriodoRapido(periodo.dias)"
                    />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-sm font-semibold mb-2">Modo de fecha <span class="text-red-500">*</span></label>
                        <Select
                            v-model="filtros.modoFecha"
                            :options="opcionesModoFecha"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Selecciona modo de consulta"
                            @update:model-value="marcarPeriodoPersonalizado"
                        />
                    </div>

                    <div v-if="filtros.modoFecha === 'DIA'">
                        <label class="block text-sm font-semibold mb-2">Dia contable <span class="text-red-500">*</span></label>
                        <DatePicker
                            v-model="filtros.fechaUnica"
                            dateFormat="yy-mm-dd"
                            :maxDate="fechaMaxima"
                            :manualInput="false"
                            class="w-full"
                            @update:model-value="marcarPeriodoPersonalizado"
                        />
                    </div>

                    <template v-else>
                        <div>
                            <label class="block text-sm font-semibold mb-2">Fecha inicio <span class="text-red-500">*</span></label>
                            <DatePicker
                                v-model="filtros.fechaInicio"
                                dateFormat="yy-mm-dd"
                                :maxDate="fechaMaxima"
                                :manualInput="false"
                                class="w-full"
                                @update:model-value="marcarPeriodoPersonalizado"
                            />
                        </div>
                        <div>
                            <label class="block text-sm font-semibold mb-2">Fecha fin <span class="text-red-500">*</span></label>
                            <DatePicker
                                v-model="filtros.fechaFin"
                                dateFormat="yy-mm-dd"
                                :maxDate="fechaMaxima"
                                :manualInput="false"
                                class="w-full"
                                @update:model-value="marcarPeriodoPersonalizado"
                            />
                        </div>
                    </template>

                    <div>
                        <label class="block text-sm font-semibold mb-2">Casino (opcional)</label>
                        <Select
                            v-model="filtros.sucursalId"
                            :options="opcionesSucursales"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Todos los casinos disponibles"
                            filter
                            filterPlaceholder="Buscar casino por nombre o clave..."
                            showClear
                        />
                    </div>

                    <div>
                        <label class="block text-sm font-semibold mb-2">Categorias operativas (opcional)</label>
                        <MultiSelect
                            v-model="filtros.categoriaIds"
                            :options="opcionesCategorias"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Todas las categorias operativas"
                            display="chip"
                            filter
                            filterPlaceholder="Buscar categoria operativa..."
                        />
                    </div>

                    <div>
                        <label class="block text-sm font-semibold mb-2">Tipo de movimiento</label>
                        <Select
                            v-model="filtros.tipoConcepto"
                            :options="opcionesTipoConcepto"
                            optionLabel="label"
                            optionValue="value"
                            class="w-full"
                            placeholder="Todos, ingresos o egresos"
                        />
                    </div>
                </div>

                <div class="flex flex-wrap items-center justify-end gap-2">
                    <Button label="Limpiar todo" severity="secondary" outlined icon="pi pi-undo" @click="limpiarFiltros" />
                    <Button label="Aplicar filtros" icon="pi pi-search" :loading="cargando" @click="consultarEstadisticas" />
                </div>

                <div class="flex flex-wrap gap-2">
                    <Tag v-for="etiqueta in etiquetasFiltrosActivos" :key="etiqueta" :value="etiqueta" severity="info" />
                </div>
            </div>

            <Message v-if="mensajeError" severity="warn" :closable="false">{{ mensajeError }}</Message>
            <Message v-if="mensajeExito" severity="success" :closable="false">{{ mensajeExito }}</Message>

            <template v-if="datosEstadisticas">
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    <div class="card rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white">
                        <small class="text-emerald-700 font-semibold">Ingresos totales</small>
                        <div class="mt-2">
                            <MontoMonedaColoreado :monto="totalIngresos" />
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 to-white">
                        <small class="text-rose-700 font-semibold">Egresos totales</small>
                        <div class="mt-2">
                            <MontoMonedaColoreado :monto="totalEgresos" />
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-sky-200 bg-gradient-to-br from-sky-50 to-white">
                        <small class="text-sky-700 font-semibold">Resultado neto</small>
                        <div class="mt-2">
                            <MontoMonedaColoreado :monto="resultadoNeto" />
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-white space-y-2">
                        <small class="text-violet-700 font-semibold">Monto promedio por movimiento</small>
                        <div class="rounded-lg border border-violet-200 bg-white/80 px-3 py-2">
                            <small class="text-violet-700 font-semibold block">Ingreso</small>
                            <MontoMonedaColoreado :monto="montoPromedioMovimientoIngreso" />
                        </div>
                        <div class="rounded-lg border border-violet-200 bg-white/80 px-3 py-2">
                            <small class="text-violet-700 font-semibold block">Egreso</small>
                            <MontoMonedaColoreado :monto="montoPromedioMovimientoEgreso" />
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-cyan-200 bg-white">
                        <small class="text-cyan-700 font-semibold">Promedio diario neto</small>
                        <div class="mt-2">
                            <MontoMonedaColoreado :monto="promedioDiarioNeto" />
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-slate-200 bg-white">
                        <small class="text-slate-700 font-semibold">Movimientos</small>
                        <p class="text-3xl font-extrabold mt-2 text-slate-800">{{ formatearNumero(totalMovimientos) }}</p>
                        <p class="text-xs text-slate-500 mt-1">Promedio por dia: {{ formatearNumero(promedioMovimientosDia, 2) }}</p>
                    </div>

                    <div class="card rounded-2xl border border-slate-200 bg-white">
                        <small class="text-slate-700 font-semibold">Margen neto</small>
                        <p class="text-3xl font-extrabold mt-2" :class="claseVariacion(margenNetoPorcentaje)">{{ formatearNumero(margenNetoPorcentaje, 2) }}%</p>
                        <p class="text-xs text-slate-500 mt-1">Resultado neto / ingresos</p>
                    </div>

                    <div class="card rounded-2xl border border-slate-200 bg-white">
                        <small class="text-slate-700 font-semibold">Intensidad operativa</small>
                        <p class="text-3xl font-extrabold mt-2 text-slate-800">{{ formatearNumero(intensidadOperativa, 2) }}%</p>
                        <p class="text-xs text-slate-500 mt-1">Dias con movimientos: {{ diasConMovimientos }} de {{ diasPeriodo }}</p>
                    </div>
                </div>

                <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <div class="card rounded-2xl border border-surface-200 xl:col-span-2 space-y-3">
                        <div class="flex items-center justify-between gap-3">
                            <h3 class="text-base font-bold text-slate-800">Comparativo contra periodo anterior</h3>
                            <Tag severity="info" :value="`${formatearFecha(comparativoAnterior.fecha_inicio)} al ${formatearFecha(comparativoAnterior.fecha_fin)}`" />
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div class="rounded-xl border border-surface-200 p-3">
                                <small class="text-slate-500 block">Variacion ingresos</small>
                                <p class="font-bold text-lg" :class="claseVariacion(comparativoAnterior.variacion_porcentual?.ingresos)">
                                    {{ formatearVariacion(comparativoAnterior.variacion_porcentual?.ingresos) }}
                                </p>
                                <div class="mt-2">
                                    <MontoMonedaColoreado :monto="Number(comparativoAnterior.total_ingresos || 0)" />
                                </div>
                            </div>

                            <div class="rounded-xl border border-surface-200 p-3">
                                <small class="text-slate-500 block">Variacion egresos</small>
                                <p class="font-bold text-lg" :class="claseVariacion(comparativoAnterior.variacion_porcentual?.egresos)">
                                    {{ formatearVariacion(comparativoAnterior.variacion_porcentual?.egresos) }}
                                </p>
                                <div class="mt-2">
                                    <MontoMonedaColoreado :monto="Number(comparativoAnterior.total_egresos || 0)" />
                                </div>
                            </div>

                            <div class="rounded-xl border border-surface-200 p-3">
                                <small class="text-slate-500 block">Variacion neto</small>
                                <p class="font-bold text-lg" :class="claseVariacion(comparativoAnterior.variacion_porcentual?.resultado_neto)">
                                    {{ formatearVariacion(comparativoAnterior.variacion_porcentual?.resultado_neto) }}
                                </p>
                                <div class="mt-2">
                                    <MontoMonedaColoreado :monto="Number(comparativoAnterior.resultado_neto || 0)" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card rounded-2xl border border-surface-200 space-y-3">
                        <h3 class="text-base font-bold text-slate-800">Insights ejecutivos</h3>
                        <div class="space-y-2">
                            <div v-for="insight in insightsClave" :key="insight" class="rounded-lg border border-surface-200 p-3 text-sm text-slate-700">
                                {{ insight }}
                            </div>
                        </div>
                        <div class="rounded-lg border border-slate-200 p-3 bg-slate-50 text-sm">
                            <p class="font-semibold text-slate-700">Relacion ingresos/egresos</p>
                            <p class="text-slate-900 text-lg font-bold mt-1">
                                {{ razonIngresosEgresos === null ? 'Sin base de egresos' : `${formatearNumero(razonIngresosEgresos, 2)}x` }}
                            </p>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <div class="card rounded-2xl border border-surface-200 xl:col-span-2">
                        <div class="flex items-center justify-between gap-3 mb-3">
                            <h3 class="text-base font-bold text-slate-800">Flujo diario: ingresos, egresos y neto</h3>
                            <Tag severity="secondary" :value="`${seriePorDia.length} dias`" />
                        </div>
                        <ComponenteGraficas ref="referenciaGraficaFlujo" type="line" height="360" :options="opcionesFlujoDiario" :series="seriesFlujoDiario" />
                    </div>

                    <div class="card rounded-2xl border border-surface-200">
                        <h3 class="text-base font-bold text-slate-800 mb-3">Distribucion por tipo</h3>
                        <ComponenteGraficas ref="referenciaGraficaDistribucion" type="donut" height="360" :options="opcionesDistribucionTipo" :series="seriesDistribucionTipo" />
                    </div>
                </div>

                <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div class="card rounded-2xl border border-surface-200">
                        <h3 class="text-base font-bold text-slate-800 mb-3">Impacto por categoria operativa</h3>
                        <ComponenteGraficas ref="referenciaGraficaCategorias" type="line" height="340" :options="opcionesCategoriasImpacto" :series="seriesCategoriasImpacto" />
                    </div>

                    <div class="card rounded-2xl border border-surface-200">
                        <h3 class="text-base font-bold text-slate-800 mb-3">Mapa de conceptos principales</h3>
                        <ComponenteGraficas ref="referenciaGraficaConceptos" type="treemap" height="340" :options="opcionesTopConceptosTreemap" :series="seriesTopConceptosTreemap" />
                    </div>
                </div>

                <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div class="card rounded-2xl border border-surface-200">
                        <h3 class="text-base font-bold text-slate-800 mb-3">Rendimiento por casino</h3>
                        <ComponenteGraficas ref="referenciaGraficaSucursales" type="line" height="340" :options="opcionesGraficaSucursales" :series="seriesSucursales" />
                    </div>

                    <div class="card rounded-2xl border border-surface-200">
                        <h3 class="text-base font-bold text-slate-800 mb-3">Pulso semanal de neto acumulado</h3>
                        <ComponenteGraficas ref="referenciaGraficaSemanal" type="heatmap" height="340" :options="opcionesPulsoSemanal" :series="seriesPulsoSemanal" />
                    </div>
                </div>

                <div class="card rounded-2xl border border-surface-200 space-y-4">
                    <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <h3 class="text-base font-bold text-slate-800">Detalle analitico expandido</h3>
                        <div class="flex flex-wrap gap-2">
                            <Button
                                v-for="vista in vistasDetalle"
                                :key="vista.value"
                                size="small"
                                :label="vista.label"
                                :severity="vistaDetalleActiva === vista.value ? 'contrast' : 'secondary'"
                                :outlined="vistaDetalleActiva !== vista.value"
                                @click="vistaDetalleActiva = vista.value"
                            />
                        </div>
                    </div>

                    <div v-if="vistaDetalleActiva === 'CATEGORIAS'" class="space-y-3">
                        <IconField iconPosition="left" class="w-full md:w-96">
                            <InputIcon class="pi pi-search" />
                            <InputText v-model="filtrosBusquedaTablas.categorias" class="w-full" placeholder="Buscar categoria por nombre o clave" />
                        </IconField>

                        <DataTable
                            :value="tablaCategoriasFiltrada"
                            paginator
                            :rows="10"
                            :rowsPerPageOptions="[10, 20, 50, 100]"
                            stripedRows
                            showGridlines
                            responsiveLayout="scroll"
                            sortMode="multiple"
                            removableSort
                            resizableColumns
                            columnResizeMode="fit"
                            reorderableColumns
                            class="w-full"
                        >
                            <Column field="categoria_clave" header="Clave" sortable />
                            <Column field="categoria_nombre" header="Categoria" sortable />
                            <Column field="movimientos" header="Movimientos" sortable>
                                <template #body="slotProps">
                                    {{ formatearNumero(slotProps.data.movimientos) }}
                                </template>
                            </Column>
                            <Column field="ingresos" header="Ingresos" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.ingresos || 0" />
                                </template>
                            </Column>
                            <Column field="egresos" header="Egresos" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.egresos || 0" />
                                </template>
                            </Column>
                            <Column field="neto" header="Neto" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.neto || 0" />
                                </template>
                            </Column>
                            <Column field="promedio_monto" header="Promedio por movimiento" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.promedio_monto || 0" />
                                </template>
                            </Column>
                        </DataTable>
                    </div>

                    <div v-else-if="vistaDetalleActiva === 'RUBROS'" class="space-y-3">
                        <IconField iconPosition="left" class="w-full md:w-96">
                            <InputIcon class="pi pi-search" />
                            <InputText v-model="filtrosBusquedaTablas.rubros" class="w-full" placeholder="Buscar rubro por nombre o padre" />
                        </IconField>

                        <DataTable
                            :value="tablaRubrosFiltrada"
                            paginator
                            :rows="10"
                            :rowsPerPageOptions="[10, 20, 50, 100]"
                            stripedRows
                            showGridlines
                            responsiveLayout="scroll"
                            sortMode="multiple"
                            removableSort
                            resizableColumns
                            columnResizeMode="fit"
                            reorderableColumns
                            class="w-full"
                        >
                            <Column field="rubro_nombre_con_padre" header="Rubro contable" sortable />
                            <Column field="movimientos" header="Movimientos" sortable>
                                <template #body="slotProps">
                                    {{ formatearNumero(slotProps.data.movimientos) }}
                                </template>
                            </Column>
                            <Column field="ingresos" header="Ingresos" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.ingresos || 0" />
                                </template>
                            </Column>
                            <Column field="egresos" header="Egresos" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.egresos || 0" />
                                </template>
                            </Column>
                            <Column field="neto" header="Neto" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.neto || 0" />
                                </template>
                            </Column>
                            <Column field="promedio_monto" header="Promedio por movimiento" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.promedio_monto || 0" />
                                </template>
                            </Column>
                        </DataTable>
                    </div>

                    <div v-else class="space-y-3">
                        <IconField iconPosition="left" class="w-full md:w-96">
                            <InputIcon class="pi pi-search" />
                            <InputText v-model="filtrosBusquedaTablas.conceptos" class="w-full" placeholder="Buscar concepto por nombre, categoria o tipo" />
                        </IconField>

                        <DataTable
                            :value="tablaConceptosFiltrada"
                            paginator
                            :rows="10"
                            :rowsPerPageOptions="[10, 20, 50, 100]"
                            stripedRows
                            showGridlines
                            responsiveLayout="scroll"
                            sortMode="multiple"
                            removableSort
                            resizableColumns
                            columnResizeMode="fit"
                            reorderableColumns
                            class="w-full"
                        >
                            <Column field="concepto_nombre" header="Concepto" sortable />
                            <Column field="categoria_nombre" header="Categoria" sortable />
                            <Column field="concepto_tipo" header="Tipo" sortable />
                            <Column field="movimientos" header="Movimientos" sortable>
                                <template #body="slotProps">
                                    {{ formatearNumero(slotProps.data.movimientos) }}
                                </template>
                            </Column>
                            <Column field="monto_total" header="Monto total" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.monto_total || 0" />
                                </template>
                            </Column>
                            <Column field="monto_promedio" header="Monto promedio" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado :monto="slotProps.data.monto_promedio || 0" />
                                </template>
                            </Column>
                        </DataTable>
                    </div>
                </div>

                <Message v-if="sinResultados" severity="info" :closable="false">
                    El periodo seleccionado no tiene movimientos. Ajusta filtros para analizar otra ventana.
                </Message>

                <Dialog
                    v-model:visible="detalleDrilldown.visible"
                    modal
                    :style="{ width: 'min(96vw, 860px)' }"
                    :header="detalleDrilldown.titulo || 'Detalle analítico'"
                    @hide="cerrarDrilldown"
                >
                    <div class="space-y-3">
                        <p v-if="detalleDrilldown.subtitulo" class="text-sm text-slate-500">
                            {{ detalleDrilldown.subtitulo }}
                        </p>

                        <DataTable
                            :value="detalleDrilldown.filas"
                            paginator
                            :rows="8"
                            :rowsPerPageOptions="[8, 16, 24]"
                            stripedRows
                            responsiveLayout="scroll"
                            sortMode="multiple"
                            removableSort
                            class="w-full"
                        >
                            <Column field="etiqueta" header="Concepto" sortable />
                            <Column field="valor_texto" header="Detalle" sortable>
                                <template #body="slotProps">
                                    <span>{{ slotProps.data.valor_texto || '-' }}</span>
                                </template>
                            </Column>
                            <Column field="valor_monetario" header="Monto" sortable>
                                <template #body="slotProps">
                                    <MontoMonedaColoreado v-if="slotProps.data.valor_monetario !== null" :monto="slotProps.data.valor_monetario || 0" />
                                    <span v-else>-</span>
                                </template>
                            </Column>
                        </DataTable>
                    </div>
                </Dialog>
            </template>
        </template>
    </section>
</template>