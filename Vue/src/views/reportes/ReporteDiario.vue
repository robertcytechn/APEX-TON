<script setup>
import MontoMonedaColoreado from '@/components/MontoMonedaColoreado.vue';
import { listarSucursalesReporte } from '@/service/estadoResultadosServicio';
import { obtenerLibroOperativoDiario } from '@/service/reporteDiarioServicio';
import { useSesionStore } from '@/stores/sesion';
import { crearNombreArchivoExportacion } from '@/utils/nombresExportacion';
import { computed, onMounted, ref } from 'vue';

const sesionStore = useSesionStore();

const cargando = ref(false);
const exportandoExcel = ref(false);
const exportandoPdf = ref(false);
const sucursales = ref([]);
const filasLibro = ref([]);
const resumenLibro = ref({
    saldo_inicial: 0,
    total_ingresos: 0,
    total_egresos: 0,
    saldo_final: 0,
    dias_consultados: 0,
    dias_con_reporte: 0
});
const filtroAplicado = ref(null);
const mensaje = ref('');
const mensajeExito = ref('');
const mensajeError = ref('');

const hoy = new Date();
const diaContable = new Date(hoy);
diaContable.setDate(hoy.getDate() - 1);

const filtroSucursalId = ref(sesionStore.usuario?.sucursal_id || null);
const filtroRangoFechas = ref([new Date(diaContable), new Date(diaContable)]);

const puedeVerControlesAvanzados = computed(() => sesionStore.cumpleAlgunoRoles(['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']));
const esOperativo = computed(() => sesionStore.esContadorOGerente);
const sucursalAsignadaId = computed(() => Number(sesionStore.usuario?.sucursal_id || 0));

const sucursalActual = computed(() => {
    return sucursales.value.find((sucursal) => Number(sucursal.id) === Number(filtroSucursalId.value)) || null;
});

const fechaContableVisible = computed(() => {
    const fechaDesdeApi = String(filtroAplicado.value?.fecha_inicio || '').trim();
    if (fechaDesdeApi) {
        return fechaDesdeApi;
    }
    return convertirFechaAISO(diaContable);
});

const textoFechaContableEnCurso = computed(() => {
    const fecha = convertirIsoAFecha(fechaContableVisible.value);
    return fecha.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: 'long',
        day: '2-digit'
    });
});

const textoCasinoEnCurso = computed(() => {
    return sucursalActual.value?.nombre || 'Sin casino asignado';
});

const hayInformacionExportable = computed(() => Array.isArray(filasLibro.value) && filasLibro.value.length > 0);

