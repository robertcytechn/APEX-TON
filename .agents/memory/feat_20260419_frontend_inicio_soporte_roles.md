# feat_20260419_frontend_inicio_soporte_roles

## Problema
- La ruta de inicio mostraba una plantilla vacía para perfiles directivos (Director/Administrador).
- El menú lateral exponía una entrada de "Plantilla vacía" en Principal.
- La sección Soporte apuntaba a "Página no encontrada" y no existía una vista real de contacto técnico.
- Se requería una experiencia de inicio específica por rol y un tablero directivo con gráficas por casino (recaudado hasta la fecha).

## Solución
- Se implementó un enrutador de inicio por rol con `Inicio.vue` para delegar en:
  - `InicioOperativo.vue` (Contador/Gerente).
  - `InicioDirector.vue` (Director) con gráficas de recaudación por casino y tendencia diaria.
  - `InicioAdministrador.vue` (Administrador/Superusuario) con tablero de control tipo modo dios.
- Se eliminó la antigua vista `Empty.vue` y se removió su acceso desde menú/rutas.
- Se creó `SoporteTecnico.vue` con datos de contacto del creador (WhatsApp, llamadas y correos).
- Se restringió la ruta de soporte a `DIRECTOR`, `ADMINISTRADOR` y `SUPERUSUARIO` desde router y menú.
- Se actualizó documentación frontend para reflejar la nueva navegación y vistas.

## Archivos modificados
- `Vue/src/router/index.js`
- `Vue/src/layout/AppMenu.vue`
- `Vue/src/views/pages/Inicio.vue`
- `Vue/src/views/pages/InicioOperativo.vue`
- `Vue/src/views/pages/InicioDirector.vue`
- `Vue/src/views/pages/InicioAdministrador.vue`
- `Vue/src/views/pages/SoporteTecnico.vue`
- `Vue/src/views/pages/Empty.vue` (eliminado)
- `docs/frontend/01_arquitectura_y_navegacion.md`
- `docs/frontend/05_vistas_administrativas.md`

## Impacto
- Mejora la experiencia de inicio para perfiles estratégicos y elimina pantallas placeholder de cara a producción.
- Alinea la navegación con control de acceso por rol en frontend y guard global de router.
- Reduce riesgo de confusión operativa al reemplazar enlaces rotos/no funcionales en Soporte.

## Lecciones aprendidas
- En pantallas de producción, cualquier ruta placeholder debe retirarse del menú aun si permanece como fallback técnico.
- Para tableros directivos, conviene reutilizar endpoints analíticos existentes (`estado-resultados/estadisticas`) antes de crear APIs nuevas.
- Es importante validar build al final para detectar rupturas de rutas dinámicas o imports perezosos.
