# Workflow Backend Django (obligatorio)

Aplica a cualquier cambio en `DJANGO\`.

## Paso 1 - Preparacion

1. Cargar reglas: `normativas_generales`, `stack_tecnologico`, `api_backend`, `base_de_datos`.
2. Activar skill `django-pro`.
3. Identificar apps/modulos impactados (modelo, serializer, viewset, rutas, permisos, celery).

## Paso 2 - Diseno del cambio

1. Definir contrato API esperado (entrada/salida).
2. Verificar impacto en roles/permisos y horario operativo.
3. Verificar impacto en snapshots historicos (si toca reportes/cierres).

## Paso 3 - Implementacion coherente

1. Aplicar cambio en modelo/migracion (si aplica).
2. Ajustar serializer, vista y rutas en la misma iteracion.
3. Mantener envelope JSON estandar (`status`, `message`, `data`).

## Paso 4 - Integracion

1. Verificar consumo esperado por frontend.
2. Actualizar documentacion en `docs\backend\` siguiendo `04_workflow_documentacion_reglas.md`.