// 1) Para qué sirve: convertir Date a cadena ISO YYYY-MM-DD en zona local.
// 2) Cómo funciona: arma año/mes/día con padStart.
// 3) Qué hace: garantiza formato esperado por filtros backend.
// 4) Cómo editarla: centraliza cambio de formato si API evoluciona.
function convertirFechaAISO(fecha) {
    if (!(fecha instanceof Date) || Number.isNaN(fecha.getTime())) {
        return '';
    }
    const anio = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

// 1) Para qué sirve: convertir texto ISO de fecha a objeto Date local.
// 2) Cómo funciona: separa segmentos y crea Date con año/mes/día.
// 3) Qué hace: evita desfases de zona horaria al renderizar fechas contables.
// 4) Cómo editarla: reutiliza en nuevos filtros que consuman fechas ISO.
function convertirIsoAFecha(fechaIso) {
    const texto = String(fechaIso || '').trim();
    if (!texto) {
        return new Date(diaContable);
    }

    const partes = texto.split('-').map((segmento) => Number(segmento));
    if (partes.length !== 3 || partes.some((parte) => !Number.isInteger(parte))) {
        return new Date(diaContable);
    }

    return new Date(partes[0], partes[1] - 1, partes[2]);
}

// 1) Para qué sirve: normalizar el rango capturado en DatePicker para consulta backend.
// 2) Cómo funciona: toma extremos válidos y completa fin cuando solo hay una fecha.
// 3) Qué hace: asegura consultas con fecha_inicio/fecha_fin consistentes.
// 4) Cómo editarla: agrega límites de rango adicionales si negocio los solicita.
function obtenerRangoNormalizado() {
    if (!Array.isArray(filtroRangoFechas.value) || filtroRangoFechas.value.length === 0) {
        return [null, null];
    }

    const inicio = filtroRangoFechas.value[0] instanceof Date ? filtroRangoFechas.value[0] : null;
    const fin = filtroRangoFechas.value[1] instanceof Date ? filtroRangoFechas.value[1] : inicio;

    if (!inicio || Number.isNaN(inicio.getTime()) || !fin || Number.isNaN(fin.getTime())) {
        return [null, null];
    }

    if (inicio <= fin) {
        return [inicio, fin];
    }
    return [fin, inicio];
}

// 1) Para qué sirve: definir clases de énfasis visual por tipo de fila del libro.
// 2) Cómo funciona: evalúa campo tipo_fila enviado por backend.
// 3) Qué hace: replica lectura tipo hoja operativa con filas clave resaltadas.
// 4) Cómo editarla: ajusta colores según lineamientos de diseño del proyecto.
function claseFilaLibro(fila) {
    const tipoFila = String(fila?.tipo_fila || '');
    if (tipoFila === 'SALDO_INICIAL') {
        return 'bg-sky-50 font-semibold';
    }
    if (tipoFila === 'TOTAL_PERIODO') {
        return 'bg-amber-100 font-semibold text-amber-950';
    }
    if (tipoFila === 'EFECTIVO_FISICO') {
        return 'bg-emerald-100 font-semibold text-emerald-950';
    }
    return '';
}

// 1) Para qué sirve: decidir si una celda monetaria debe renderizar monto o guion.
// 2) Cómo funciona: valida que exista un número finito en el valor recibido.
// 3) Qué hace: evita ruido visual en columnas ingreso/egreso cuando no aplica.
// 4) Cómo editarla: acepta strings numéricos si backend cambia formato de salida.
function celdaTieneMonto(valor) {
    return Number.isFinite(Number(valor));
}

// 1) Para qué sirve: limpiar alertas de exportación antes de nuevas acciones.
// 2) Cómo funciona: reinicia mensajes de éxito y error.
// 3) Qué hace: evita mostrar estados obsoletos al usuario.
// 4) Cómo editarla: agrega reinicio de nuevos banners si se incorporan.
function limpiarMensajesExportacion() {
    mensajeExito.value = '';
    mensajeError.value = '';
}

// 1) Para qué sirve: formatear fecha ISO a etiqueta legible en español.
// 2) Cómo funciona: parsea la fecha y aplica toLocaleDateString.
// 3) Qué hace: homologa encabezados de exportación para dirección.
// 4) Cómo editarla: cambia formato regional si se requiere otro país.
function formatearFecha(fechaIso) {
    const fecha = convertirIsoAFecha(fechaIso);
    return fecha.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// 1) Para qué sirve: obtener etiqueta textual del periodo actualmente consultado.
// 2) Cómo funciona: toma fecha inicio/fin aplicadas y construye rango o fecha única.
// 3) Qué hace: inserta contexto de filtros en Excel y PDF.
// 4) Cómo editarla: agrega hora de corte si negocio lo solicita.
function obtenerPeriodoTextoExportacion() {
    const fechaInicio = String(filtroAplicado.value?.fecha_inicio || fechaContableVisible.value || '').trim();
    const fechaFin = String(filtroAplicado.value?.fecha_fin || fechaContableVisible.value || '').trim();

    if (!fechaInicio && !fechaFin) {
        return 'Sin período definido';
    }
    if (fechaInicio && fechaFin && fechaInicio !== fechaFin) {
        return `${formatearFecha(fechaInicio)} al ${formatearFecha(fechaFin)}`;
    }
    return formatearFecha(fechaInicio || fechaFin);
}

// 1) Para qué sirve: serializar una fila del libro a estructura de Excel.
// 2) Cómo funciona: transforma valores nulos y preserva montos numéricos.
// 3) Qué hace: garantiza compatibilidad de apertura/uso nativo en Excel.
// 4) Cómo editarla: agrega columnas nuevas cuando cambie el contrato del libro.
function construirFilasExcelLibro() {
    return filasLibro.value.map((fila) => ({
        Partida: String(fila?.partida || ''),
        Concepto: String(fila?.concepto || ''),
        Ingreso: celdaTieneMonto(fila?.ingreso) ? Number(fila.ingreso) : '',
        Egreso: celdaTieneMonto(fila?.egreso) ? Number(fila.egreso) : '',
        Saldo: Number(fila?.saldo || 0),
        Tipo_fila: String(fila?.tipo_fila || '')
    }));
}

// 1) Para qué sirve: exportar el libro operativo a Excel nativo.
// 2) Cómo funciona: construye libro con hoja resumen y hoja de detalle.
// 3) Qué hace: entrega archivo utilizable directamente en Microsoft Excel.
// 4) Cómo editarla: agrega hojas complementarias según nuevas necesidades.
async function exportarExcelLibro() {
    if (!hayInformacionExportable.value) {
        mensajeError.value = 'No hay datos en pantalla para exportar a Excel.';
        return;
    }

    exportandoExcel.value = true;
    limpiarMensajesExportacion();

    try {
        const XLSX = await import('xlsx');
        const libro = XLSX.utils.book_new();
        const fechaExportacion = convertirFechaAISO(new Date());
        const nombreCasino = textoCasinoEnCurso.value;
        const periodo = obtenerPeriodoTextoExportacion();

        const hojaResumen = XLSX.utils.aoa_to_sheet([
            ['Reporte diario operativo'],
            ['Fecha de exportación', formatearFecha(fechaExportacion)],
            ['Casino', nombreCasino],
            ['Periodo', periodo],
            [],
            ['Indicador', 'Valor'],
            ['Saldo inicial del rango', Number(resumenLibro.value.saldo_inicial || 0)],
            ['Total ingresos', Number(resumenLibro.value.total_ingresos || 0)],
            ['Total egresos', Number(resumenLibro.value.total_egresos || 0)],
            ['Saldo final', Number(resumenLibro.value.saldo_final || 0)],
            ['Días consultados', Number(resumenLibro.value.dias_consultados || 0)],
            ['Días con reporte', Number(resumenLibro.value.dias_con_reporte || 0)]
        ]);

        const hojaLibro = XLSX.utils.json_to_sheet(construirFilasExcelLibro());

        XLSX.utils.book_append_sheet(libro, hojaResumen, 'Resumen');
        XLSX.utils.book_append_sheet(libro, hojaLibro, 'Libro_Operativo');

        const fechaInicioExportacion = String(filtroAplicado.value?.fecha_inicio || fechaContableVisible.value || '').trim();
        const fechaFinExportacion = String(filtroAplicado.value?.fecha_fin || fechaInicioExportacion || '').trim();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'reporte_diario',
            tipo: 'libro_operativo',
            casino: nombreCasino,
            fechaInicio: fechaInicioExportacion,
            fechaFin: fechaFinExportacion,
            extension: 'xlsx'
        });
        XLSX.writeFile(libro, nombreArchivo);
        mensajeExito.value = 'Exportación Excel completada correctamente.';
    } catch (error) {
        mensajeError.value = error?.message || 'No se pudo exportar el archivo Excel.';
    } finally {
        exportandoExcel.value = false;
    }
}

