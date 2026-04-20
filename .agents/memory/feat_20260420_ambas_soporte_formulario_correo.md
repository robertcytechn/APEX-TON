# feat_20260420_ambas_soporte_formulario_correo

## Problema
Se requería transformar la vista de soporte técnico en un flujo funcional de reporte de incidencias: cualquier usuario con sesión activa debía poder capturar un ticket con selectores y detalle libre, y enviar un correo real con copia automática a un segundo destinatario.

## Solución
Se implementó un endpoint autenticado en `usuarios` para recibir solicitudes de soporte, validar campos guiados y enviar correo vía SMTP a `robert-cyby@hotmail.com` con copia a `robertot@gbentretenimiento.com`. En frontend se creó servicio dedicado y se rediseñó `SoporteTecnico.vue` con formulario completo, validaciones de cliente y estados de envío, incluyendo nombre y correo del usuario autenticado como datos de contexto.

## Archivos modificados
- `DJANGO/usuarios/serializers.py`
- `DJANGO/usuarios/views.py`
- `DJANGO/usuarios/tests.py`
- `Vue/src/service/soporteTecnicoServicio.js`
- `Vue/src/views/pages/SoporteTecnico.vue`
- `Vue/src/router/index.js`
- `Vue/src/layout/AppMenu.vue`
- `docs/backend/01_usuarios.md`
- `docs/frontend/01_arquitectura_y_navegacion.md`
- `docs/frontend/03_servicios_api.md`

## Impacto
- Se habilita un canal operativo de soporte para todos los usuarios autenticados.
- El backend de usuarios agrega una acción nueva de negocio para envío de tickets por correo.
- El menú y los guards de ruta dejan de restringir soporte solo a director/admin.
- Se agregan pruebas para validar autenticación y envío de correo del endpoint.

## Lecciones aprendidas
- Para flujos transversales de soporte conviene centralizar validaciones en serializer y no en la vista.
- Un endpoint de soporte requiere trazabilidad mínima (folio) para seguimiento posterior.
- Al abrir acceso de una vista por rol, hay que alinear router, menú y texto UX en el mismo cambio.
