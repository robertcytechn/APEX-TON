# Workflow Frontend UI/UX (obligatorio)

Aplica a cualquier cambio en `Vue\`.

## Paso 1 - Preparacion

1. Cargar reglas: `normativas_generales`, `stack_tecnologico`, `estilos_frontend`, `comportamiento_roles`.
2. Activar skill `ui-ux-pro-max`.
3. Identificar vistas/componentes/rutas afectadas.

## Paso 2 - Diseno UX

1. Definir estado de carga, vacio, error y exito.
2. Mantener textos visibles en espanol.
3. Asegurar responsive y accesibilidad minima en formularios y tablas.

## Paso 3 - Implementacion visual

1. Mantener consistencia con PrimeVue + Tailwind.
2. Respetar organizacion por rol en `src\views\admin|contador|director`.
3. Usar `MontoMonedaColoreado` para montos monetarios.

## Paso 4 - Integracion API

1. Respetar contrato del backend y manejo de sesion.
2. No romper navegacion, menu lateral ni control visual por permisos.
3. Si cambia comportamiento funcional de UI, documentar en `docs\frontend\` segun `04_workflow_documentacion_reglas.md`.
