# APEX-TON — Referencia de API y Modelos del Backend

> **Stack:** Python 3.13 · Django 5.2 · Django REST Framework · MySQL  
> **Autenticación:** Sesiones nativas de Django (`SessionAuthentication`)  
> **Base URL:** `/api/`  
> **Formato de respuesta:** Siempre `{ "status", "message", "data" }`

---

## Convenciones globales

### Respuesta estándar
Todos los endpoints devuelven la misma estructura JSON:

```json
{
  "status": "success",   // "success" | "error"
  "message": "Operación exitosa",
  "data": {}             // objeto | arreglo | null
}
```

### ModeloBase — Campos de auditoría comunes
Todos los modelos transaccionales heredan de `ModeloBase` (clase abstracta en `core/models.py`).

| Campo | Tipo | Descripción |
|---|---|---|
| `estado` | `CharField` | Estado del ciclo de vida: `ACTIVO`, `INACTIVO`, `BLOQUEADO`, `ELIMINADO` |
| `creado_en` | `DateTimeField` | Fecha/hora de creación (automático) |
| `actualizado_en` | `DateTimeField` | Última actualización (automático) |
| `eliminado_en` | `DateTimeField` | Fecha de soft-delete (null = vigente) |
| `creado_por` | `FK → Usuario` | Usuario que creó el registro |
| `actualizado_por` | `FK → Usuario` | Usuario de la última edición |
| `eliminado_por` | `FK → Usuario` | Usuario que eliminó el registro |
| `valor_anterior` | `JSONField` | Snapshot JSON antes de la última modificación |
| `valor_actual` | `JSONField` | Snapshot JSON después de la última modificación |

**Managers:**
- `objects` — Solo registros con `eliminado_en = null` (default)
- `todos` — Todos los registros incluyendo eliminados lógicamente

**Métodos del ciclo de vida:**
- `eliminar_logico(usuario)` — Soft-delete
- `activar()` → Estado `ACTIVO`
- `desactivar()` → Estado `INACTIVO`
- `bloquear()` → Estado `BLOQUEADO`

### Control de horario operativo
Las operaciones de **escritura** (`POST`, `PUT`, `PATCH`, `DELETE`) están bloqueadas fuera del horario definido en `HORARIO_APERTURA` y `HORARIO_CIERRE` (configuraciones globales). Las operaciones de **lectura** (`GET`) siempre están permitidas.

---

## App: `core`

### `ModeloBase` (abstracto)
Clase base descrita en la sección de convenciones globales. No tiene tabla propia en la BD.

### Permisos DRF (`core/permisos.py`)

| Clase | Descripción |
|---|---|
| `VentanaHorariaPermiso` | Bloquea escrituras fuera del horario HORARIO_APERTURA–HORARIO_CIERRE |
| `EsAdministrador` | Solo usuarios con rol `ADMINISTRADOR` o `is_superuser` |

---

## App: `usuarios`
**Prefijo URL:** `/api/usuarios/`  
**Tabla DB:** `usuarios`, `roles`, `permisos`, `roles_permisos`, `usuarios_roles`

### Modelo: `Rol`
**Tabla:** `roles`

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `CharField(80)` · único | Nombre único del rol (`Administrador`, `Cajero`, etc.) |
| `descripcion` | `TextField` · nullable | Alcance y responsabilidades del rol |
| + campos `ModeloBase` | | |

### Modelo: `Permiso`
**Tabla:** `permisos`

| Campo | Tipo | Descripción |
|---|---|---|
| `codigo` | `CharField(100)` · único | Identificador en formato `MODULO_ACCION` (ej. `SUCURSALES_CREAR`) |
| `nombre` | `CharField(150)` | Nombre descriptivo legible |
| `modulo` | `CharField(80)` | Módulo del sistema al que pertenece |
| `descripcion` | `TextField` · nullable | Detalle de lo que permite hacer |
| + campos `ModeloBase` | | |

### Modelo: `RolPermiso`
**Tabla:** `roles_permisos`  
**Unique together:** `(rol, permiso)`

