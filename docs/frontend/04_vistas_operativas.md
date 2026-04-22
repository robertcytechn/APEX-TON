# Documentación del Frontend: Vistas Operativas

Este módulo cubre la pantalla de trabajo diario principal utilizada por los roles `CONTADOR` y `GERENTE`, así como los reportes de consulta operativa. El enfoque técnico aquí es el **manejo de formularios altamente dinámicos y autoguardado**.

---

## 1. Captura Operativa Diaria (`views/contador/CapturaOperativaCategoria.vue`)

Este componente es el más extenso y crítico del sistema operativo. Genera una interfaz que cambia de forma dinámica según la categoría (Pestaña) seleccionada.

### 1.1 Estado Reactivo Complejo (Autoguardado)
Dado que los contadores pueden capturar decenas de movimientos por categoría, la pantalla **no tiene un botón general de "Guardar"**. En su lugar, implementa un modelo de autoguardado por fila (Drafting):
- **Diccionario de Capturas (`capturasPorConcepto`)**: Construye un estado reactivo en memoria (`reactive({})`) por cada fila visible (concepto).
- **Firma de Estado (`construirFirmaEstado`)**: Genera un hash/JSON del valor de la fila (Monto, Detalles, Notas).
- **Debounce de Red (`programarGuardado`)**: Al detectar un cambio en la firma, espera `1000ms` sin actividad antes de enviar el `POST`/`PUT` en segundo plano a la API de `capturaOperativaServicio`.

### 1.2 Reglas de Bloqueo por Ventana Horaria en Tiempo Real
El componente lee `HORARIO_APERTURA` y `HORARIO_CIERRE` de las configuraciones globales.
- Un ciclo interno (`setInterval`) actualiza `minutosActualesCliente` cada segundo.
- Computed Property `capturaBloqueada`: Si la hora del equipo del cliente se sale del rango operativo, todos los campos de entrada se deshabilitan (`disabled=true`) automáticamente sin recargar la página, y se muestra una barra de advertencia.

### 1.3 Comportamiento Multi-Fila y Saldo Inicial
- Si la categoría tiene la bandera `usa_saldo_inicial` (ej. SOBRANTES O PRESTAMOS), el componente bloquea la visualización de conceptos hasta que el contador establezca (o confirme) el arrastre inicial de la bolsa de dinero a través de `guardarSaldoInicialCategoriaManual()`.
- Soporta capturar múltiples veces un mismo concepto gracias a un generador de Ids sintéticos (`generarIdentificadorFilaConcepto`), lo cual inyecta filas extra a la tabla bajo demanda (Botón "Agregar otro").

### 1.4 Calculadora Reactiva de Saldos (Solo Frontend)
- Se mantiene la tarjeta de **saldo mensual** (saldo inicial, ingresos, egresos, resultado neto, saldo final), pero ahora los montos reaccionan al vuelo con lo que el usuario captura en la tabla, sin recargar.
- Se agrega una segunda tarjeta de **saldo diario del día contable** (ingresos, egresos, resultado neto) con cálculo referencial en pantalla y saldo inicial diario implícito en `0.00`.
- La lógica es estrictamente de frontend: no crea tablas ni persiste información adicional en base de datos.
- Para evitar doble conteo en el resumen mensual, el componente toma una línea base del día ya persistido al cargar y aplica únicamente el delta de la edición activa del usuario.
- Para la categoría **Administración**, la quinta tarjeta mensual ya no muestra `saldo final del mes`; ahora muestra **fondos fijos de la sucursal** usando el campo entregado por backend, y el `saldo inicial` se consume con la fórmula especial de Administración calculada del lado servidor.

---

## 2. Vistas de Reportes (`views/reportes/`)

Pantallas de solo lectura que consolidan y muestran el estado histórico.

### 2.1 Estado de Resultados Mensual (`EstadoResultados.vue`)
- Despliega un componente tipo *TreeTable* o matriz dinámica con el `desglose_por_rubro` del JSON guardado por el backend tras un cierre de mes.
- Al tratarse de un registro "Snapshot Inmutable", la vista simplemente rinde el JSON y asegura que las descripciones y montos no puedan alterarse.

### 2.2 Reporte Diario (`ReporteDiario.vue`)
- Muestra una tabla tipo libro por columnas `Fecha / Concepto / Ingreso / Egreso / Saldo`.
- El detalle principal del cuerpo muestra movimientos de la categoría **Administración** agrupados por fecha contable.
- Incluye un bloque de ajustes contables al final del listado (fondos fijos, faltantes, sobrantes, por comprobar, dólares y bancos) para cerrar el saldo esperado.
- Mantiene control de visibilidad por rol: Director/Administrador con filtros amplios por sucursal y rango, Contador/Gerente restringidos a su sucursal y día contable vigente.

### 2.3 Estadísticas Generales (`Estadisticas.vue`)
- Es un tablero analítico.
- Requiere roles directivos (`['DIRECTOR', 'ADMINISTRADOR', 'SUPERUSUARIO']`) mediante un `meta` tag en el router, por lo que un Contador regular nunca podrá acceder a ella.
