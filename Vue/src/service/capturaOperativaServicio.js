import api from '@/service/api';

function obtenerConfiguracionNotificacionSilenciosa() {
    return {
        notificacionToast: {
            exito: false,
            error: false
        }
    };
}

// 1) Para qué sirve: obtener catálogo de categorías operativas disponibles.
// 2) Cómo funciona: consulta endpoint de categorías sin parámetros.
// 3) Qué hace: alimenta menú/rutas de captura operativa.
// 4) Cómo editarla: agrega params de filtrado si backend habilita paginación/filtros.
export function listarCategoriasOperativas() {
    return api.get('/categorias/');
}

// 1) Para qué sirve: obtener detalle completo de una categoría específica.
// 2) Cómo funciona: llama endpoint REST por id en la URL.
// 3) Qué hace: devuelve conceptos y detalles parametrizados para render de captura.
// 4) Cómo editarla: cambia ruta base si el recurso se versiona.
export function obtenerCategoriaOperativa(idCategoria) {
    return api.get(`/categorias/${idCategoria}/`);
}

// 1) Para qué sirve: recuperar o crear el reporte diario actual por sucursal.
// 2) Cómo funciona: envía sucursal_id como query param al endpoint actual.
// 3) Qué hace: asegura contexto de día contable antes de capturar movimientos.
// 4) Cómo editarla: agrega parámetros adicionales si backend extiende el endpoint.
export function obtenerReporteDiarioActual(sucursalId) {
    return api.get('/reportes-diarios/actual/', {
        params: {
            sucursal_id: sucursalId
        }
    });
}

// 1) Para qué sirve: recuperar o crear el reporte diario de una fecha contable específica.
// 2) Cómo funciona: envía sucursal_id y fecha_contable al endpoint actual.
// 3) Qué hace: permite capturar días abiertos distintos al día contable por defecto.
// 4) Cómo editarla: agrega validaciones de cliente si se extiende el contrato de fecha.
export function obtenerReporteDiarioPorFecha(sucursalId, fechaContable) {
    return api.get('/reportes-diarios/actual/', {
        params: {
            sucursal_id: sucursalId,
            fecha_contable: fechaContable
        }
    });
}

// 1) Para qué sirve: consultar estado de saldo inicial mensual por categoría.
// 2) Cómo funciona: envía sucursal, categoría y fecha contable al endpoint dedicado.
// 3) Qué hace: retorna saldo inicial/final, origen y si requiere captura manual.
// 4) Cómo editarla: añade filtros opcionales cuando backend exponga nuevos parámetros.
export function obtenerSaldoInicialCategoriaMensual(sucursalId, categoriaId, fechaContable) {
    return api.get('/reportes-diarios/saldo-inicial-categoria/', {
        params: {
            sucursal_id: sucursalId,
            categoria_id: categoriaId,
            fecha_contable: fechaContable
        }
    });
}

// 1) Para qué sirve: registrar manualmente el primer saldo inicial mensual de una categoría.
// 2) Cómo funciona: envía payload con sucursal/categoría/fecha/monto al endpoint de captura manual.
// 3) Qué hace: fija saldo inicial del mes y lo bloquea para mantener trazabilidad.
// 4) Cómo editarla: integra motivo o firma de autorización si negocio lo solicita.
export function establecerSaldoInicialCategoriaManual(payload) {
    return api.post('/reportes-diarios/saldo-inicial-categoria/manual/', payload);
}

// 1) Para qué sirve: listar configuraciones globales consumidas en captura.
// 2) Cómo funciona: consulta el endpoint de configuraciones globales.
// 3) Qué hace: permite leer variables como tipo de cambio vigente.
// 4) Cómo editarla: ajusta la ruta si se separa por módulo/namespace.
export function listarConfiguracionesGlobales() {
    return api.get('/configuraciones-globales/configuraciones/');
}

// 1) Para qué sirve: consultar movimientos diarios con filtros opcionales.
// 2) Cómo funciona: envía objeto params directamente a axios.
// 3) Qué hace: soporta filtrado por reporte y categoría.
// 4) Cómo editarla: agrega normalización de params si backend cambia nombres de filtro.
export function listarMovimientosDiarios(params = {}) {
    return api.get('/movimientos-diarios/', { params });
}

// 1) Para qué sirve: guardar captura rápida en formato JSON o multipart.
// 2) Cómo funciona: detecta FormData y agrega cabecera multipart cuando aplica.
// 3) Qué hace: crea/actualiza movimiento y opcionalmente adjunta archivo de respaldo.
// 4) Cómo editarla: actualiza manejo de headers si backend cambia recepción de archivos.
export function guardarCapturaRapida(payload) {
    const configuracionNotificacionSilenciosa = obtenerConfiguracionNotificacionSilenciosa();

    if (payload instanceof FormData) {
        return api.post('/movimientos-diarios/captura-rapida/', payload, {
            ...configuracionNotificacionSilenciosa,
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
    }
    return api.post('/movimientos-diarios/captura-rapida/', payload, configuracionNotificacionSilenciosa);
}

// 1) Para qué sirve: eliminar un movimiento diario específico desde captura operativa.
// 2) Cómo funciona: invoca DELETE sobre el endpoint del movimiento por id.
// 3) Qué hace: permite retirar una fila guardada por error en la tabla dinámica.
// 4) Cómo editarla: agrega confirmaciones externas solo en componentes, no en este wrapper.
export function eliminarMovimientoDiario(idMovimiento) {
    return api.delete(`/movimientos-diarios/${idMovimiento}/`);
}