| Campo | Tipo | Descripción |
|---|---|---|
| `rol` | `FK → Rol` | Rol receptor del permiso |
| `permiso` | `FK → Permiso` | Permiso asignado al rol |
| + campos `ModeloBase` | | |

### Modelo: `Usuario`
**Tabla:** `usuarios`  
Extiende `AbstractBaseUser` + `PermissionsMixin`. **No hereda de ModeloBase** (tiene sus propios campos de auditoría).

| Campo | Tipo | Descripción |
|---|---|---|
| `username` | `CharField(80)` · único | Identificador de login |
| `nombre` | `CharField(150)` | Nombre completo |
| `correo` | `EmailField` · nullable | Correo electrónico (opcional) |
| `sucursal` | `FK → Sucursal` · nullable | Sucursal a la que pertenece (null = usuario global) |
| `is_active` | `BooleanField` | Puede iniciar sesión |
| `is_staff` | `BooleanField` | Acceso al admin de Django |
| `creado_en` | `DateTimeField` | Fecha de registro |
| `actualizado_en` | `DateTimeField` | Última modificación |

**Campo de login:** `USERNAME_FIELD = 'username'`

### Modelo: `UsuarioRol`
**Tabla:** `usuarios_roles`  
**Unique together:** `(usuario, rol)`

| Campo | Tipo | Descripción |
|---|---|---|
| `usuario` | `FK → Usuario` | Usuario receptor del rol |
| `rol` | `FK → Rol` | Rol asignado |
| `asignado_en` | `DateTimeField` | Fecha de asignación |

### Endpoints de la app `usuarios`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/usuarios/roles/` | Listar roles |
| `POST` | `/api/usuarios/roles/` | Crear rol |
| `GET` | `/api/usuarios/roles/{id}/` | Obtener rol |
| `PUT/PATCH` | `/api/usuarios/roles/{id}/` | Actualizar rol |
| `DELETE` | `/api/usuarios/roles/{id}/` | Eliminar rol |
| `GET` | `/api/usuarios/permisos/` | Listar permisos |
| `POST` | `/api/usuarios/permisos/` | Crear permiso |
| `GET/PUT/PATCH/DELETE` | `/api/usuarios/permisos/{id}/` | CRUD de permiso |
| `GET` | `/api/usuarios/usuarios/` | Listar usuarios |
| `POST` | `/api/usuarios/usuarios/` | Crear usuario |
| `GET/PUT/PATCH/DELETE` | `/api/usuarios/usuarios/{id}/` | CRUD de usuario |
| `GET` | `/api/usuarios/rol-permisos/` | Listar asignaciones rol→permiso |
| `POST` | `/api/usuarios/rol-permisos/` | Asignar permiso a rol |
| `GET/PUT/PATCH/DELETE` | `/api/usuarios/rol-permisos/{id}/` | CRUD |
| `GET` | `/api/usuarios/usuario-roles/` | Listar asignaciones usuario→rol |
| `POST` | `/api/usuarios/usuario-roles/` | Asignar rol a usuario |
| `GET/PUT/PATCH/DELETE` | `/api/usuarios/usuario-roles/{id}/` | CRUD |

---

## App: `configuraciones_globales`
**Prefijo URL:** `/api/global/`  
**Tabla DB:** `configuraciones_globales`, `rubro_contable`

### Modelo: `ConfiguracionGlobal`
**Tabla:** `configuraciones_globales`

| Campo | Tipo | Descripción |
|---|---|---|
| `clave` | `CharField(100)` · único | Clave de configuración (ej. `TIPO_CAMBIO_USD`, `HORARIO_APERTURA`) |
| `valor` | `TextField` | Valor en texto plano |
| `tipo_valor` | `CharField(20)` | Tipo de dato: `STRING`, `INT`, `FLOAT`, `BOOLEAN`, `DATE`, `TIME`, `DATETIME`, `JSON` |
| `descripcion` | `TextField` · nullable | Descripción del propósito |
| + campos `ModeloBase` | | |

