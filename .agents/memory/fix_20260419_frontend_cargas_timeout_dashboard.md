# fix_20260419_frontend_cargas_timeout_dashboard

## Problema
- Varias pantallas podían tardar demasiado en cargar o quedarse en espera sin feedback claro cuando un endpoint no respondía.
- El tablero de Director iniciaba en un rango histórico amplio, incrementando costo de consulta/render y percepción de bloqueo.
- El tablero de Administrador dependía de `Promise.all`, por lo que un fallo en un módulo impedía renderizar los demás.

## Solución
- Se agregó timeout global en `service/api.js` para evitar esperas indefinidas (`20000 ms` por defecto, configurable con `VITE_API_TIMEOUT_MS`).
- Se mejoró `extraerMensajeError` en `notificacionesApi.js` para detectar timeouts y mostrar mensaje claro de reintento.
- En `InicioAdministrador.vue` se cambió la carga a `Promise.allSettled` para permitir carga parcial controlada.
- En `InicioDirector.vue` se optimizó rendimiento:
  - Período inicial en `YTD`.
  - Opción histórica acotada a 5 años.
  - Muestreo de series largas para gráficas.
  - Límite de casinos en gráfica de barras (top 20) para evitar saturación visual.

## Archivos modificados
- `Vue/src/service/api.js`
- `Vue/src/service/notificacionesApi.js`
- `Vue/src/views/pages/InicioAdministrador.vue`
- `Vue/src/views/pages/InicioDirector.vue`
- `docs/frontend/03_servicios_api.md`
- `docs/frontend/05_vistas_administrativas.md`

## Impacto
- Se reduce drásticamente el riesgo de pantallas colgadas por peticiones sin respuesta.
- El usuario recibe errores accionables (timeout) en lugar de espera indefinida.
- Los dashboards de inicio mantienen continuidad operativa aun con fallas parciales de backend.
- Mejora perceptible de rendimiento en carga inicial del panel directivo.

## Lecciones aprendidas
- En tableros con múltiples fuentes, preferir `Promise.allSettled` cuando el objetivo es continuidad parcial.
- Definir timeout explícito en capa HTTP es obligatorio en producción para evitar esperas silenciosas.
- Las gráficas deben aplicar límites/muestreo cuando el rango temporal crece para proteger la fluidez del frontend.
