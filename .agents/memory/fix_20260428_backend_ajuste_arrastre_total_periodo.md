# Fix: Ajuste contable ARRASTRE DE MOVIMIENTOS PREVIOS no sumaba a total_ingresos_rango / total_egresos_rango

**Fecha:** 2026-04-28  
**Autor:** Jose Roberto Tamayo Montejano  
**Versión:** v0.0.14

---

## Problema

El TOTAL DEL PERIODO del correo diario y del endpoint `libro-operativo` desfilaba respecto a la suma de las filas individuales. Específicamente, la fila de ajuste contable **"ARRASTRE DE MOVIMIENTOS PREVIOS"** se mostraba en el libro con su monto (ej. egreso $16.00) pero **no sumaba** a `total_ingresos_rango` / `total_egresos_rango`, haciendo que:

- La tarjeta de resumen (ingresos/egresos) mostrara un total incorrecto.
- La fila TOTAL DEL PERIODO tuviera un desfase igual al monto del arrastre.
- El email/PDF/Excel no fueran congruentes con la página de Reporte Diario del frontend.

## Ejemplo concreto

| Concepto                       | Ingreso | Egreso   |
|-------------------------------|---------|----------|
| SALDO INICIAL                 | -       | -        |
| ARRASTRE DE MOVIMIENTOS PREVIOS | -       | **16.00** |
| FONDOS FIJOS                  | -       | 430,000.00 |
| POR COMPROBAR                 | -       | 8,000.00 |
| DOLARES                       | -       | 6,600.00 |
| **TOTAL DEL PERIODO (antes)** | 0.00    | **444,600.00** ❌ |
| **TOTAL DEL PERIODO (después)**| 0.00    | **444,616.00** ✅ |

Desfase: **$16.00** (exactamente el arrastre no contabilizado).

## Solución

En `DJANGO/reportes_diarios/views.py`, función `_construir_datos_libro_operativo_detallado`, bloque que genera la fila de arrastre (líneas ~1171-1178), se agregaron las líneas que acumulan el monto del arrastre a los totales del rango:

```python
if neto_admin_previo != 0:
    saldo_acumulado += neto_admin_previo
    if neto_admin_previo > 0:
        total_ingresos_rango += neto_admin_previo
    else:
        total_egresos_rango += abs(neto_admin_previo)
    filas.append({
        ...
    })
```

## Archivos modificados

- `DJANGO/reportes_diarios/views.py` — `_construir_datos_libro_operativo_detallado`

## Impacto

- Correo diario: resumen, tabla principal y adjuntos PDF/Excel ahora cuadran.
- Endpoint `libro-operativo`: mismo fix, mismo punto de verdad.
- Frontend `ReporteDiario.vue`: recibe datos correctos desde la API.

## Lecciones aprendidas

1. Cada ajuste contable que se dibuja como fila visible **debe** reflejarse en los acumulados de ingresos/egresos del periodo.
2. Si se usa una función helper (`_agregar_fila_operacion`) para filas normales, verificar que los ajustes inline hagan exactamente lo mismo.
3. Al probar, comparar siempre: suma de filas vs totales del resumen vs TOTAL DEL PERIODO.