**Propiedad calculada `valor_tipado`:** Devuelve el valor convertido al tipo nativo correspondiente (int, float, bool, date, etc.).

**Claves de sistema relevantes:**

| Clave | Tipo | Uso |
|---|---|---|
| `HORARIO_APERTURA` | `TIME` | Hora a partir de la cual se permiten escrituras |
| `HORARIO_CIERRE` | `TIME` | Hora límite para operaciones de escritura |
| `TIPO_CAMBIO_USD` | `FLOAT` | Tipo de cambio MXN/USD (snapshot en reportes) |
| `TIPO_CAMBIO_EUR` | `FLOAT` | Tipo de cambio MXN/EUR (snapshot en reportes) |

### Modelo: `RubroContable`
**Tabla:** `rubro_contable`

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `CharField(150)` · único | Nombre único del rubro (ej. `VENTAS_BEBIDAS`) |
| `padre` | `CharField(150)` | Categoría padre: `INGRESOS`, `GASTOS`, `JUEGO_VIVO`, etc. |
| `tipo` | `CharField(20)` | `INGRESO` o `EGRESO` |
| `descripcion` | `TextField` · nullable | Descripción adicional |
| + campos `ModeloBase` | | |

### Endpoints de la app `configuraciones_globales`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/global/configuraciones/` | Listar configuraciones |
| `POST` | `/api/global/configuraciones/` | Crear configuración |
| `GET/PUT/PATCH/DELETE` | `/api/global/configuraciones/{id}/` | CRUD de configuración |
| `GET` | `/api/global/rubros/` | Listar rubros contables |
| `POST` | `/api/global/rubros/` | Crear rubro contable |
| `GET/PUT/PATCH/DELETE` | `/api/global/rubros/{id}/` | CRUD de rubro |

---

## App: `sucursales`
**Prefijo URL:** `/api/sucursales/`  
**Tabla DB:** `sucursales`

### Modelo: `Sucursal`
**Tabla:** `sucursales`

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `CharField(150)` · único | Nombre comercial de la sala |
| `clave` | `CharField(30)` · único | Código interno (ej. `MOR-01`) |
| `direccion` | `TextField` · nullable | Domicilio completo |
| `ciudad` | `CharField(100)` · nullable | Ciudad/municipio |
| `estado_republica` | `CharField(100)` · nullable | Entidad federativa |
| `telefono` | `CharField(20)` · nullable | Teléfono de contacto |
| `correo` | `EmailField` · nullable | Correo institucional |
| `encargado` | `CharField(150)` · nullable | Nombre del responsable operativo |
| `fondo_inicial` | `DecimalField(18,2)` | Monto inicial del fondo fijo en MXN |
| + campos `ModeloBase` | | |

### Endpoints de la app `sucursales`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/sucursales/sucursales/` | Listar sucursales |
| `POST` | `/api/sucursales/sucursales/` | Crear sucursal |
| `GET/PUT/PATCH/DELETE` | `/api/sucursales/sucursales/{id}/` | CRUD de sucursal |

---

## App: `fondos_fijos`
**Prefijo URL:** `/api/fondos/`  
**Tabla DB:** `fondos_fijos`

### Modelo: `FondoFijo`
**Tabla:** `fondos_fijos`  
Relación **1:1** con `Sucursal`. Cada sucursal tiene exactamente un fondo fijo.

| Campo | Tipo | Descripción |
|---|---|---|
| `sucursal` | `OneToOneField → Sucursal` | Sucursal propietaria del fondo |
| `monto_autorizado` | `DecimalField(18,2)` | Monto máximo autorizado en MXN |
| `saldo_actual` | `DecimalField(18,2)` | Saldo disponible actual (se recalcula con movimientos) |
| `moneda` | `CharField(10)` | Código de moneda (default `MXN`) |
| `observaciones` | `TextField` · nullable | Notas administrativas |
| + campos `ModeloBase` | | |

### Endpoints de la app `fondos_fijos`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/fondos/fondos-fijos/` | Listar fondos fijos |
| `POST` | `/api/fondos/fondos-fijos/` | Crear fondo fijo |
| `GET/PUT/PATCH/DELETE` | `/api/fondos/fondos-fijos/{id}/` | CRUD de fondo fijo |

