## Problema
Director y Administrador no contaban con una vista dedicada para auditar, en modo solo lectura, el detalle de capturas operativas realizadas por Contador o Gerente por día contable y categoría operativa.

## Solución
Se implementó la vista `ConsultaCapturaOperativaDirector.vue` en `views/director/` con filtros por casino, día contable y categoría. La consulta resuelve primero el reporte del día y después lista movimientos filtrados para mostrar una tabla estilo Excel con detalle de concepto, tipo, montos, detalles parametrizados, notas y evidencia, sin exponer acciones de edición.

## Archivos modificados
- `Vue/src/views/director/ConsultaCapturaOperativaDirector.vue`
- `Vue/src/router/index.js`
- `Vue/src/layout/AppMenu.vue`
- `docs/frontend/05_vistas_administrativas.md`

## Impacto
- Se habilita revisión ejecutiva granular de captura operativa para roles directivos y administrativos.
- La navegación principal incorpora acceso directo para `DIRECTOR`, `ADMINISTRADOR` y `SUPERUSUARIO`.
- No se modificó el flujo de captura operativa ni la escritura en backend.

## Lecciones aprendidas
- Para vistas de auditoría por día conviene resolver primero el `reporte_diario` y después consultar `movimientos`, evitando ambigüedad por fecha.
- Reutilizar servicios existentes (`listarReportesDiarios`, `listarMovimientosDiarios`) reduce riesgo de inconsistencia entre pantallas.
