version_actual: v0.0.8

## v0.0.8 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se implementó regla especial de saldo inicial para la categoría Administración (fondos fijos + ajustes por Sobrantes/Pérdidas/Por Comprobar), aplicada en captura operativa y en el saldo inicial del libro diario.
**Capa(s):** ambas
**Detalle:** `.agents/memory/feat_20260420_ambas_formula_saldo_inicial_administracion.md`

## v0.0.7 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se eliminó la métrica redundante de saldo final diario en captura operativa, conservando resultado neto del día como indicador único.
**Capa(s):** frontend
**Detalle:** `.agents/memory/refactor_20260420_frontend_saldo_diario_sin_duplicado.md`

## v0.0.6 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se implementó calculadora reactiva de saldos diarios y ajuste en vivo de saldos mensuales dentro de la captura operativa por categoría, sin persistencia adicional en backend.
**Capa(s):** frontend
**Detalle:** `.agents/memory/feat_20260420_frontend_calculadora_saldos_reactiva_captura.md`

## v0.0.5 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Refactor integral de textos visibles al usuario final en todo el frontend para elevar el tono a un registro profesional e institucional en español mexicano correcto.
**Capa(s):** frontend
**Detalle:** `.agents/memory/refactor_20260420_frontend_textos_profesionales.md`


## v0.0.1 — 2026-04-19
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se reemplazaron plantillas vacías de inicio y soporte por vistas funcionales por rol, incluyendo tablero directivo con gráficas y página de soporte técnico restringida por permisos.
**Capa(s):** frontend
**Detalle:** `.agents/memory/feat_20260419_frontend_inicio_soporte_roles.md`

## v0.0.2 — 2026-04-19
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se corrigieron cargas lentas/colgadas agregando timeout global de API, mensajes de timeout claros y estrategias de carga parcial/optimizada en dashboards de inicio.
**Capa(s):** frontend
**Detalle:** `.agents/memory/fix_20260419_frontend_cargas_timeout_dashboard.md`

## v0.0.3 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se implementó flujo completo de soporte técnico con formulario para usuarios autenticados, endpoint backend de envío de correo y apertura de acceso en menú/rutas.
**Capa(s):** ambas
**Detalle:** `.agents/memory/feat_20260420_ambas_soporte_formulario_correo.md`

## v0.0.4 — 2026-04-20
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se agregó persistencia de tickets de soporte, acuse por correo al solicitante y bandeja administrativa para seguimiento/cierre de eventos.
**Capa(s):** ambas
**Detalle:** `.agents/memory/feat_20260420_ambas_tickets_soporte_seguimiento_admin.md`