---

## App: `categoria_operativa`
**Prefijo URL:** `/api/operativa/`  
**Tabla DB:** `categorias_operativas`, `conceptos`, `detalles_parametrizados`

### Modelo: `CategoriaOperativa` (Pestañas)
**Tabla:** `categorias_operativas`

| Campo | Tipo | Descripción |
|---|---|---|
| `nombre` | `CharField(100)` · único | Nombre de la pestaña (ej. `ADMINISTRACION`, `BOOK`, `DOLARES`) |
| `clave` | `CharField(50)` · único | Identificador corto (ej. `ADMIN`, `BOOK`) |
| `descripcion` | `TextField` · nullable | Descripción del tipo de movimientos |
| `tipo` | `CharField(20)` | `INGRESO`, `EGRESO` o `MIXTO` |
| `orden` | `PositiveSmallIntegerField` | Posición de visualización en la interfaz |
| + campos `ModeloBase` | | |

**Pestañas del sistema:** `ADMINISTRACION`, `BOOK`, `BILLPOCKET`, `BAHIA BANORTE`, `BANORTE AHIS`, `BBVB BANCOMER`, `DOLARES`, `PERDIDAS`, `PERMISO`, `SOBRANTES`, `POR COMPROBAR`, `MAQUINAS`, `CAJA CHICA MORELIA`, `COMPARATIVO`, `PRESUPUESTO`, `MAQUINEROS`, `JUEGO VIVO`, `F. fijos`

### Modelo: `Concepto`
**Tabla:** `conceptos`  
**Unique together:** `(categoria, nombre)`

| Campo | Tipo | Descripción |
|---|---|---|
| `categoria` | `FK → CategoriaOperativa` | Pestaña a la que pertenece |
| `rubro_contable` | `FK → RubroContable` | Rubro contable para consolidación del Estado de Resultados |
| `nombre` | `CharField(150)` | Nombre del movimiento (ej. `VENTA DE CAFE`) |
| `clave` | `CharField(60)` · único | Código único (ej. `ADMIN_VENTA_CAFE`) |
| `tipo` | `CharField(20)` | `INGRESO` o `EGRESO` |
| `descripcion` | `TextField` · nullable | Descripción y contexto de aplicación |
| `es_recurrente` | `BooleanField` | Si se repite periódicamente |
| + campos `ModeloBase` | | |

### Modelo: `DetalleParametrizado`
**Tabla:** `detalles_parametrizados`  
**Unique together:** `(categoria, clave)`  
Campos extra por categoría sin alterar el esquema base (ej. `responsable`, `area_origen` para la pestaña `SOBRANTES`).

| Campo | Tipo | Descripción |
|---|---|---|
| `categoria` | `FK → CategoriaOperativa` | Pestaña que extiende |
| `nombre` | `CharField(100)` | Nombre descriptivo del campo |
| `clave` | `CharField(80)` | Identificador en `snake_case` |
| `tipo_valor` | `CharField(20)` | `TEXT`, `DECIMAL`, `INT`, `BOOLEAN`, `DATE`, `DATETIME` |
| `requerido` | `BooleanField` | Si es obligatorio al registrar |
| `valor_defecto` | `CharField(255)` · nullable | Valor predeterminado |
| `descripcion` | `TextField` · nullable | Propósito del campo |
| + campos `ModeloBase` | | |

### Endpoints de la app `categoria_operativa`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/operativa/categorias/` | Listar categorías (pestañas) |
| `POST` | `/api/operativa/categorias/` | Crear categoría |
| `GET/PUT/PATCH/DELETE` | `/api/operativa/categorias/{id}/` | CRUD de categoría |
| `GET` | `/api/operativa/conceptos/` | Listar conceptos |
| `POST` | `/api/operativa/conceptos/` | Crear concepto |
| `GET/PUT/PATCH/DELETE` | `/api/operativa/conceptos/{id}/` | CRUD de concepto |
| `GET` | `/api/operativa/detalles-parametrizados/` | Listar detalles parametrizados |
| `POST` | `/api/operativa/detalles-parametrizados/` | Crear detalle |
| `GET/PUT/PATCH/DELETE` | `/api/operativa/detalles-parametrizados/{id}/` | CRUD de detalle |

