# Workflow Memory de problemas e incidentes

Aplica para registrar contexto util de errores/problemas en `.agents\memory\`.

## Paso 1 - Activacion

Cuando exista un bug, incidente o fallo recurrente, activar este workflow.
Si la tarea es de memoria contextual, usar skill `agent-memory-systems`.

## Paso 2 - Archivo por problema

Guardar un archivo por descripcion de problema en:

`.agents\memory\`

Formato de nombre obligatorio:

`<descripcion_problema>_<YYYY-MM-DD>_v<version>.md`

Ejemplo:

`error_inicio_sesion_2026-04-19_v1.0.md`

## Paso 3 - Contenido minimo del archivo

1. Titulo con version:
   - `# v1.0 - Error inicio de sesion`
2. Sintoma observado
3. Contexto (modulo, endpoint, vista o proceso afectado)
4. Causa raiz (si se conoce)
5. Solucion aplicada o propuesta
6. Archivos impactados
7. Estado actual (resuelto, en seguimiento, pendiente)

## Paso 4 - Regla de versionado en memory

- Primer registro del problema: `v1.0`
- Ajustes o nuevos hallazgos del mismo problema: `v1.1`, `v1.2`, ...
- Cambio importante de diagnostico/solucion: `v2.0`

## Paso 5 - Relacion con documentacion tecnica

Si el problema implica cambios funcionales estables, documentar tambien en:

- `docs\backend\` o
- `docs\frontend\`

segun corresponda, aplicando `04_workflow_documentacion_reglas.md`.
