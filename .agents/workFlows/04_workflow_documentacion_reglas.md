# Workflow de documentacion tecnica y funcional

Aplica cuando un cambio modifica comportamiento en backend, frontend o reglas de agente.

## Paso 1 - Estructura obligatoria

1. La carpeta `docs\` debe trabajar con dos subcarpetas:
   - `docs\backend\`
   - `docs\frontend\`
2. No mezclar documentacion de frontend dentro de backend ni viceversa.

## Paso 2 - Convencion de nombres de archivos

Usar nombres descriptivos por tipo de modulo + recurso:

- Backend: `api_<nombre>.md`, `vista_<nombre>.md`, `modelo_<nombre>.md`
- Frontend: `vista_<nombre>.md`, `componente_<nombre>.md`, `flujo_<nombre>.md`

Ejemplos:

- `docs\backend\api_usuarios_login.md`
- `docs\backend\modelo_reporte_diario.md`
- `docs\frontend\vista_estado_resultados.md`

## Paso 3 - Formato interno obligatorio del documento

La primera linea debe iniciar con version + nombre del recurso:

`# v1.0 - API usuarios_login`

Luego documentar como minimo:

1. Que es
2. Para que funciona
3. Como funciona (flujo)
4. Entradas/salidas o contrato (si aplica)
5. Reglas de negocio/permisos relacionados
6. Cambios recientes

## Paso 4 - Regla de versionado de documento

- Primer documento de un recurso: `v1.0`
- Cambios incrementales sin ruptura: `v1.1`, `v1.2`, ...
- Cambios relevantes de comportamiento/contrato: `v2.0`, `v3.0`, ...

El versionado siempre se actualiza en el encabezado del mismo archivo.

## Paso 5 - Regla de sincronizacion con agentes

Si cambia estandar de documentacion o naming:

1. Actualizar este workflow.
2. Actualizar `agents.md` si cambia alcance o rutas.
3. Mantener reglas de `.agents\rules\` coherentes con la estructura `docs\backend` / `docs\frontend`.
