import api from '@/service/api';
import axios from 'axios';

// 1) Para qué sirve: obtener sucursales disponibles para filtros de reportes.
// 2) Cómo funciona: consume endpoint de sucursales del backend.
// 3) Qué hace: provee opciones de selección para consultas de resultados.
// 4) Cómo editarla: integra paginación o filtros al endpoint si backend lo solicita.
export function listarSucursalesReporte() {
    return api.get('/sucursales/');
}

// 1) Para qué sirve: consultar estado de resultados histórico o en tiempo real.
// 2) Cómo funciona: envía parámetros de sucursal/periodo a endpoint dedicado.
// 3) Qué hace: retorna consolidado por categoría y rubro contable.
// 4) Cómo editarla: ajusta parámetros esperados si cambian reglas de consulta.
export function obtenerEstadoResultados(params) {
    return api.get('/estado-resultados/', { params });
}

// 1) Para qué sirve: consultar tablero analítico con filtros operativos avanzados.
// 2) Cómo funciona: envía filtros de fecha, casino, categoría y tipo al endpoint dedicado.
// 3) Qué hace: retorna métricas ejecutivas y series para gráficas/tablas.
// 4) Cómo editarla: extiende params cuando backend incorpore nuevas dimensiones.
export function obtenerEstadisticasOperativas(params = {}) {
    return api.get('/estado-resultados/estadisticas/', { params });
}

// 1) Para qué sirve: obtener tipo de cambio USD/MXN en vivo desde fuentes públicas.
// 2) Cómo funciona: intenta varias APIs en orden y valida que el valor sea numérico positivo.
// 3) Qué hace: devuelve primera tasa válida junto con fuente y fecha de actualización.
// 4) Cómo editarla: agrega/quita proveedores en `fuentes` manteniendo el contrato de retorno.
export async function obtenerTipoCambioUsdMxnActual() {
    const fuentes = [
        {
            nombre: 'ExchangeRate-API',
            url: 'https://open.er-api.com/v6/latest/USD',
            extraer: (data) => ({
                tipoCambio: Number(data?.rates?.MXN),
                actualizadoEn: data?.time_last_update_utc || null,
                fuente: 'ExchangeRate-API (open.er-api.com)',
            }),
        },
        {
            nombre: 'Frankfurter',
            url: 'https://api.frankfurter.app/latest?from=USD&to=MXN',
            extraer: (data) => ({
                tipoCambio: Number(data?.rates?.MXN),
                actualizadoEn: data?.date || null,
                fuente: 'Frankfurter (api.frankfurter.app)',
            }),
        },
        {
            nombre: 'Currency API (fawazahmed0)',
            url: 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json',
            extraer: (data) => ({
                tipoCambio: Number(data?.usd?.mxn),
                actualizadoEn: data?.date || null,
                fuente: 'Currency API (jsDelivr/fawazahmed0)',
            }),
        },
    ];

    const errores = [];

    for (const fuente of fuentes) {
        try {
            const respuesta = await axios.get(fuente.url, {
                timeout: 10000,
            });

            const resultado = fuente.extraer(respuesta?.data);
            const tipoCambio = Number(resultado?.tipoCambio);

            if (!Number.isFinite(tipoCambio) || tipoCambio <= 0) {
                throw new Error(`Respuesta invalida de ${fuente.nombre}`);
            }

            return {
                tipoCambio,
                actualizadoEn: resultado?.actualizadoEn || null,
                fuente: resultado?.fuente || fuente.nombre,
            };
        } catch (error) {
            const detalle = error?.message || 'sin detalle';
            errores.push(`${fuente.nombre}: ${detalle}`);
        }
    }

    throw new Error(`No fue posible obtener el tipo de cambio USD/MXN desde ninguna fuente. Intentos: ${errores.join(' | ')}`);
}
