# Documentación del Módulo: Operación Diaria (Reportes Diarios)

Este documento detalla la estructura del módulo `reportes_diarios`, el cual actúa como el corazón transaccional del sistema. Controla el registro de ingresos y egresos, el arrastre de saldos, y la inmutabilidad de la información al cierre de caja.

---

## 1. Arquitectura de Modelos (`models.py`)

El módulo se compone de una relación de Maestro-Detalle. Todo se basa en el "Día Contable", el cual por regla de negocio es siempre **T-1** (el día anterior a la fecha de captura).

### 1.1 `ReporteDiario` (Maestro)
Representa el corte de caja ("fotografía") de un día contable para una sucursal específica.
- **Identificadores:** `sucursal` y `fecha_contable` (T-1, únicos en conjunto).
- **Control de Flujo:**
  - `estado_reporte`: ABIERTO o CERRADO. Una vez cerrado, congela cualquier mutación de sus movimientos.
- **Saldos y Totales (Autocalculados):**
  - `saldo_arrastre_inicio`: Proviene del `saldo_arrastre_fin` del reporte del día anterior.
  - `total_ingresos`, `total_egresos`, `resultado_neto`.
  - `saldo_arrastre_fin`: `saldo_arrastre_inicio` + `resultado_neto`.
- **Snapshots de Auditoría:** `tipo_cambio_usd_snapshot` y `tipo_cambio_eur_snapshot`. Fijan el valor de la divisa en el momento del cierre para que cambios futuros en `ConfiguracionGlobal` no afecten el historial.
- **Historial:** Integrado con `simple_history`.

### 1.2 `MovimientoDiario` (Detalle)
Registra la transacción operativa individual.
- **Campos:**
  - `reporte` (FK -> ReporteDiario).
  - `concepto` (FK -> Concepto): Dictamina si es INGRESO o EGRESO.
  - `monto` (Decimal): Monto final en MXN.
  - `monto_divisa` y `tipo_divisa`: Opcionales si la operación fue en moneda extranjera.
- **Snapshots y Respaldos:**
  - `detalles_snapshot` (JSONField): Guarda el contexto exacto (ej. campos extra) en el momento del registro.
  - `archivo_respaldo`: Permite adjuntar imágenes/PDFs. Se guardan jerárquicamente en `comprobantes/<sucursal>/<categoria>/<fecha>/`.
- **Historial:** Integrado con `simple_history`.

---

## 2. Capa de Serialización (`serializers.py`)

La serialización aplica conversiones de divisa en tiempo real (al vuelo) y evita la mutación manual de campos contables protegidos.

### 2.1 Serializadores del Reporte
- **`ReporteDiarioSerializer`**: Devuelve toda la cabecera y anida la lista de movimientos (`MovimientoDiarioListSerializer(many=True)`).
  - Protege (`read_only`): Totales calculados (`total_ingresos`, `total_egresos`, `resultado_neto`), datos de cierre (`cerrado_en`, `cerrado_por`) y auditoría.
- **`ReporteDiarioListSerializer`**: Excluye los movimientos para renderizar listados o tablas rápidas eficientemente.

### 2.2 Serializadores de Movimientos y Lógica de Divisas
- **Lógica de Dólares (`_es_categoria_dolares`, `_obtener_tasa_cambio_dolares`):**
  - Si el concepto enviado pertenece a la categoría "DOLARES" (o clave DOLARES), el `validate()` del serializador ignora el monto MXN enviado, toma el monto capturado como USD (`monto_divisa`), busca en `ConfiguracionGlobal` la `TASA_CAMBIO_DOLARES` vigente, y calcula automáticamente el `monto` en MXN (`monto_divisa * tasa`).
- **`MovimientoDiarioSerializer`**: Ejecuta las validaciones anteriores. Protege el Snapshot y la auditoría.
- **`MovimientoDiarioListSerializer`**: Inyecta dinámicamente `concepto_nombre`, `categoria_nombre`, `tipo` e `archivo_respaldo_url` para no realizar joins costosos en el frontend.

