# Arquitectura Lógica de la Base de Datos

## Tablas Globales Maestras
Tablas pilares del sistema global (no dependen de lógicas divisionales):
- `configuraciones_globales`
- `rubro_contable`
- `roles`
- `permisos`
- `sucursales`
- `modelobase` (Abstracto)
- `fondos_fijos`

## Relaciones Fundamentales
- **Usuarios:** Hereda de `modelobase` y se relaciona con `sucursal` y `roles`.
- **Preferencias:** `configuraciones_de_usuario` (hereda de `modelobase`, relacionada con `usuarios`).
- **Sucursales:** Hereda de `modelobase` e incluye conexión a `fondos_fijos`.
- **Contabilidad:** `rubro_contable` es global para homologar ingresos/egresos. `fondos_fijos` es estrictamente independiente por sucursal.
