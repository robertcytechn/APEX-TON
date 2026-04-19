# Control Operacional de Tesorería (Reglas de Negocio)

El objetivo es estandarizar la lógica del archivo matriz `CAJA MUESTRA.xlsx`. El sistema es un registro de transacciones diarias para auditar dinero físico en sala, no un software contable estricto.

**Contexto de Flujo:**
- Dinero a bancos $\rightarrow$ **Egreso** (sale de caja de sala).
- Sala surtida desde bancos $\rightarrow$ **Ingreso**.

## Organización por Pestañas
El flujo se categoriza en "Pestañas":
`ADMINISTRACION`, `BOOK`, `BILLPOCKET`, `BAHIA BANORTE`, `BANORTE AHIS`, `BBVB BANCOMER`, `DOLARES`, `PERDIDAS`, `PERMISO`, `SOBRANTES`, `POR COMPROBAR`, `MAQUINAS`, `CAJA CHICA MORELIA`, `COMPARATIVO`, `PRESUPUESTO`, `MAQUINEROS`, `JUEGO VIVO`, `F. fijos`.

## Conceptos y Rubros
- **Concepto:** Nomenclatura de movimientos específicos (ej. "VENTA DE CAFE").
- **Relación:** Cada concepto pertenece a una **única pestaña** y está conectado al `rubro_contable` global (ej. "VENTAS_BEBIDAS").

## Parametrización y Datos
- **Contexto:** Las pestañas documentan responsable, origen y monto (ej. Pestaña `Sobrantes`).
- **Tipos de Datos:** Usar siempre **decimales** para representar valores monetarios.

## Estado de Resultados
El objetivo final es consolidar ingresos y egresos en el **Estado de Resultados** de forma autónoma y en tiempo real.
