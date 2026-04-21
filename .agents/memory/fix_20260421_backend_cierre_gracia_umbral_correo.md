# Fix 2026-04-21 · Backend · Cierre con gracia y correos de cierre

## Problema
- La tarea `auto_cerrar_dias_con_gracia` cerraba reportes abiertos aunque sus movimientos fueran cero o montos mínimos por captura equivocada.
- El envío de correo de cierre podía no ejecutarse de forma confiable por carreras de transacción (encolado antes del commit) y por bloqueo `select_for_update` sin `transaction.atomic`.
- El cierre manual (`cerrar_actual` y `cerrar`) no programaba correo de cierre.
- Los logs no eran lo suficientemente detallados para aislar en qué etapa fallaba cada tarea.

## Solución
- Se agregó umbral de seguridad en cierre con gracia: un reporte solo cierra si tiene movimientos y `total_ingresos + total_egresos > 10.00`.
- Se centralizó el encolado de correo en `_encolar_envio_correo_cierre` con manejo seguro de errores y trazabilidad (`reporte_id`, `origen`, `task_id`).
- Se cambió el disparo del correo a `transaction.on_commit(...)` en cierres automáticos y manuales.
- Se reforzó `enviar_correo_cierre_reporte` con `transaction.atomic`, logs por etapa y anti-duplicado robusto.
- Cuando no hay destinatarios configurados, ya no se marca `correo_enviado=True`, para permitir reintentos posteriores.

## Archivos modificados
- `DJANGO/reportes_diarios/tareas.py`
- `DJANGO/reportes_diarios/views.py`
- `DJANGO/reportes_diarios/tests.py`
- `docs/backend/03_operacion_diaria.md`

## Impacto
- Menor riesgo de cierres automáticos indebidos por capturas en cero o montos marginales.
- Mayor confiabilidad del flujo de correo al cierre (manual y automático) al eliminar condiciones de carrera.
- Diagnóstico operativo más rápido con bitácoras de etapa y resumen de métricas por ejecución.

## Lecciones aprendidas
- En flujos con side effects (correo, eventos), encolar tareas Celery dentro de transacciones sin `on_commit` puede provocar omisiones silenciosas.
- En pruebas con `TestCase/APITestCase`, las validaciones de callbacks `on_commit` requieren ejecución explícita (`captureOnCommitCallbacks`).
- No conviene marcar como "enviado" un correo que realmente fue omitido por configuración faltante.
