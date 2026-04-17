// 1) Para que sirve: estandarizar nombres de archivo de exportacion en todo el frontend.
// 2) Como funciona: normaliza segmentos (modulo, tipo, casino, periodo) y agrega marca de tiempo.
// 3) Que hace: evita nombres inconsistentes y facilita trazabilidad de archivos generados.
// 4) Como editarla: reutilizar en toda exportacion nueva en lugar de construir nombres manualmente.

function normalizarSegmento(valor, predeterminado = 'sin_dato') {
    const texto = String(valor ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-zA-Z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .toLowerCase();
    return texto || predeterminado;
}

function fechaIsoACompacta(valor) {
    const texto = String(valor ?? '').trim();
    const coincidenciaIso = texto.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (coincidenciaIso) {
        return `${coincidenciaIso[1]}${coincidenciaIso[2]}${coincidenciaIso[3]}`;
    }

    const fecha = new Date(texto);
    if (Number.isNaN(fecha.getTime())) {
        return '';
    }

    const anio = String(fecha.getFullYear());
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${anio}${mes}${dia}`;
}

function obtenerPeriodoCompacto(fechaInicio, fechaFin) {
    const inicio = fechaIsoACompacta(fechaInicio);
    const fin = fechaIsoACompacta(fechaFin || fechaInicio);

    if (!inicio && !fin) {
        return 'sin_periodo';
    }
    if ((inicio || fin) === (fin || inicio)) {
        return `periodo_${inicio || fin}`;
    }
    return `periodo_${inicio || fin}_a_${fin || inicio}`;
}

function obtenerMarcaTiempo() {
    const ahora = new Date();
    const anio = String(ahora.getFullYear());
    const mes = String(ahora.getMonth() + 1).padStart(2, '0');
    const dia = String(ahora.getDate()).padStart(2, '0');
    const hora = String(ahora.getHours()).padStart(2, '0');
    const minuto = String(ahora.getMinutes()).padStart(2, '0');
    const segundo = String(ahora.getSeconds()).padStart(2, '0');
    return `${anio}${mes}${dia}_${hora}${minuto}${segundo}`;
}

// 1) Para que sirve: construir nombre unico y consistente para exportaciones.
// 2) Como funciona: compone plantilla fija con segmentos normalizados.
// 3) Que hace: produce archivos con formato apto para sistema de archivos y auditoria.
// 4) Como editarla: agrega nuevos segmentos aqui para impactar todas las exportaciones.
export function crearNombreArchivoExportacion({
    modulo,
    tipo,
    casino,
    fechaInicio,
    fechaFin,
    extension
}) {
    const extensionLimpia = normalizarSegmento(extension || 'dat', 'dat').replace(/_/g, '');
    const segmentos = [
        'binsurmx',
        normalizarSegmento(modulo, 'reporte'),
        normalizarSegmento(tipo, 'general'),
        normalizarSegmento(casino, 'sin_casino'),
        obtenerPeriodoCompacto(fechaInicio, fechaFin),
        obtenerMarcaTiempo()
    ];

    return `${segmentos.join('_')}.${extensionLimpia}`;
}