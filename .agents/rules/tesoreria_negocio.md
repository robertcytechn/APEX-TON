# Reglas de negocio de tesoreria (APEX-TON)

## 1) Objetivo funcional

El sistema controla flujo diario de caja por sucursal y consolida resultados en tiempo real e historico mensual.
No es un ERP contable general; es control operativo de tesoreria.

## 2) Regla de signo operativo

- Dinero que sale de caja hacia banco: **EGRESO**
- Dinero que ingresa de banco/surtido a sala: **INGRESO**

## 3) Estructura de captura

- Categoria operativa (pestana) define el bloque funcional.
- Concepto define el movimiento especifico.
- Cada concepto debe mapearse a un `rubro_contable`.
- Campos extra de captura se guardan como detalle parametrizado/snapshot cuando aplique.

## 4) Reglas criticas de tiempo

- El dia contable opera con logica T-1.
- El backend controla fecha contable y cierre; frontend no debe imponer fecha manual para romper la regla.

## 5) Reglas de consolidacion

- Estado de resultados del mes en curso: agregado en tiempo real desde movimientos diarios.
- Mes cerrado: lectura desde snapshot historico (sin recalculo retroactivo).
- Cambios de tipo de cambio/configuracion futura no alteran cierres historicos.
