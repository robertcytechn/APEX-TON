# feat_20260420_ambas_tickets_soporte_seguimiento_admin

## Problema
El formulario de soporte ya enviaba correo, pero no existía persistencia estructurada del ticket ni una bandeja administrativa para dar seguimiento operativo. Además, faltaba el acuse por correo al usuario que levantaba el ticket con su folio.

## Solución
Se creó el modelo `TicketSoporteTecnico` para almacenar snapshot completo del ticket (usuario, datos del formulario, estado de seguimiento y estatus de correos). Se extendió el endpoint de creación para guardar el ticket, enviar correo al canal de soporte y enviar correo de confirmación al usuario con folio. También se agregaron endpoints administrativos para listar y actualizar tickets, y una vista frontend exclusiva de administrador para gestionar estados y notas de seguimiento.

## Archivos modificados
- `DJANGO/usuarios/models.py`
- `DJANGO/usuarios/migrations/0004_ticketsoportetecnico.py`
- `DJANGO/usuarios/serializers.py`
- `DJANGO/usuarios/views.py`
- `DJANGO/usuarios/admin.py`
- `DJANGO/usuarios/tests.py`
- `Vue/src/service/soporteTecnicoServicio.js`
- `Vue/src/views/admin/SoporteTecnicoAdmin.vue`
- `Vue/src/router/index.js`
- `Vue/src/layout/AppMenu.vue`
- `docs/backend/01_usuarios.md`
- `docs/frontend/01_arquitectura_y_navegacion.md`
- `docs/frontend/03_servicios_api.md`
- `docs/frontend/05_vistas_administrativas.md`

## Impacto
- Soporte técnico deja de ser solo correo y pasa a un flujo trazable con historial y seguimiento.
- Administración obtiene una bandeja central para cerrar o descartar tickets con notas.
- Usuarios reciben acuse automático con folio para continuidad de atención.
- Se fortalecen pruebas backend del módulo usuarios para cubrir creación y seguimiento de tickets.

## Lecciones aprendidas
- En flujos de soporte, persistir snapshot del usuario y del formulario evita pérdida de contexto al cambiar datos de cuenta.
- El envío de correo no debe ser el único canal de trazabilidad; el modelo de ticket permite auditoría y reintentos.
- Mantener estados de seguimiento explícitos simplifica la operación diaria del equipo administrativo.
