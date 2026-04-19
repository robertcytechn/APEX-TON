# Reglas de roles, permisos y cierres

## 1) Matriz de roles

- **ADMINISTRADOR**: control total; puede reabrir dias cerrados.
- **GERENTE**: permisos operativos equivalentes a CONTADOR (estado actual).
- **CONTADOR**: captura operativa diaria en pestañas habilitadas.
- **DIRECTOR**: enfoque de lectura/reporteria; sin captura operativa diaria.

## 2) Permisos

- La asignacion de permisos es por rol.
- Evitar permisos directos por usuario fuera del modelo definido.

## 3) Horario operativo

- La ventana de escritura depende de `HORARIO_APERTURA` y `HORARIO_CIERRE` en configuraciones globales.
- Fuera de ventana: lectura permitida, escrituras bloqueadas.

## 4) Cierre diario y mensual

- Cierre diario bloquea edicion de movimientos del dia.
- Solo ADMINISTRADOR puede reabrir un dia cerrado.
- Cierre mensual genera snapshot historico inmutable en libro de resultados.

## 5) Regla de dia contable

- El sistema opera con dia contable T-1.
- No permitir logicas frontend que contradigan esa regla.
