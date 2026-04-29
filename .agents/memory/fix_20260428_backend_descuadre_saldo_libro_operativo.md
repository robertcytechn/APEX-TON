# Fix · Descuadre del Saldo Final entre Reporte Diario y Captura Operativa Detallada

**Fecha:** 2026-04-28
**Capa:** backend
**Versión:** v0.0.12

## Problema

El "Saldo final" mostrado por la página **Reporte Diario** (endpoint
`GET /reportes-diarios/libro-operativo/`) no coincidía con el "Saldo acumulado al día"
mostrado por **Captura Operativa Detallada** (endpoint
`GET /reportes-diarios/saldo-inicial-categoria/`) para el mismo casino y día.

Caso reportado:
- Casino Crown City, mismo día contable.
- Reporte Diario → `334,378.42`
- Captura Operativa Detallada → `332,660.19` *(valor correcto según negocio)*
- Diferencia: `1,718.23`

## Causa raíz

En `libro_operativo` los ajustes contables (sobrantes, pérdidas, por comprobar,
dólares) se calculaban con la ventana `[fecha_inicio, fecha_fin]`, mientras que
Captura Operativa Detallada los calculaba con el **mes completo**. Cuando el
rango consultado no iniciaba el día 1 del mes, los movimientos de esas
categorías ocurridos entre el día 1 del mes y `fecha_inicio − 1` quedaban
**completamente ignorados** en el saldo final. Lo mismo ocurría con los
movimientos de Administración previos al rango, que tampoco se aplicaban al
saldo acumulado mostrado en pantalla.

## Solución aplicada

Se eligió un fix mínimo que **preserva la narrativa visual original** (cada
fila — `FONDOS FIJOS`, `FALTANTES`, `SOBRANTES`, `POR COMPROBAR`, `DOLARES` —
sigue descontando o sumando al saldo acumulado, como antes) y al mismo tiempo
corrige el descuadre.

### Cambios en `DJANGO/reportes_diarios/views.py`

1. **`_calcular_saldo_inicial_libro_operativo`**: se mantiene devolviendo el
   saldo bruto mensual de Administración registrado en
   `SaldoInicialCategoriaMensual` (sin aplicar ajustes contables). Esto deja
   intacto el valor mostrado en la fila `SALDO INICIAL` y los campos
   `saldo_arrastre_inicio` / `saldo_arrastre_fin` de los reportes abiertos.

2. **`libro_operativo` (acción del ViewSet)**:
   - Las llamadas a `_calcular_totales_categoria_rango` para sobrantes,
     pérdidas, por comprobar y dólares ahora usan la ventana
     `[día 1 del mes de fecha_fin, fecha_fin]` en lugar de
     `[fecha_inicio, fecha_fin]`. Así se incluyen los ajustes ocurridos antes
     del rango consultado.
   - Se restablecieron los `total_acumulado_X = saldo_inicial_X_mensual +
     movs_X_(día 1 → fecha_fin)`, alineando la fórmula con la de
     `_calcular_componentes_saldo_inicial_administracion` usada por Captura
     Operativa Detallada.
   - Se calcula `neto_admin_previo = ingresos_admin_(día 1 → fecha_inicio − 1)
     − egresos_admin_(día 1 → fecha_inicio − 1)`. Si es distinto de cero, se
     inserta una nueva fila **`MOVIMIENTOS ADMIN PREVIOS AL RANGO`** justo
     después del `SALDO INICIAL` que ajusta el saldo acumulado pero **no se
     suma** a `total_ingresos_rango` / `total_egresos_rango` (porque no
     pertenece al rango consultado).
   - El array `ajustes_contables` vuelve a su forma original con
     `('FONDOS FIJOS', fondos_fijos_sucursal, 'EGRESO')` y los demás conceptos
     usando `total_acumulado_X`. Cada fila descuenta o suma al saldo como en
     la versión previa al bug.

### Fórmula resultante

```
saldo_final = saldo_base_admin_mes
            + neto_admin_(día 1 → fecha_inicio − 1)        ← fila MOVIMIENTOS ADMIN PREVIOS
            + admin_movs_RANGO                             ← filas movimientos del rango
            − fondos_fijos                                 ← fila FONDOS FIJOS
            − total_acumulado_perdidas_(1 → fecha_fin)     ← fila FALTANTES
            + total_acumulado_sobrantes_(1 → fecha_fin)    ← fila SOBRANTES
            − total_acumulado_por_comprobar_(1 → fecha_fin)← fila POR COMPROBAR
            − total_acumulado_dolares_(1 → fecha_fin)      ← fila DOLARES

= saldo_base_admin_mes
  + admin_movs_(día 1 → fecha_fin)
  − fondos_fijos
  − total_acumulado_dolares_(1 → fecha_fin)
  − total_acumulado_por_comprobar_(1 → fecha_fin)
  − total_acumulado_perdidas_(1 → fecha_fin)
  + total_acumulado_sobrantes_(1 → fecha_fin)
```

Esta fórmula es algebraicamente equivalente al `saldo_final_acumulado`
expuesto por `saldo-inicial-categoria` cuando no existen movimientos
posteriores a `fecha_fin` en el mes (caso típico de consulta T-1).

## Archivos modificados

- `DJANGO/reportes_diarios/views.py`
- `.agents/versionamiento.md`
- `.agents/memory/fix_20260428_backend_descuadre_saldo_libro_operativo.md` *(este archivo)*

## Impacto

- **Reporte Diario** coincide con Captura Operativa Detallada para cualquier
  rango dentro del mes.
- La narrativa visual del libro operativo se conserva: cada ajuste contable
  sigue afectando el saldo en pantalla.
- Los reportes diarios `ABIERTO` mantienen la sincronización de
  `saldo_arrastre_inicio` / `saldo_arrastre_fin` con el saldo bruto
  mensual + movimientos del día (sin cambios respecto a versiones anteriores).
- Los reportes `CERRADO` no se modifican.
- No se ejecutaron migraciones ni cambios en BD.

### Side-effects a vigilar

- Cuando `fecha_inicio` no sea el día 1 del mes, aparece la nueva fila
  `MOVIMIENTOS ADMIN PREVIOS AL RANGO`. Validar con usuarios de negocio que
  el wording sea claro; ajustar etiqueta si lo solicitan.
- Si el rango cruza varios meses (caso poco frecuente), los `total_acumulado_X`
  toman el mes de `fecha_fin`. Para escenarios de cierre fiscal multi-mes,
  revisar caso por caso.

## Lecciones aprendidas

- Cuando dos endpoints calculen "lo mismo" para el usuario, deben **compartir
  ventana temporal** además de fórmula. Aquí el bug era simplemente que
  `libro_operativo` usaba `[fecha_inicio, fecha_fin]` cuando debía usar
  `[día 1 del mes, fecha_fin]`.
- Antes de mover el "saldo inicial" de un endpoint, evaluar el costo en
  narrativa visual: el usuario puede preferir ver cada concepto descontar
  explícitamente del saldo, aunque algebraicamente equivalga a sumarlo todo
  al inicio.