---

## App: `reportes_diarios`
**Prefijo URL:** `/api/reportes/`  
**Tabla DB:** `reportes_diarios`, `movimientos_diarios`

### Modelo: `ReporteDiario`
**Tabla:** `reportes_diarios`  
**Unique together:** `(sucursal, fecha_contable)`  
Integra `django-simple-history` para auditoría completa de cambios.

| Campo | Tipo | Descripción |
|---|---|---|
| `sucursal` | `FK → Sucursal` | Sala a la que corresponde |
| `fecha_contable` | `DateField` | **Siempre D-1** (día anterior al operativo). Calculado por el backend |
| `estado_reporte` | `CharField(10)` | `ABIERTO` (editable) o `CERRADO` (inmutable) |
| `saldo_arrastre_inicio` | `DecimalField(18,2)` | Saldo al inicio del día (viene del `saldo_arrastre_fin` del día anterior) |
| `saldo_arrastre_fin` | `DecimalField(18,2)` | Saldo al cierre (inicio + resultado neto) |
| `tipo_cambio_usd_snapshot` | `DecimalField(12,4)` | Tipo de cambio USD al momento del corte (snapshot, inmutable) |
| `tipo_cambio_eur_snapshot` | `DecimalField(12,4)` | Tipo de cambio EUR al momento del corte (snapshot, inmutable) |
| `total_ingresos` | `DecimalField(18,2)` | Suma de ingresos del día (calculado al cerrar) |
| `total_egresos` | `DecimalField(18,2)` | Suma de egresos del día (calculado al cerrar) |
| `resultado_neto` | `DecimalField(18,2)` | Ingresos − Egresos |
| `cerrado_en` | `DateTimeField` · nullable | Fecha/hora del cierre |
| `cerrado_por` | `FK → Usuario` · nullable | Usuario que ejecutó el cierre |
| `observaciones` | `TextField` · nullable | Notas del cierre |
| + campos `ModeloBase` | | |

**Regla crítica T-1:** El backend siempre calcula `fecha_contable = hoy - 1 día`. El frontend **nunca** puede enviar ni sobreescribir esta fecha.

### Modelo: `MovimientoDiario`
**Tabla:** `movimientos_diarios`  
Integra `django-simple-history` para auditoría completa.

| Campo | Tipo | Descripción |
|---|---|---|
| `reporte` | `FK → ReporteDiario` | Reporte al que pertenece (asignado automáticamente por el backend) |
| `concepto` | `FK → Concepto` | Concepto que clasifica el movimiento |
| `monto` | `DecimalField(18,2)` | Monto en MXN (siempre positivo; tipo INGRESO/EGRESO viene del concepto) |
| `monto_divisa` | `DecimalField(18,2)` · nullable | Monto en divisa extranjera si aplica |
| `tipo_divisa` | `CharField(10)` · nullable | `USD`, `EUR`, etc. |
| `detalles_snapshot` | `JSONField` | Snapshot de detalles parametrizados al momento del registro |
| `notas` | `TextField` · nullable | Observaciones específicas del movimiento |
| + campos `ModeloBase` | | |

**Regla crítica:** El campo `reporte` enviado por el frontend es **ignorado**. El backend lo asigna automáticamente según `sucursal_id` y `fecha_contable = T-1`.

### Endpoints de la app `reportes_diarios`

