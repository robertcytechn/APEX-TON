# Task: Inicio por rol y soporte técnico

## Objetivo
Eliminar plantillas vacías en Inicio/Soporte y entregar vistas funcionales por rol para producción.

## Fases
- [x] Fase 1: Investigación de rutas, menú, roles y endpoints
- [x] Fase 2: Diseño e implementación de Inicio por rol
- [x] Fase 3: Implementación de soporte técnico con permisos
- [x] Fase 4: Ajustes de router y menú lateral
- [x] Fase 5: Documentación y validación build

## Decisiones
| Decisión | Rationale | Fecha |
|----------|-----------|------|
| Usar endpoint estado-resultados/estadisticas para dashboard director | Ya entrega series por sucursal para recaudado hasta fecha y evita duplicar backend | 2026-04-19 |
| Separar dashboards por componentes de página | Mantiene mantenibilidad y evita archivo monolítico | 2026-04-19 |

## Errores Encontrados
| Error | Intento | Resolución |
|-------|---------|------------|
| `npm run build` ejecutado fuera de `Vue/` | Se lanzó el comando en raíz y falló por script inexistente | Se ejecutó build dentro de `Vue/` y compiló correctamente |
