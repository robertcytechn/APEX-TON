# feat_20260420_ambas_formula_saldo_inicial_administracion

## Problema
La tarjeta mensual de captura operativa mostraba `saldo final del mes` en una posición donde negocio requería visualizar fondos fijos para Administración, y el saldo inicial de Administración no integraba una fórmula operativa con Sobrantes/Pérdidas/Por Comprobar.
Además, el saldo inicial mostrado en Reporte Diario no estaba alineado explícitamente con esa misma regla de Administración.

## Solución
Se implementó en backend una fórmula especial para la categoría Administración:
`saldo_inicial_administracion = saldo_inicial_base_mes + fondos_fijos_sucursal + resultado_sobrantes - resultado_perdidas - egresos_por_comprobar`.
Esta lógica se aplicó en el endpoint `saldo-inicial-categoria` y en el cálculo de `saldo_inicial` del `libro-operativo`.
En frontend de captura operativa, la quinta tarjeta mensual ahora muestra `Fondos fijos de la sucursal` para Administración y consume el saldo inicial ajustado entregado por backend.

## Archivos modificados
- `DJANGO/reportes_diarios/views.py`
- `DJANGO/reportes_diarios/tests.py`
- `Vue/src/views/contador/CapturaOperativaCategoria.vue`
- `docs/backend/03_operacion_diaria.md`
- `docs/frontend/04_vistas_operativas.md`
- `.agents/versionamiento.md`

## Impacto
- Unifica criterio de saldo inicial para Administración entre captura y reporte diario.
- Mantiene intacto el comportamiento de categorías no-Administración.
- Introduce pruebas automatizadas específicas para la fórmula de Administración y su efecto en libro operativo.

## Lecciones aprendidas
- Reglas contables especiales deben centralizarse en helpers backend reutilizables para evitar divergencia entre vistas.
- Cuando una métrica visual cambia por negocio (ej. reemplazar saldo final por fondos fijos), conviene exponer explícitamente el campo en la API para evitar cálculos duplicados en cliente.