| Método | URL | Permisos | Descripción |
|---|---|---|---|
| `GET` | `/api/reportes/reportes-diarios/` | Autenticado | Listar reportes (filtrar con `?sucursal_id=`) |
| `POST` | `/api/reportes/reportes-diarios/` | Autenticado + Horario | Crear/obtener reporte del día actual (T-1), con encadenamiento de saldo |
| `GET` | `/api/reportes/reportes-diarios/{id}/` | Autenticado | Detalle de un reporte |
| `PATCH` | `/api/reportes/reportes-diarios/{id}/` | Autenticado + Horario | Actualizar campos del reporte (solo si ABIERTO) |
| `DELETE` | `/api/reportes/reportes-diarios/{id}/` | Autenticado + Horario | Soft-delete (solo si ABIERTO) |
| `POST` | `/api/reportes/reportes-diarios/{id}/cerrar/` | Autenticado | Cierre manual del día: calcula totales, guarda snapshot divisas, bloquea el reporte |
| `POST` | `/api/reportes/reportes-diarios/{id}/reabrir/` | **Solo ADMINISTRADOR** | Reabre un reporte cerrado, deja rastro en historial |
| `GET` | `/api/reportes/movimientos-diarios/` | Autenticado | Listar movimientos (filtrar con `?reporte_id=`, `?categoria_id=`) |
| `POST` | `/api/reportes/movimientos-diarios/` | Autenticado + Horario | Registrar movimiento (el reporte se asigna automáticamente por T-1) |
| `GET` | `/api/reportes/movimientos-diarios/{id}/` | Autenticado | Detalle de un movimiento |
| `PUT/PATCH` | `/api/reportes/movimientos-diarios/{id}/` | Autenticado + Horario | Editar movimiento (solo si reporte ABIERTO) |
| `DELETE` | `/api/reportes/movimientos-diarios/{id}/` | Autenticado + Horario | Soft-delete (solo si reporte ABIERTO) |

---

## App: `estado_resultados`
**Prefijo URL:** `/api/`  
**Sin modelos propios:** es un endpoint de agregación pura.

### Endpoint: Estado de Resultados (modo dual)

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/estado-resultados/` | Estado de Resultados (tiempo real o snapshot histórico) |

**Parámetros de query:**

| Parámetro | Requerido | Default | Descripción |
|---|---|---|---|
| `sucursal_id` | ✅ Sí | — | ID de la sucursal |
| `mes` | No | Mes actual | Mes del período (1-12) |
| `anio` | No | Año actual | Año del período |

**Comportamiento (modo dual):**

1. **Mes CERRADO** → Lee el `LibroEstadoResultados` guardado (`fuente: "snapshot_historico"`). Lectura instantánea sin agregación.
2. **Mes en CURSO** → Agrega en tiempo real desde `MovimientoDiario` (`fuente: "tiempo_real"`). Siempre refleja el estado actual.

**Respuesta (fragmento):**
```json
{
  "status": "success",
  "data": {
    "fuente": "tiempo_real",
    "sucursal_id": 1,
    "periodo": "2026/03",
    "saldo_arrastre_inicio": 50000.00,
    "total_ingresos": 120000.00,
    "total_egresos": 80000.00,
    "resultado_neto": 40000.00,
    "saldo_proyectado_fin": 90000.00,
    "por_categoria": [...],
    "por_rubro": [...]
  }
}
```

---

## App: `libro_estado_resultados`
**Prefijo URL:** `/api/libro/`  
**Tabla DB:** `libro_estado_resultados`

### Modelo: `LibroEstadoResultados`
**Tabla:** `libro_estado_resultados`  
**Unique together:** `(sucursal, anio, mes)`  
**INMUTABLE** una vez cerrado. Snapshot mensual histórico.

| Campo | Tipo | Descripción |
|---|---|---|
| `sucursal` | `FK → Sucursal` | Sucursal del período |
| `anio` | `PositiveSmallIntegerField` | Año contable (ej. 2026) |
| `mes` | `PositiveSmallIntegerField` | Mes (1-12) |
| `estado_mes` | `CharField(10)` | `ABIERTO` o `CERRADO` |
| `tipo_cambio_usd_snapshot` | `DecimalField(12,4)` | Tipo de cambio USD al cierre (inmutable) |
| `tipo_cambio_eur_snapshot` | `DecimalField(12,4)` | Tipo de cambio EUR al cierre (inmutable) |
| `total_ingresos` | `DecimalField(18,2)` | Total ingresos del mes |
| `total_egresos` | `DecimalField(18,2)` | Total egresos del mes |
| `resultado_neto` | `DecimalField(18,2)` | Ingresos − Egresos |
| `saldo_arrastre_inicio` | `DecimalField(18,2)` | Saldo al inicio del mes |
| `saldo_arrastre_fin` | `DecimalField(18,2)` | Saldo al cierre del mes |
| `desglose_por_rubro` | `JSONField` | Totales agrupados por rubro contable al cierre |
| `cerrado_en` | `DateTimeField` · nullable | Fecha/hora del cierre |
| `cerrado_por` | `FK → Usuario` · nullable | Usuario que ejecutó el cierre |
| `observaciones` | `TextField` · nullable | Notas del cierre mensual |
| + campos `ModeloBase` | | |

**Regla de negocio:** Si se modifica el tipo de cambio en `ConfiguracionGlobal`, los registros históricos del libro **NO** se modifican. Los snapshots son inmutables.

### Endpoints de la app `libro_estado_resultados`

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/libro/libro-estado-resultados/` | Listar todos los libros mensuales |
| `POST` | `/api/libro/libro-estado-resultados/` | Crear libro mensual |
| `GET/PUT/PATCH/DELETE` | `/api/libro/libro-estado-resultados/{id}/` | CRUD de libro |