---

## 3. Controladores y Vistas (`views.py`)

Contiene una alta densidad de reglas de negocio para asegurar la integridad de la contabilidad y los permisos horizontales (jerarquía por sucursales y rango de fechas).

### Reglas Globales (Helpers)
- **Día Contable (`_dia_contable_actual()`):** Calcula en el servidor `fecha_actual - 1 día`. 
- **Roles y Visibilidad (`_resolver_filtros_consulta_reportes()`):**
  - **Perfil Operativo (Gerente/Contador):** Bloqueados a consultar *exclusivamente* su sucursal asignada y *exclusivamente* el día contable actual.
  - **Perfil Directivo (Administrador/Director):** Pueden consultar cualquier sucursal y proveer rangos de fechas (`fecha_inicio` y `fecha_fin`).
  - Límite máximo de consultas: 63 días. Fechas futuras bloqueadas.

### 3.1 `ReporteDiarioViewSet`
Aplica `VentanaHorariaPermiso` en acciones de escritura (bloquea operaciones fuera de horario laboral de oficina).
- **Acciones principales:**
  - `list()`: Respeta la visibilidad por rol.
  - `@action libro-operativo`: Genera una matriz consolidada (Ingresos/Egresos/Saldo por fecha y categoría) arrastrando el saldo. Utilizado para reportes gerenciales (Libro Diario).
  - `@action resumen-rapido`: Devuelve KPIs del día, incluyendo una alerta de "Conceptos Recurrentes Faltantes" (qué falta por capturar).
  - `@action cerrar-actual`: Totaliza la caja, toma snapshots de divisas, estampa al usuario, calcula netos y bloquea el reporte. Encadena el saldo al reporte de mañana si ya estuviese pre-abierto.
  - `@action reabrir`: Exclusivo para ADMINISTRADOR. Regresa a estado ABIERTO para correcciones.

### 3.2 `MovimientoDiarioViewSet`
- **Operaciones CRUD:**
  - Bloquea cualquier `create`, `update` o `destroy` si el `ReporteDiario` padre está `CERRADO`.
  - Fuerza a que el registro provenga de la sucursal asignada al usuario si es Perfil Operativo.
  - `destroy()`: Baja lógica del movimiento.

---

## 4. Referencia de Endpoints API (`urls.py`)

Rutas anidadas en el router bajo `/api/reportes_diarios/`.

### Reportes Diarios (`/api/reportes_diarios/reportes-diarios/`)
| Endpoint | Acción | Método | Descripción |
|----------|--------|--------|-------------|
| `/` | Listar | GET | Filtra por `sucursal_id`, `fecha_inicio`, `fecha_fin`. |
| `/{id}/` | Detalle | GET | Retorna cabecera y lista de movimientos anidados. |
| `/libro-operativo/` | Consulta | GET | Genera la sábana contable cruzada por categorías y fechas. |
| `/actual/` | Operativo | GET | Retorna (o crea autómaticamente) el reporte del día actual (`T-1`). |
| `/actual/resumen-rapido/`| Operativo | GET | Indicadores de progreso del día (total vs capturado). |
| `/actual/cerrar-actual/`| Operativo | POST | Totaliza y congela el día. |
| `/{id}/reabrir/` | Admin | POST | Desbloquea un reporte (Solo Administrador). |

### Movimientos Diarios (`/api/reportes_diarios/movimientos-diarios/`)
| Endpoint | Acción | Método | Descripción |
|----------|--------|--------|-------------|
| `/` | CRUD | POST, GET | Captura transacciones. Soporta `FormData` para envío de comprobantes en el campo `archivo_respaldo`. |
| `/{id}/` | CRUD | GET, PUT, PATCH, DELETE | Modificación y borrado lógico de registros (siempre y cuando el reporte siga ABIERTO). |