// 1) Para qué sirve: escapar caracteres reservados para texto SVG válido.
// 2) Cómo funciona: reemplaza entidades XML básicas.
// 3) Qué hace: previene corrupción del SVG por textos con símbolos.
// 4) Cómo editarla: agrega nuevas entidades si se detectan más casos.
function escaparTextoSvg(valor) {
    return String(valor ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

// 1) Para qué sirve: recortar etiquetas largas para que no desborden columnas SVG.
// 2) Cómo funciona: limita longitud y agrega puntos suspensivos.
// 3) Qué hace: mantiene legibilidad de tabla vectorial en PDF.
// 4) Cómo editarla: ajusta máximos al cambiar anchos de columna.
function truncarTexto(valor, longitudMaxima) {
    const texto = String(valor ?? '');
    if (texto.length <= longitudMaxima) {
        return texto;
    }
    return `${texto.slice(0, Math.max(0, longitudMaxima - 3))}...`;
}

// 1) Para qué sirve: colorear filas clave dentro del SVG del PDF.
// 2) Cómo funciona: devuelve color por tipo de fila del backend.
// 3) Qué hace: destaca TOTAL y EFECTIVO para lectura rápida.
// 4) Cómo editarla: reemplaza paleta según lineamientos visuales.
function colorFondoPorTipoFila(tipoFila) {
    const tipo = String(tipoFila || '');
    if (tipo === 'SALDO_INICIAL') {
        return '#e0f2fe';
    }
    if (tipo === 'TOTAL_PERIODO') {
        return '#fde68a';
    }
    if (tipo === 'EFECTIVO_FISICO') {
        return '#a7f3d0';
    }
    return '#ffffff';
}

// 1) Para qué sirve: renderizar montos en notación de moneda para exportaciones.
// 2) Cómo funciona: usa Intl.NumberFormat con 2 decimales fijos.
// 3) Qué hace: mantiene consistencia visual entre pantalla y documentos.
// 4) Cómo editarla: cambia locale/decimales si el negocio lo exige.
function formatearMonto(valor) {
    return new Intl.NumberFormat('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(Number(valor || 0));
}

// 1) Para qué sirve: construir un SVG vectorial del reporte para una página PDF.
// 2) Cómo funciona: dibuja encabezado, metadata y tabla con filas del chunk.
// 3) Qué hace: habilita exportación PDF nítida sin rasterizar contenido.
// 4) Cómo editarla: ajusta tamaños de fuente o márgenes según diseño.
function construirSvgPaginaPdf({
    filasPagina,
    numeroPagina,
    totalPaginas,
    anchoPagina,
    altoPagina,
    margen,
    fechaExportacion,
    periodo,
    casino
}) {
    const anchoContenido = anchoPagina - (margen * 2);
    const anchosColumnas = [
        Math.round(anchoContenido * 0.16),
        Math.round(anchoContenido * 0.34),
        Math.round(anchoContenido * 0.16),
        Math.round(anchoContenido * 0.16),
        anchoContenido - Math.round(anchoContenido * 0.16) - Math.round(anchoContenido * 0.34) - Math.round(anchoContenido * 0.16) - Math.round(anchoContenido * 0.16)
    ];

    const altoFila = 20;
    const altoEncabezadoTabla = 24;
    const inicioTablaY = margen + 106;
    const partes = [];

    partes.push(`<rect x="0" y="0" width="${anchoPagina}" height="${altoPagina}" fill="#ffffff" />`);
    partes.push(`<text x="${margen}" y="${margen + 16}" font-family="Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#0f172a">${escaparTextoSvg('Reporte Diario Operativo')}</text>`);
    partes.push(`<text x="${margen}" y="${margen + 36}" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#334155">${escaparTextoSvg(`Fecha de exportación: ${fechaExportacion}`)}</text>`);
    partes.push(`<text x="${margen}" y="${margen + 52}" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#334155">${escaparTextoSvg(`Periodo: ${periodo}`)}</text>`);
    partes.push(`<text x="${margen}" y="${margen + 68}" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#334155">${escaparTextoSvg(`Casino: ${casino}`)}</text>`);
    partes.push(`<text x="${anchoPagina - margen}" y="${margen + 68}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="10" fill="#334155">${escaparTextoSvg(`Página ${numeroPagina} de ${totalPaginas}`)}</text>`);

    partes.push(`<rect x="${margen}" y="${inicioTablaY}" width="${anchoContenido}" height="${altoEncabezadoTabla}" fill="#0f172a" />`);

    const encabezados = ['Partida', 'Concepto', 'Ingreso', 'Egreso', 'Saldo'];
    let cursorXEncabezado = margen;
    for (let indice = 0; indice < encabezados.length; indice += 1) {
        const anchoColumna = anchosColumnas[indice];
        const textoEncabezado = encabezados[indice];
        const esColumnaMonto = indice >= 2;
        const xTexto = esColumnaMonto ? cursorXEncabezado + anchoColumna - 6 : cursorXEncabezado + 6;
        const ancla = esColumnaMonto ? 'end' : 'start';
        partes.push(`<text x="${xTexto}" y="${inicioTablaY + 16}" text-anchor="${ancla}" font-family="Helvetica, Arial, sans-serif" font-size="10" font-weight="700" fill="#ffffff">${escaparTextoSvg(textoEncabezado)}</text>`);
        cursorXEncabezado += anchoColumna;
    }

    filasPagina.forEach((fila, indiceFila) => {
        const yFila = inicioTablaY + altoEncabezadoTabla + (indiceFila * altoFila);
        const fondoFila = colorFondoPorTipoFila(fila?.tipo_fila);
        const colorTexto = String(fila?.tipo_fila || '') === 'TOTAL_PERIODO' || String(fila?.tipo_fila || '') === 'EFECTIVO_FISICO' ? '#111827' : '#1e293b';
        const pesoTexto = String(fila?.tipo_fila || '') === 'CATEGORIA_RESUMEN' ? '500' : '700';

        partes.push(`<rect x="${margen}" y="${yFila}" width="${anchoContenido}" height="${altoFila}" fill="${fondoFila}" />`);

        const valores = [
            truncarTexto(fila?.partida || '-', 20),
            truncarTexto(fila?.concepto || '-', 42),
            celdaTieneMonto(fila?.ingreso) ? formatearMonto(fila.ingreso) : '-',
            celdaTieneMonto(fila?.egreso) ? formatearMonto(fila.egreso) : '-',
            formatearMonto(fila?.saldo || 0)
        ];

        let cursorX = margen;
        for (let indiceColumna = 0; indiceColumna < valores.length; indiceColumna += 1) {
            const anchoColumna = anchosColumnas[indiceColumna];
            const esColumnaMonto = indiceColumna >= 2;
            const xTexto = esColumnaMonto ? cursorX + anchoColumna - 6 : cursorX + 6;
            const ancla = esColumnaMonto ? 'end' : 'start';
            partes.push(`<text x="${xTexto}" y="${yFila + 14}" text-anchor="${ancla}" font-family="Helvetica, Arial, sans-serif" font-size="9" font-weight="${pesoTexto}" fill="${colorTexto}">${escaparTextoSvg(valores[indiceColumna])}</text>`);
            cursorX += anchoColumna;
        }
    });

    const altoTabla = altoEncabezadoTabla + (filasPagina.length * altoFila);
    const yFinalTabla = inicioTablaY + altoTabla;
    partes.push(`<rect x="${margen}" y="${inicioTablaY}" width="${anchoContenido}" height="${altoTabla}" fill="none" stroke="#94a3b8" stroke-width="1" />`);

    let cursorXLinea = margen;
    anchosColumnas.forEach((anchoColumna) => {
        cursorXLinea += anchoColumna;
        partes.push(`<line x1="${cursorXLinea}" y1="${inicioTablaY}" x2="${cursorXLinea}" y2="${yFinalTabla}" stroke="#cbd5e1" stroke-width="1" />`);
    });

    for (let indiceFila = 0; indiceFila <= filasPagina.length; indiceFila += 1) {
        const yLinea = inicioTablaY + altoEncabezadoTabla + (indiceFila * altoFila);
        partes.push(`<line x1="${margen}" y1="${yLinea}" x2="${margen + anchoContenido}" y2="${yLinea}" stroke="#e2e8f0" stroke-width="1" />`);
    }

    return `<svg xmlns="http://www.w3.org/2000/svg" width="${anchoPagina}" height="${altoPagina}" viewBox="0 0 ${anchoPagina} ${altoPagina}">${partes.join('')}</svg>`;
}

// 1) Para qué sirve: convertir un texto SVG en imagen PNG en memoria.
// 2) Cómo funciona: crea un Blob, lo carga en Image y lo dibuja en canvas.
// 3) Qué hace: permite insertar páginas PDF sin depender de svg2pdf.
// 4) Cómo editarla: ajusta resolución canvas si se requiere más nitidez.
async function convertirTextoSvgAPng(textoSvg, anchoPx, altoPx) {
    const blob = new Blob([textoSvg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    try {
        const imagen = await new Promise((resolve, reject) => {
            const elemento = new Image();
            elemento.onload = () => resolve(elemento);
            elemento.onerror = () => reject(new Error('No se pudo cargar la imagen SVG para PDF.'));
            elemento.src = url;
        });

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(anchoPx || imagen.width || 1));
        canvas.height = Math.max(1, Math.round(altoPx || imagen.height || 1));
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

// 1) Para qué sirve: exportar el reporte diario a PDF multipágina.
// 2) Cómo funciona: renderiza cada página SVG en imagen PNG y la inserta en jsPDF.
// 3) Qué hace: evita error de dependencias ESM en tiempo de ejecución.
// 4) Cómo editarla: incrementa resolución de imagen si se requiere más detalle.
async function exportarPdfSvgLibro() {
    if (!hayInformacionExportable.value) {
        mensajeError.value = 'No hay datos en pantalla para exportar a PDF.';
        return;
    }

    exportandoPdf.value = true;
    limpiarMensajesExportacion();

    try {
        const { jsPDF } = await import('jspdf');

        const documento = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
        const anchoPagina = documento.internal.pageSize.getWidth();
        const altoPagina = documento.internal.pageSize.getHeight();
        const margen = 28;
        const altoFila = 20;
        const altoEncabezadoTabla = 24;
        const inicioTablaY = margen + 106;
        const altoDisponibleTabla = altoPagina - margen - inicioTablaY;
        const filasPorPagina = Math.max(1, Math.floor((altoDisponibleTabla - altoEncabezadoTabla) / altoFila));
        const totalPaginas = Math.max(1, Math.ceil(filasLibro.value.length / filasPorPagina));
        const fechaExportacion = formatearFecha(convertirFechaAISO(new Date()));
        const periodo = obtenerPeriodoTextoExportacion();
        const casino = textoCasinoEnCurso.value;

        for (let indicePagina = 0; indicePagina < totalPaginas; indicePagina += 1) {
            if (indicePagina > 0) {
                documento.addPage();
            }

            const inicio = indicePagina * filasPorPagina;
            const fin = inicio + filasPorPagina;
            const filasPagina = filasLibro.value.slice(inicio, fin);

            const textoSvg = construirSvgPaginaPdf({
                filasPagina,
                numeroPagina: indicePagina + 1,
                totalPaginas,
                anchoPagina,
                altoPagina,
                margen,
                fechaExportacion,
                periodo,
                casino
            });

            const imagenPagina = await convertirTextoSvgAPng(textoSvg, anchoPagina * 2, altoPagina * 2);
            documento.addImage(imagenPagina, 'PNG', 0, 0, anchoPagina, altoPagina);
        }

        const fechaInicioExportacion = String(filtroAplicado.value?.fecha_inicio || fechaContableVisible.value || '').trim();
        const fechaFinExportacion = String(filtroAplicado.value?.fecha_fin || fechaInicioExportacion || '').trim();
        const nombreArchivo = crearNombreArchivoExportacion({
            modulo: 'reporte_diario',
            tipo: 'libro_operativo_pdf',
            casino,
            fechaInicio: fechaInicioExportacion,
            fechaFin: fechaFinExportacion,
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

// 1) Para qué sirve: cargar catálogo de sucursales activas para filtros del reporte.
// 2) Cómo funciona: consulta endpoint, filtra por estado y ordena por nombre.
// 3) Qué hace: habilita selector inicial del casino a consultar.
// 4) Cómo editarla: agrega filtros de acceso por rol si backend expone esa metadata.
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

// 1) Para qué sirve: consultar libro operativo diario en formato columnar.
// 2) Cómo funciona: envía sucursal y rango según rol al endpoint de libro-operativo.
// 3) Qué hace: hidrata filas PARTIDA/CONCEPTO/INGRESO/EGRESO/SALDO y resumen.
// 4) Cómo editarla: agrega parámetros de segmentación cuando backend los exponga.
const consultar = async () => {
    mensaje.value = '';
    limpiarMensajesExportacion();
    filasLibro.value = [];
    resumenLibro.value = {
        saldo_inicial: 0,
        total_ingresos: 0,
        total_egresos: 0,
        saldo_final: 0,
        dias_consultados: 0,
        dias_con_reporte: 0
    };
    filtroAplicado.value = null;

    if (esOperativo.value) {
        filtroSucursalId.value = sucursalAsignadaId.value || null;
    }

    if (!filtroSucursalId.value) {
        mensaje.value = puedeVerControlesAvanzados.value
            ? 'Selecciona un casino para consultar el reporte diario.'
            : 'Tu usuario no tiene un casino asignado. Solicita apoyo al administrador.';
        return;
    }

    const params = {
        sucursal_id: filtroSucursalId.value
    };

    if (puedeVerControlesAvanzados.value) {
        const [fechaInicio, fechaFin] = obtenerRangoNormalizado();
        if (!fechaInicio || !fechaFin) {
            mensaje.value = 'Selecciona un rango de fechas válido para consultar.';
            return;
        }
        params.fecha_inicio = convertirFechaAISO(fechaInicio);
        params.fecha_fin = convertirFechaAISO(fechaFin);
    }

    cargando.value = true;
    try {
        const respuestaLibro = await obtenerLibroOperativoDiario(params);
        const dataLibro = respuestaLibro?.data?.data || {};
        const filas = Array.isArray(dataLibro.filas) ? dataLibro.filas : [];

        filasLibro.value = filas;
        resumenLibro.value = {
            saldo_inicial: Number(dataLibro?.resumen?.saldo_inicial || 0),
            total_ingresos: Number(dataLibro?.resumen?.total_ingresos || 0),
            total_egresos: Number(dataLibro?.resumen?.total_egresos || 0),
            saldo_final: Number(dataLibro?.resumen?.saldo_final || 0),
            dias_consultados: Number(dataLibro?.resumen?.dias_consultados || 0),
            dias_con_reporte: Number(dataLibro?.resumen?.dias_con_reporte || 0)
        };
        filtroAplicado.value = dataLibro?.filtro_aplicado || null;

        if (!filas.length) {
            mensaje.value = 'No se encontraron datos operativos para el rango seleccionado.';
        }
    } catch (error) {
        mensaje.value = error?.response?.data?.message || 'No se pudo consultar el reporte diario.';
    } finally {
        cargando.value = false;
    }
};

// 1) Para qué sirve: cargar datos iniciales de la pantalla al montarse.
// 2) Cómo funciona: obtiene sucursales y ejecuta la primera consulta automática.
// 3) Qué hace: evita que la vista abra vacía para el usuario.
// 4) Cómo editarla: incluye inicialización de nuevos filtros si se agregan.
onMounted(async () => {
    await cargarSucursales();
    await consultar();
});
</script>

<template>
    <section class="space-y-4">
        <div class="card space-y-4">
            <div>
                <h1 class="text-2xl font-semibold">Reporte diario operativo</h1>
                <p class="text-surface-500 mt-1">Formato columnar tipo libro: ingreso, egreso y saldo acumulado usando categorías de operación.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div v-if="puedeVerControlesAvanzados">
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Casino <span class="text-red-500">*</span></label>
                    <Select
                        v-model="filtroSucursalId"
                        :options="sucursales"
                        optionLabel="nombre"
                        optionValue="id"
                        class="w-full"
                        placeholder="Selecciona casino"
                        filter
                        filterPlaceholder="Buscar opción..."
                    />
                </div>

                <div v-else>
                    <label class="block text-sm mb-2"><i class="pi pi-building mr-1 text-primary"></i>Casino visible</label>
                    <div class="w-full rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-surface-700 font-semibold">
                        {{ textoCasinoEnCurso }}
                    </div>
                </div>

                <template v-if="puedeVerControlesAvanzados">
                    <div class="md:col-span-2">
                        <label class="block text-sm mb-2"><i class="pi pi-calendar mr-1 text-primary"></i>Rango de fechas <span class="text-red-500">*</span></label>
                        <DatePicker
                            v-model="filtroRangoFechas"
                            selectionMode="range"
                            dateFormat="yy-mm-dd"
                            :manualInput="false"
                            class="w-full"
                        />
                    </div>
                </template>

                <div v-else class="md:col-span-2">
                    <label class="block text-sm mb-2"><i class="pi pi-calendar-clock mr-1 text-primary"></i>Fecha visible</label>
                    <div class="w-full rounded-lg border border-surface-200 bg-surface-50 px-3 py-2 text-surface-700 font-semibold">
                        Fecha en curso: {{ textoFechaContableEnCurso }}
                    </div>
                </div>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3">
                <Tag
                    v-if="filtroAplicado?.filtro_forzado"
                    severity="warn"
                    value="Consulta restringida a día contable actual por rol operativo"
                />
                <div class="flex flex-wrap items-center gap-2">
                    <Button icon="pi pi-search" label="Consultar reporte" :loading="cargando" @click="consultar" />
                    <Button
                        icon="pi pi-file-excel"
                        label="Exportar Excel"
                        severity="success"
                        outlined
                        :loading="exportandoExcel"
                        :disabled="!hayInformacionExportable || cargando || exportandoPdf"
                        @click="exportarExcelLibro"
                    />
                    <Button
                        icon="pi pi-file-pdf"
                        label="Exportar PDF"
                        severity="danger"
                        outlined
                        :loading="exportandoPdf"
                        :disabled="!hayInformacionExportable || cargando || exportandoExcel"
                        @click="exportarPdfSvgLibro"
                    />
                </div>
            </div>
        </div>

        <Message v-if="mensaje" severity="warn" :closable="false">{{ mensaje }}</Message>
        <Message v-if="mensajeExito" severity="success" :closable="false">{{ mensajeExito }}</Message>
        <Message v-if="mensajeError" severity="error" :closable="false">{{ mensajeError }}</Message>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            <div class="card space-y-1">
                <small class="text-surface-500">Saldo inicial del rango</small>
                <MontoMonedaColoreado :monto="resumenLibro.saldo_inicial" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Total ingresos</small>
                <MontoMonedaColoreado :monto="resumenLibro.total_ingresos" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Total egresos</small>
                <MontoMonedaColoreado :monto="resumenLibro.total_egresos" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Saldo final</small>
                <MontoMonedaColoreado :monto="resumenLibro.saldo_final" />
            </div>
            <div class="card space-y-1">
                <small class="text-surface-500">Días consultados / con reporte</small>
                <p class="font-semibold text-lg mt-1">{{ resumenLibro.dias_consultados }} / {{ resumenLibro.dias_con_reporte }}</p>
            </div>
        </div>

        <div class="card">
            <DataTable
                :value="filasLibro"
                :loading="cargando"
                responsiveLayout="scroll"
                :rowClass="claseFilaLibro"
            >
                <Column field="partida" header="Partida" style="min-width: 10rem" />
                <Column field="concepto" header="Concepto" style="min-width: 16rem" />
                <Column field="ingreso" header="Ingreso" style="min-width: 10rem">
                    <template #body="slotProps">
                        <div v-if="celdaTieneMonto(slotProps.data.ingreso)">
                            <MontoMonedaColoreado :monto="slotProps.data.ingreso" />
                        </div>
                        <span v-else class="text-surface-500">-</span>
                    </template>
                </Column>
                <Column field="egreso" header="Egreso" style="min-width: 10rem">
                    <template #body="slotProps">
                        <div v-if="celdaTieneMonto(slotProps.data.egreso)">
                            <MontoMonedaColoreado :monto="slotProps.data.egreso" />
                        </div>
                        <span v-else class="text-surface-500">-</span>
                    </template>
                </Column>
                <Column field="saldo" header="Saldo" style="min-width: 12rem">
                    <template #body="slotProps">
                        <MontoMonedaColoreado :monto="slotProps.data.saldo || 0" />
                    </template>
                </Column>
            </DataTable>
        </div>
    </section>
</template>

