# refactor_20260420_frontend_saldo_diario_sin_duplicado

## Problema
La tarjeta de saldo diario mostraba simultáneamente "resultado neto del día" y "saldo final del día" con saldo inicial diario fijo en cero, por lo que ambos valores eran idénticos y generaban ruido visual.

## Solución
Se eliminó la métrica "saldo final del día" en la tarjeta diaria de `CapturaOperativaCategoria.vue`, conservando ingresos, egresos y resultado neto del día.
También se ajustó el layout de la cuadrícula para tres bloques y se retiró el `computed` no utilizado.

## Archivos modificados
- `Vue/src/views/contador/CapturaOperativaCategoria.vue`
- `docs/frontend/04_vistas_operativas.md`
- `.agents/versionamiento.md`

## Impacto
- Menor redundancia en UI operativa.
- Claridad de lectura para usuario capturista.
- Sin impacto en API, backend o persistencia de datos.

## Lecciones aprendidas
- Cuando una métrica derivada sea matemáticamente equivalente por definición operativa, conviene mostrar una sola para reducir carga cognitiva.
- Si en el futuro se introduce saldo inicial diario distinto de cero, se debe revaluar exponer nuevamente el saldo final diario.
