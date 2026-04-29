version_actual: v0.0.16

## v0.0.16 — 2026-04-29
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se ajusto el correo diario para adjuntar reportes del mes en curso (dia 1 al dia contable) y se actualizo el texto de periodo en correo/PDF.
**Capa(s):** backend
**Detalle:** `.agents/memory/feat_20260429_backend_correo_diario_mes_corriente.md`

## v0.0.15 — 2026-04-28
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se ajusto el formato del correo diario y sus adjuntos: cuerpo con resumen ejecutivo, Excel con hoja principal que replica el reporte diario y bancos al final, y hojas posteriores por categoria.
**Capa(s):** backend
**Detalle:** `.agents/memory/fix_20260428_backend_correo_reporte_diario_formato.md`

## v0.0.14 — 2026-04-28
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se corrigió descuadre en TOTAL DEL PERIODO del correo diario: el ajuste contable "ARRASTRE DE MOVIMIENTOS PREVIOS" no sumaba su monto a total_ingresos_rango / total_egresos_rango, haciendo que el resumen del email desfilara vs las filas individuales.
**Capa(s):** backend
**Detalle:** `.agents/memory/fix_20260428_backend_ajuste_arrastre_total_periodo.md`

## v0.0.13 — 2026-04-28
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Refactor completo del sistema de generacion de correos de resumen diario ejecutivo: helpers reutilizables para libro operativo detallado, nuevos generadores PDF/Excel multi-pagina/hoja con detalle por categoria y bancos, plantillas HTML/TXT enriquecidas, y modo --solo-generar para revision sin envio SMTP.
**Capa(s):** ambas
**Detalle:** `.agents/memory/refactor_20260428_ambas_correo_diario_libro_detallado.md`

## v0.0.12 — 2026-04-28
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se corrigió el descuadre del Saldo final del Reporte Diario respecto a Captura Operativa Detallada cambiando la ventana de los ajustes contables del rango `[fecha_inicio, fecha_fin]` a `[día 1 del mes, fecha_fin]` y agregando una fila "MOVIMIENTOS ADMIN PREVIOS AL RANGO" que ajusta el saldo cuando el rango no inicia el día 1 del mes. Se preserva la narrativa visual original donde cada concepto (FONDOS FIJOS, FALTANTES, SOBRANTES, POR COMPROBAR, DOLARES) descuenta o suma al saldo acumulado.
**Capa(s):** backend
**Detalle:** `.agents/memory/fix_20260428_backend_descuadre_saldo_libro_operativo.md`

## v0.0.11 — 2026-04-21
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se actualizó la fórmula del saldo inicial de Administración para incluir Dólares y se eliminó el bloqueo que impedía la edición del saldo inicial manual en categorías operativas.
**Capa(s):** ambas
**Detalle:** `.agents/memory/feat_20260421_ambas_formula_dolares_y_desbloqueo_saldo_inicial.md`

## v0.0.10 — 2026-04-21
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se agregó una vista de consulta detallada de captura operativa (solo lectura) para Director/Administrador con filtros por casino, día contable y categoría, además de su integración en rutas y menú.
**Capa(s):** frontend
**Detalle:** `.agents/memory/feat_20260421_frontend_consulta_captura_operativa_director_admin.md`

## v0.0.9 — 2026-04-21
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Se endureció el cierre automático con gracia para cerrar solo reportes con movimientos reales superiores a $10.00, se aseguró el envío de correo post-commit en cierres manuales/automáticos y se amplió la trazabilidad de logs por etapa.
**Capa(s):** backend
**Detalle:** `.agents/memory/fix_20260421_backend_cierre_gracia_umbral_correo.md`

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
