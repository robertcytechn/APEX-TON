import api from '@/service/api';

// 1) Para qué sirve: listar reportes diarios con filtros enviados por query params.
// 2) Cómo funciona: delega objeto params al cliente axios.
// 3) Qué hace: devuelve colección de reportes para tablas o búsquedas.
// 4) Cómo editarla: ajusta nombres de filtros si backend cambia contrato.
export function listarReportesDiarios(params = {}) {
    return api.get('/reportes-diarios/', { params });
}

// 1) Para qué sirve: obtener un reporte diario puntual por id.
// 2) Cómo funciona: construye endpoint REST con id en ruta.
// 3) Qué hace: retorna encabezado y métricas del reporte solicitado.
// 4) Cómo editarla: cambia la ruta si el endpoint se mueve de módulo.
export function obtenerReporteDiario(idReporte) {
    return api.get(`/reportes-diarios/${idReporte}/`);
}

// 1) Para qué sirve: listar movimientos asociados a un reporte diario.
// 2) Cómo funciona: consulta movimientos-diarios con filtro reporte_id.
// 3) Qué hace: obtiene detalle transaccional para vista de reporte.
// 4) Cómo editarla: añade filtros adicionales aquí cuando se requiera segmentar resultados.
export function listarMovimientosPorReporte(idReporte) {
    return api.get('/movimientos-diarios/', {
        params: { reporte_id: idReporte }
    });
}

// 1) Para qué sirve: obtener el libro operativo diario con formato columnar por rango.
// 2) Cómo funciona: envía sucursal y fechas al endpoint dedicado de reportes diarios.
// 3) Qué hace: retorna filas de FECHA/CONCEPTO/INGRESO/EGRESO/SALDO y resumen.
// 4) Cómo editarla: amplía params cuando backend exponga segmentaciones adicionales.
export function obtenerLibroOperativoDiario(params = {}) {
    return api.get('/reportes-diarios/libro-operativo/', { params });
}

// 1) Para qué sirve: obtener el resumen rápido del día contable de una sucursal.
// 2) Cómo funciona: consulta endpoint dedicado con sucursal_id y fecha opcional.
// 3) Qué hace: devuelve avances de captura, neto y conceptos recurrentes faltantes.
// 4) Cómo editarla: agrega nuevos parámetros si backend expone filtros adicionales.
export function obtenerResumenDiaContableActual(params = {}) {
    return api.get('/reportes-diarios/resumen-actual/', { params });
}

// 1) Para qué sirve: ejecutar el cierre operativo del día contable por sucursal.
// 2) Cómo funciona: envía sucursal_id y fecha opcional al endpoint de cierre actual.
// 3) Qué hace: bloquea el reporte diario para impedir nuevas modificaciones.
// 4) Cómo editarla: adapta payload si negocio añade campos de confirmación/motivo.
export function cerrarDiaContableActual(payload = {}) {
    return api.post('/reportes-diarios/cerrar-actual/', payload);
}

// 1) Para qué sirve: obtener el tablero mensual de estados de días contables por casino.
// 2) Cómo funciona: envía sucursal_id, anio y mes como query params al endpoint dedicado.
// 3) Qué hace: devuelve color/estado por día para construir el calendario operativo.
// 4) Cómo editarla: añade parámetros opcionales aquí si backend integra más filtros.
export function obtenerCalendarioMensualDiasContables(params = {}) {
    return api.get('/reportes-diarios/calendario-mensual/', { params });
}