---

## Tareas programadas (Celery)
**App:** `reportes_diarios/tareas.py`  
**Scheduler:** `django-celery-beat` con `DatabaseScheduler`  
**Broker/Backend:** Redis (`redis://localhost:6379/0`)  
**Zona horaria:** `America/Mexico_City`

| Tarea | Trigger | Descripción |
|---|---|---|
| `cerrar_dia_contable` | Automático (fin del día operativo) | Cierra el `ReporteDiario` del día T-1 para todas las sucursales activas: calcula totales, guarda snapshot de divisas y bloquea el reporte |
| `cerrar_mes_contable` | Automático (fin de mes) | Crea o cierra el `LibroEstadoResultados` del mes, consolida todos los movimientos del mes |

---

## Roles del sistema

| Rol | Capacidades |
|---|---|
| `ADMINISTRADOR` | Acceso total. Único que puede reabrir reportes cerrados. Gestión completa del sistema |
| `GERENTE` | Mismos permisos que Contador (por ahora) |
| `CONTADOR` | Captura de pestañas históricas: `POR COMPROBAR`, `MAQUINAS`, `CAJA CHICA MORELIA`, `PRESUPUESTO`, `MAQUINEROS`, `JUEGO VIVO` |
| `DIRECTOR` | Solo lectura: reportes, comparativos, Estado de Resultados. Puede exportar PDF/Excel y ajustar configuraciones globales y fondos fijos por sucursal |

---

## Diagrama de flujo operativo

```
APERTURA DEL DÍA (HORARIO_APERTURA)
│
├── Usuario registra movimientos → POST /api/reportes/movimientos-diarios/
│   ├── Backend asigna automáticamente ReporteDiario del T-1
│   ├── Snapshot de detalles parametrizados en detalles_snapshot
│   └── Tipo INGRESO/EGRESO heredado del Concepto
│
├── En tiempo real → GET /api/estado-resultados/?sucursal_id=X
│   └── Agrega MovimientoDiarios por rubro y categoría
│
CIERRE DEL DÍA (HORARIO_CIERRE o tarea Celery)
│
├── POST /api/reportes/reportes-diarios/{id}/cerrar/
│   ├── Calcula total_ingresos, total_egresos, resultado_neto
│   ├── Snapshot tipo de cambio al momento del cierre
│   ├── saldo_arrastre_fin = inicio + neto
│   └── estado_reporte = CERRADO (inmutable)
│
└── Si es fin de mes → Tarea Celery crea LibroEstadoResultados
    ├── Snapshot inmutable: tipo de cambio, totales, desglose por rubro
    └── saldo_arrastre_fin → inicio del siguiente mes
```
