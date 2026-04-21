# feat_20260420_frontend_calculadora_saldos_reactiva_captura

## Problema
En la vista de captura operativa por categoría, el usuario necesitaba usar una calculadora externa para sumar ingresos/egresos del día y para validar el impacto inmediato en los saldos mensuales, porque la interfaz no reaccionaba en tiempo real con los montos que iba capturando.

## Solución
Se agregó una tarjeta nueva de saldo diario reactivo en `CapturaOperativaCategoria.vue` que calcula en vivo ingresos, egresos, resultado neto y saldo final del día contable.
También se actualizó la tarjeta de saldo mensual para que sus montos reaccionen en frontend con el delta de la captura activa, sin recargar la página.
Para evitar doble conteo, se implementó una línea base del día persistido al momento de carga y se aplica solo la diferencia de la edición actual.
No se realizaron cambios de backend ni persistencia adicional en base de datos.

## Archivos modificados
- `Vue/src/views/contador/CapturaOperativaCategoria.vue`
- `docs/frontend/04_vistas_operativas.md`
- `.agents/versionamiento.md`

## Impacto
- Mejora inmediata de UX para CONTADOR y GERENTE en captura diaria.
- Menor probabilidad de errores manuales al cuadrar montos.
- Sin impacto en contratos API, modelos de datos ni tareas asíncronas.

## Lecciones aprendidas
- Cuando un resumen depende de entradas dinámicas por fila, conviene calcular con estado local y separar claramente el dato base persistido del delta editable.
- La lógica reactiva de frontend puede resolver necesidades operativas rápidas sin sobrecargar backend, siempre que el alcance sea referencial y no contable oficial.
