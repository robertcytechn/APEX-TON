# AGENTS - Estandar operativo de IA (APEX-TON)

Este archivo define como deben operar los agentes dentro del proyecto APEX-TON.
Objetivo: eliminar ambiguedad, reducir retrabajo y asegurar entregas consistentes.

## 1) Alcance real del proyecto

- Backend: `DJANGO\` (Django + DRF + MySQL + Celery)
- Frontend: `Vue\` (Vue 3 + PrimeVue + Tailwind + Vite)
- Documentacion funcional y tecnica: `docs\backend\` y `docs\frontend\`
- Reglas de agentes: `.agents\rules\`
- Workflows de agentes: `.agents\workFlows\`

## 2) Carga minima obligatoria por tarea

Antes de proponer o editar codigo, el agente debe:

1. Leer `rules\normativas_generales.md`
2. Leer `rules\stack_tecnologico.md`
3. Leer archivos relacionados al cambio o nueva como son los .vue, .py, .js afectados para entender contexto y stack real.
4. Detectar alcance de la tarea (backend, frontend, fullstack, negocio)
5. Activar skill segun matriz de uso
6. Seguir workflow correspondiente en `workFlows\`

## 3) Matriz obligatoria de skills

| Si la tarea es... | Skill obligatorio | Resultado esperado |
|---|---|---|
| Modelos Django, DRF, serializers, viewsets, permisos, Celery, migraciones, auth por sesion | `django-pro` | Cambios backend consistentes con arquitectura Django del proyecto |
| UI, UX, layout, componentes Vue/PrimeVue, accesibilidad, responsive, formularios/tablas | `ui-ux-pro-max` | Interfaz consistente, usable y alineada al estandar visual |
| Planificacion por fases, ejecucion multietapa, tareas largas con seguimiento | `planning` | Plan claro, hitos y ejecucion controlada |
| Diseno de memoria contextual, recuperacion de conocimiento, reglas de contexto de agente | `agent-memory-systems` | Estructura de memoria clara y util para continuidad |

Regla: si una tarea toca backend y frontend, usar ambos skills (`django-pro` + `ui-ux-pro-max`) y workflow fullstack.

## 4) Reglas por dominio (que archivo aplicar)

- Reglas transversales: `rules\normativas_generales.md`
- Stack y versiones: `rules\stack_tecnologico.md`
- Backend/API: `rules\api_backend.md`
- Base de datos: `rules\base_de_datos.md`
- Negocio tesoreria: `rules\tesoreria_negocio.md`
- Roles/permisos/horarios: `rules\comportamiento_roles.md`
- Frontend/UI-UX: `rules\estilos_frontend.md`

## 5) Workflows obligatorios

- `workFlows\01_workflow_backend_django.md`
- `workFlows\02_workflow_frontend_uiux.md`
- `workFlows\03_workflow_fullstack_integracion.md`
- `workFlows\04_workflow_documentacion_reglas.md`
- `workFlows\05_workflow_memory_problemas.md`

## 6) Criterio de salida (Definition of Done del agente)

Una tarea se considera terminada cuando:

1. El cambio cumple reglas del dominio afectado.
2. El skill correcto fue usado segun alcance.
3. Backend y frontend quedan coherentes entre si (si aplica).
4. La documentacion en `docs\backend\` o `docs\frontend\` y/o reglas en `.agents\` se actualiza si el comportamiento cambia.

## 7) Reducir costo de agentes
- usamos un numero limitado de peticiones api de gemini y otros llm de githubcopilot, por lo que es crucial que cada peticion tenga un proposito claro y se evite el uso excesivo o innecesario.
- Antes de hacer una peticion, el agente debe asegurarse de que tiene toda la informacion.