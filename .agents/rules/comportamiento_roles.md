# Control Histórico y Comportamiento

## Control Histórico
- **Libro de Estado de Resultados:** Registro histórico mensual de movimientos en la sala de juegos.
- **Integridad de Datos:** Si se modifica el tipo de cambio en `configuraciones_globales`, **no se deben modificar los registros históricos**, ya que deben conservar el valor vigente al momento de la transacción.

## Roles y Permisos
- **CONTADOR:** Encargado de llenar campos en pestañas históricas (`POR COMPROBAR`, `MAQUINAS`, `CAJA CHICA MORELIA`, `PRESUPUESTO`, `MAQUINEROS`, `JUEGO VIVO`).
- **GERENTE:** Permisos equivalentes al Contador (actualmente).
- **DIRECTOR:** Solo lectura de reportes (Estado de Resultados, comparativos por periodo, filtros personalizados). No puede editar pestañas históricas. Puede ajustar `configuraciones_globales` y `fondos_fijos` por casino.
- **ADMINISTRADOR:** Control total del sistema.

## Reglas Operativas
- **Horarios:** En `configuraciones_globales` existen los campos `HORARIO_APERTURA` y `HORARIO_CIERRE`. Fuera de este rango, las pestañas no pueden modificarse.
- **Cierre de Día:** El sistema debe cerrar el día creando/cerrando el histórico diario. Al finalizar el mes, cierra el histórico de estado de resultados.
- **Día Contable:** Se define como el día anterior (ej. si hoy es 20 de marzo, el día contable es 19 de marzo).
