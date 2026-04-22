# feat_20260421_ambas_formula_dolares_y_desbloqueo_saldo_inicial

## Problema
1. La fórmula de saldo inicial de Administración requería ser ajustada a: `saldo_inicial = - fondos_fijos - dolares - por_comprobar - perdidas + sobrantes`.
2. Existía un bloqueo al indicar un saldo inicial a una categoría operativa, impidiendo su modificación manual en el frontend una vez guardado, lo cual limitaba pruebas y operación.

## Solución
1. Se incorporó el patrón `DOLARES` en el backend para obtener el resultado neto en el mes o rango de esta categoría. Se ajustó `_calcular_componentes_saldo_inicial_administracion` restando los dólares y modificando los signos para alinearse a la nueva fórmula.
2. Se modificó el endpoint `establecer_saldo_inicial_categoria` permitiendo actualizar el registro existente si se requiere modificar manualmente, y se cambió `bloqueado_edicion` a `False` por defecto. En frontend, se reemplazó el uso de `requiereCapturaManualSaldoInicial` por `permiteCapturaManualSaldoInicial` para mantener visible la entrada de texto incluso si el saldo inicial ya fue definido, permitiendo enviar la actualización al backend.

## Archivos modificados
- `DJANGO/reportes_diarios/views.py`
- `Vue/src/views/contador/CapturaOperativaCategoria.vue`

## Impacto
- El cálculo de la categoría especial de Administración tomará en cuenta los movimientos en dólares y deducirá los fondos fijos en lugar de sumarlos.
- Los usuarios con permisos para capturar el saldo inicial manual podrán sobrescribirlo o actualizarlo sin enfrentarse al candado de sólo lectura, mejorando la usabilidad y soporte a errores de captura.

## Lecciones aprendidas
- La reutilización del campo `permite_captura_manual` del endpoint simplifica la validación del frontend y evita dependencias en múltiples flags para habilitar o deshabilitar bloques UI.
- Actualizar componentes visuales desde propiedades computadas (`computed`) ayuda a mantener la interfaz reactiva cuando se combinan requisitos de negocio como el desbloqueo de saldos iniciales manuales.
