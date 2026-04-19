# Workflow Fullstack (backend + frontend)

Usar este flujo cuando una tarea toque `DJANGO\` y `Vue\` en la misma historia.

## Paso 1 - Orquestacion

1. Cargar reglas base y de ambas capas.
2. Activar skills `django-pro` y `ui-ux-pro-max`.
3. Definir primero el contrato API final y luego el consumo frontend.

## Paso 2 - Secuencia recomendada

1. Ajustar backend (modelo/serializer/vista/ruta/permisos).
2. Ajustar frontend (servicio, estado, vista, feedback UX).
3. Verificar reglas de negocio, roles y horario operativo.

## Paso 3 - Criterios de coherencia

1. Sin endpoints huerfanos ni vistas desconectadas.
2. Sin campos frontend no soportados por API.
3. Sin cambios de negocio sin actualizacion documental.

## Paso 4 - Documentacion y cierre

Si el cambio altera flujo funcional o contrato:

- `docs\backend\` (backend)
- `docs\frontend\` (frontend)
- Ajustes en `.agents\rules\` o `.agents\workFlows\` cuando cambie el estandar de trabajo.

Siempre aplicar convenciones de nombre y versionado definidas en `04_workflow_documentacion_reglas.md`.
