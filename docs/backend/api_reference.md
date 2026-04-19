# Referencia API - APEX-TON Backend

El backend de APEX-TON expone una API RESTful construida con Django REST Framework. Las rutas base están prefijadas con `/api/v1/` o el namespace de cada aplicación. 
La mayoría de los recursos utilizan `ViewSets`, lo que proporciona de manera automática los métodos estándar (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`).

## Autenticación

- **Mecanismo**: Cookies `HttpOnly` / Sesiones (identificado por la presencia del endpoint `iniciar_sesion` y `cerrar_sesion`).
- **Headers Requeridos**: Para métodos que mutan el estado (POST, PUT, PATCH, DELETE), se requiere el encabezado `X-CSRFToken`.

---

## 1. Módulo: Usuarios (`/api/usuarios/`)

### 1.1 Auth & Sesión
- `GET /api/usuarios/usuarios/csrf/`
  - **Descripción**: Obtiene el token CSRF para operaciones subsiguientes.
- `POST /api/usuarios/usuarios/iniciar_sesion/`
  - **Body**: `{ "email": "...", "password": "..." }`
  - **Respuesta**: Detalles del usuario logueado.
- `POST /api/usuarios/usuarios/cerrar_sesion/`
  - **Descripción**: Destruye la sesión actual.
- `GET /api/usuarios/usuarios/sesion_actual/`
  - **Descripción**: Retorna la información de la sesión activa del usuario.

### 1.2 Usuarios (`/api/usuarios/usuarios/`)
- `GET /` - Listar usuarios.
- `POST /` - Crear usuario.
- `GET /{id}/` - Obtener detalle de usuario.
- `PUT / PATCH /{id}/` - Actualizar usuario.
- `DELETE /{id}/` - Desactivar/Eliminar usuario.
- `GET, PUT, PATCH /perfil_propio/` - Administra el perfil del usuario autenticado.
- `POST /{id}/asignar_rol/` - Asignar un rol específico.
- `DELETE /{id}/quitar_rol/{rol_id}/` - Remover un rol.

### 1.3 Roles (`/api/usuarios/roles/`)
- Soporta CRUD estándar.
- `POST /{id}/asignar_permiso/` - Asigna un permiso al rol.
- `DELETE /{id}/quitar_permiso/{permiso_id}/` - Remueve un permiso del rol.

### 1.4 Permisos (`/api/usuarios/permisos/`)
- Soporta CRUD estándar.

---

## 2. Módulo: Operación y Configuración

### 2.1 Sucursales (`/api/sucursales/sucursales/`)
- Soporta CRUD estándar para la gestión de sucursales.

### 2.2 Fondos Fijos (`/api/fondos_fijos/`)
- `/fondos_fijos/`: CRUD de catálogo de fondos fijos.
- `/sucursal_fondos_fijos/`: Asignación de fondos fijos a sucursales (`SucursalFondoFijo`).

### 2.3 Categorías Operativas (`/api/categoria_operativa/`)
- `/categorias/`: CRUD estándar para `CategoriaOperativa`.
- `/conceptos/`: CRUD para `Concepto` (dependientes de categoría y rubro contable).
- `/detalles_parametrizados/`: Detalles adicionales configurables por categoría.
- `/saldos_iniciales/`: Gestión de `SaldoInicialCategoriaMensual`.

### 2.4 Configuraciones Globales (`/api/configuraciones_globales/`)
- `/padres_rubros_contables/`: Agrupadores principales de la contabilidad.
- `/rubros_contables/`: Rubros específicos que pertenecen a un padre.
- `/configuraciones/`: Configuraciones de sistema genéricas (Clave/Valor).

### 2.5 Configuraciones de Usuario (`/api/configuraciones_usuario/configuraciones/`)
- Soporta métodos para configurar preferencias de UI (tema, color de acento) por usuario.

---

## 3. Módulo: Financiero y Reportes

### 3.1 Reportes Diarios (`/api/reportes_diarios/`)
- `/reportes/`
  - `GET /` - Listar reportes diarios por sucursal/fecha.
  - `POST /` - Crear un nuevo reporte diario.
  - `PUT / PATCH /{id}/` - Actualizar estado del reporte (ej. "Cerrado").
- `/movimientos/`
  - `GET /` - Listar movimientos dentro de los reportes diarios.
  - `POST /` - Registrar ingreso/egreso.
  - `PUT / PATCH /{id}/` - Modificar movimiento.
  - `DELETE /{id}/` - Eliminar movimiento (si el reporte no está cerrado).

### 3.2 Libro Estado de Resultados (`/api/libro_estado_resultados/libros/`)
- `GET /` - Listado de libros mensuales.
- `POST /` - Generación de un nuevo libro para un mes/año específico.
- `GET /{id}/` - Detalle completo de los resultados del mes, consolidando la información de los reportes diarios.

---

## Estructura de Respuesta Estándar
Casi todos los endpoints responden siguiendo una estructura unificada:
```json
{
  "estado": "success|error",
  "mensaje": "Mensaje descriptivo del resultado de la operación",
  "data": { ... } // Payload con los recursos solicitados o afectados
}
```
