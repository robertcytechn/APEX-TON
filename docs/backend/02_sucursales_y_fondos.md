# Documentación del Módulo: Sucursales y Fondos Fijos

Este documento detalla la estructura, serialización y controladores de las aplicaciones `sucursales` y `fondos_fijos`. Estos módulos administran las entidades de negocio físicas (casinos/sucursales) y las configuraciones de flujos de efectivo asignados a ellas (fondos fijos).

---

## 1. Arquitectura de Modelos (`models.py`)

Ambos módulos dependen de `core.models.ModeloBase` para garantizar la trazabilidad (auditoría de creación, edición, borrado lógico).

### 1.1 Módulo `sucursales`

#### `Sucursal`
Representa una sala de juegos o sede operativa del negocio.
- **Campos Principales:**
  - `nombre` (CharField, 150): Nombre comercial único (ej. "Sala Morelia Centro").
  - `clave` (CharField, 30): Identificador alfanumérico corto y único (ej. "MOR-01").
  - `direccion`, `ciudad`, `estado_republica`: Metadatos de ubicación geográfica.
  - `telefono`, `correo`, `encargado`: Datos de contacto operativo.
- **Relaciones Internas:**
  - `fondos_fijos`: Una relación `ManyToManyField` hacia `FondoFijo` a través del modelo pivote explícito `SucursalFondoFijo`. Esto permite gestionar qué fondos pertenecen a qué sucursal y con qué monto operativo.

### 1.2 Módulo `fondos_fijos`

#### `FondoFijo`
Catálogo maestro de los tipos de fondos fijos que existen a nivel global.
- **Campos Principales:**
  - `nombre` (CharField, 120): Único (ej. "Caja Chica", "Juego Vivo").
  - `descripcion` (TextField): Propósito operativo.

#### `SucursalFondoFijo` (Tabla Pivote)
Registra la asignación de un `FondoFijo` específico a una `Sucursal` específica, dictaminando su presupuesto inicial o tamaño base.
- **Campos Principales:**
  - `sucursal` (ForeignKey -> `Sucursal`): Protegido contra borrado (`on_delete=models.PROTECT`).
  - `fondo_fijo` (ForeignKey -> `FondoFijo`): Protegido contra borrado (`on_delete=models.PROTECT`).
  - `monto_asignado` (DecimalField): Valor monetario con 2 decimales asignado específicamente a esa sala.
- **Restricciones:** Unicidad compuesta entre `('sucursal', 'fondo_fijo')` para evitar asignaciones duplicadas.

---

## 2. Capa de Serialización (`serializers.py`)

Se diseñaron serializadores robustos para omitir los campos de auditoría del usuario en las peticiones de escritura.

### 2.1 Serializadores de Sucursales
- **`SucursalSerializer`**: Expone la totalidad de los datos de la sucursal. Marca `fondos_fijos` y todos los campos de auditoría (`creado_en`, `actualizado_en`, `creado_por`, etc.) como `read_only_fields`.
- **`SucursalListSerializer`**: Un subconjunto optimizado para listas desplegables o tablas rápidas (`id`, `clave`, `nombre`, `ciudad`, `estado_republica`, `encargado`, `estado`).

### 2.2 Serializadores de Fondos Fijos
- **`FondoFijoSerializer`**: Mapea directamente todos los atributos del catálogo maestro de fondos, excluyendo auditoría.
- **`SucursalFondoFijoSerializer`**: Al leer relaciones Foráneas, inyecta dinámicamente:
  - `sucursal_nombre`: Recuperado de `sucursal.nombre` (Read Only).
  - `fondo_fijo_nombre`: Recuperado de `fondo_fijo.nombre` (Read Only).
  - Facilita enormemente el renderizado de la UI sin consultas adicionales.

---

## 3. Controladores y Vistas (`views.py`)

Siguiendo la convención general, todos los controladores extienden `viewsets.ViewSet` de Django REST Framework y envuelven sus retornos en la función unificada `respuesta_estandar`.

### 3.1 `SucursalViewSet`
- **Operaciones CRUD:** 
  - `list()` (usando `SucursalListSerializer`), `create()`, `retrieve()`, `update()`, `partial_update()`.
  - `destroy()`: Ejecuta una baja lógica llamando a `instancia.eliminar_logico(usuario=request.user)`. Nunca borra físicamente.
- **Acciones de Ciclo de Vida (Custom Actions):**
  - `@action /activar`: Invoca `instancia.activar()` para cambiar el estado a ACTIVO.
  - `@action /desactivar`: Invoca `instancia.desactivar()`.
  - `@action /bloquear`: Invoca `instancia.bloquear()`.

### 3.2 `FondoFijoViewSet`
- **Autenticación/Permisos:** Requiere usuario autenticado y el permiso custom `EsDirectorOAdministradorEnEscritura`.
- **Operaciones CRUD:** Soporta el flujo estándar (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy` con baja lógica).

### 3.3 `SucursalFondoFijoViewSet`
- **Autenticación/Permisos:** Mismos permisos estrictos.
- **Operaciones CRUD:**
  - El método `list()` optimiza la carga de base de datos ejecutando `select_related('sucursal', 'fondo_fijo')` para evitar el problema de N+1 queries al serializar los nombres inyectados por el serializador.
  - Implementa la baja lógica regular.

---

## 4. Referencia de Endpoints API (`urls.py`)

Los controladores son expuestos mediante enrutadores `DefaultRouter` estándar.

### Rutas de Sucursales (`/api/sucursales/`)
| Endpoint | Acción | Método | Descripción |
|----------|--------|--------|-------------|
| `/api/sucursales/sucursales/` | CRUD | GET, POST | Lista resumida y Creación de sucursales. |
| `/api/sucursales/sucursales/{id}/` | CRUD | GET, PUT, PATCH, DELETE | Manipulación y Soft-Delete de sucursal. |
| `/api/sucursales/sucursales/{id}/activar/` | Estado | POST | Cambia el estado a Activo. |
| `/api/sucursales/sucursales/{id}/desactivar/`| Estado | POST | Cambia el estado a Inactivo. |
| `/api/sucursales/sucursales/{id}/bloquear/` | Estado | POST | Cambia el estado a Bloqueado. |

### Rutas de Fondos Fijos (`/api/fondos_fijos/`)
| Endpoint | Acción | Método | Descripción |
|----------|--------|--------|-------------|
| `/api/fondos_fijos/fondos-fijos/` | CRUD | GET, POST | Gestión del catálogo maestro de Fondos. |
| `/api/fondos_fijos/fondos-fijos/{id}/` | CRUD | GET, PUT, PATCH, DELETE | Modificación y Baja lógica de Fondo Fijo maestro. |
| `/api/fondos_fijos/sucursales-fondos-fijos/` | CRUD | GET, POST | Listado y asignación de fondos a sucursales (`monto_asignado`). |
| `/api/fondos_fijos/sucursales-fondos-fijos/{id}/` | CRUD | GET, PUT, PATCH, DELETE | Modificación del monto o baja lógica de la asignación. |

**Ejemplo de Payload Exitoso (Listar Asignaciones de Fondo)**:
```json
{
  "status": "success",
  "message": "Asignaciones de fondos fijos obtenidas correctamente.",
  "data": [
    {
      "id": 1,
      "sucursal": 3,
      "fondo_fijo": 2,
      "monto_asignado": "50000.00",
      "sucursal_nombre": "Sala Morelia Centro",
      "fondo_fijo_nombre": "Juego Vivo",
      "estado": "A"
    }
  ]
}
```
