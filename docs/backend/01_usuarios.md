# Documentación del Módulo: Usuarios

Este documento describe exhaustivamente la arquitectura, serialización y controladores de la aplicación `usuarios`. Este módulo es fundamental para el control de acceso, gestión de sesiones e identidades de todo el sistema APEX-TON.

---

## 1. Arquitectura de Modelos (`models.py`)

La capa de datos se centra en extender `AbstractBaseUser` y `PermissionsMixin` de Django, incorporando auditoría a través de `ModeloBase` y una estructura de roles granulares.

### 1.1 `Usuario`
Modelo principal del sistema. Hereda de `AbstractBaseUser` y `PermissionsMixin`.

- **Campos Principales:**
  - `username` (CharField, 80): Identificador único de inicio de sesión.
  - `nombre` (CharField, 150): Nombre completo.
  - `correo` (EmailField): Correo electrónico opcional.
  - `foto_perfil` (ImageField): Foto almacenada con una estructura jerárquica: `media/<casino_global>/<id_usuario>/images/perfil.ext`.
  - `sucursal` (ForeignKey -> `Sucursal`): Nulo si es un usuario con privilegios globales, o asignado a una sucursal específica.
  - `is_active` (BooleanField, default=True): Permite control de acceso lógico (Soft Delete).
  - `is_staff` (BooleanField): Permiso nativo para el administrador de Django.
  - `requiere_cambio_password` (BooleanField): Forza al usuario a renovar su contraseña en el próximo inicio de sesión.
- **Relaciones Internas:**
  - Manager personalizado `UsuarioManager` para la creación correcta de usuarios y superusuarios manipulando el `username`.

### 1.2 `Rol`
Clasifica a los usuarios según sus responsabilidades.
- Hereda de `ModeloBase` (auditoría + borrado lógico).
- **Campos:** `nombre` (único, 80 char), `descripcion` (texto libre).

### 1.3 `Permiso`
Define acciones granulares y unívocas del sistema.
- Hereda de `ModeloBase`.
- **Campos:** `codigo` (único, formato `MODULO_ACCION`), `nombre`, `modulo` (agrupador para UI), `descripcion`.

### 1.4 Tablas Intermedias (`RolPermiso` y `UsuarioRol`)
- `RolPermiso` (Hereda de `ModeloBase`): Asigna muchos permisos a muchos roles. Regla de unicidad en `(rol, permiso)`.
- `UsuarioRol` (Modelo estándar Django): Asigna muchos roles a muchos usuarios. Registra `asignado_en`.

---

## 2. Capa de Serialización (`serializers.py`)

Los serializadores configuran qué datos se exponen o se aceptan en la API REST, protegiendo campos de auditoría internamente.

- **`PermisoSerializer` y `RolPermisoSerializer`**: Exponen todos los campos pero protegen los valores de auditoría (`creado_en`, `creado_por`, etc.) dejándolos como `read_only`.
- **`RolSerializer`**: Incorpora los permisos asociados al rol a través de un campo anidado `permisos` (aprovechando `RolPermisoSerializer(source='rol_permisos')`).
- **`UsuarioSerializer`**: 
  - Incluye `sucursal_nombre`, `foto_perfil_url` (mediante un `SerializerMethodField`) y `roles` anidados.
  - Oculta de lectura el campo `password` (`write_only=True`).
  - Sobrescribe `create()` y `update()` para aplicar correctamente el hash de la contraseña si ésta fue proveída.
- **`UsuarioListSerializer`**: Una versión reducida para la tabla principal, omitiendo datos sensibles o pesados y optimizando las consultas.

---

## 3. Controladores y Vistas (`views.py`)

Todo el módulo utiliza `ViewSet` base nativos de DRF en lugar de `ModelViewSet`, lo que ofrece un control absoluto y explícito de la inyección de la respuesta en la función envoltorio `respuesta_estandar`.

### 3.1 Utilidades Transversales
- `respuesta_estandar`: Toda respuesta de este módulo sigue el estándar JSON: `{ "status": "...", "message": "...", "data": ... }`.
- `construir_datos_sesion`: Retorna la sesión completa (Usuario + Lista Plana de Roles + Lista Plana de Permisos Únicos). 

### 3.2 `UsuarioViewSet`
Controlador más importante que agrupa CRUD de usuarios y métodos de autenticación nativos.
- **Auth Endpoints:**
  - `csrf()`: Retorna token CSRF y establece cookie.
  - `iniciar_sesion()`: Soporta login por `username` o `correo` simultáneamente utilizando un `Q` object. Crea sesión Django nativa.
  - `cerrar_sesion()`: Finaliza la sesión actual nativa.
  - `sesion_actual()`: Recupera la sesión activa.
- **Perfil de Usuario (`/perfil-propio/`):**
  - Maneja métodos GET y PATCH.
  - Soporta MultiPart/Form Data para carga de imágenes (`foto_perfil`).
  - Maneja validaciones obligatorias de cambio de contraseña si `requiere_cambio_password` está en `True`.
- **Soporte técnico (`/soporte-tecnico/solicitudes/`):**
  - Endpoint autenticado para registrar tickets de soporte.
  - Persiste cada solicitud en el modelo `TicketSoporteTecnico` con folio único, snapshot del usuario, detalle del incidente y estado de seguimiento.
  - Valida selectores de problema/áreas/comportamiento y descripción detallada.
  - Envía correo al canal técnico con destinatario principal `robert-cyby@hotmail.com` y copia a `robertot@gbentretenimiento.com`, incluyendo nombre/correo del usuario autenticado.
  - Envía correo de confirmación al usuario solicitante con folio y resumen del ticket.
- **Seguimiento administrativo de soporte (`/soporte-tecnico/eventos/`):**
  - Endpoint exclusivo de administrador para listar tickets y consultar su historial.
  - Permite actualizar estado (`NUEVO`, `EN_PROCESO`, `COMPLETADO`, `DESCARTADO`) y notas de seguimiento.
- **Administración de Roles (`asignar-rol`, `quitar-rol`):** Endpoints anidados explícitos.
- **Baja Lógica (`destroy()`):** El borrado establece `is_active=False` y nunca ejecuta borrado físico.

### 3.3 Otros ViewSets (`RolViewSet`, `PermisoViewSet`, Tablas intermedias)
- Exponen métodos estándar `list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`.
- En todos ellos, el método `destroy()` invoca `eliminar_logico()` proveniente de `ModeloBase`.
- `RolViewSet` posee acciones anidadas `asignar_permiso` y `quitar_permiso`.

---

## 4. Referencia de Endpoints API (`urls.py`)

A través del `DefaultRouter`, los recursos quedan estructurados así:

| Endpoint Base | Acción | Método | Descripción |
|--------------|--------|--------|-------------|
| `/api/usuarios/usuarios/csrf/` | Auth | GET | Obtiene Token CSRF para clientes Web. |
| `/api/usuarios/usuarios/iniciar-sesion/` | Auth | POST | Espera `{identificador, password}`. Crea sesión. |
| `/api/usuarios/usuarios/cerrar-sesion/` | Auth | POST | Cierra la sesión activa. |
| `/api/usuarios/usuarios/sesion-actual/` | Auth | GET | Retorna datos del perfil y sus permisos. |
| `/api/usuarios/usuarios/perfil-propio/` | Perfil | GET, PATCH | Gestión personal. Recibe `FormData` para imagen y validaciones de contraseña (`password_actual`, `password_nueva`, `password_confirmacion`). |
| `/api/usuarios/soporte-tecnico/solicitudes/` | Soporte | POST | Crea y guarda ticket de soporte, envía correo al canal técnico y correo de acuse al usuario con folio. |
| `/api/usuarios/soporte-tecnico/eventos/` | Soporte Admin | GET | Lista tickets de soporte para seguimiento administrativo (solo administrador). |
| `/api/usuarios/soporte-tecnico/eventos/{ticket_id}/` | Soporte Admin | PATCH | Actualiza estado y notas de seguimiento del ticket (solo administrador). |
| `/api/usuarios/usuarios/` | CRUD | GET, POST | Listar o crear usuarios administrativos. |
| `/api/usuarios/usuarios/{id}/` | CRUD | GET, PUT, PATCH, DELETE | Manipulación directa del usuario objetivo. |
| `/api/usuarios/usuarios/{id}/asignar-rol/` | Custom | POST | Asocia el rol. Requiere `{rol: <rol_id>}`. |
| `/api/usuarios/usuarios/{id}/quitar-rol/{rol_id}/`| Custom | DELETE | Remueve la relación. |
| `/api/usuarios/roles/` | CRUD | ALL | Catálogo de roles. |
| `/api/usuarios/roles/{id}/asignar-permiso/` | Custom | POST | Asocia el permiso al rol. Requiere `{permiso: <permiso_id>}`. |
| `/api/usuarios/roles/{id}/quitar-permiso/{id_permiso}/`| Custom | DELETE | Remueve permiso del rol. |
| `/api/usuarios/permisos/` | CRUD | ALL | Catálogo de permisos. |
| `/api/usuarios/rol-permisos/` | CRUD | ALL | Control directo de tabla intermedia. |
| `/api/usuarios/usuario-roles/` | CRUD | ALL | Control directo de tabla intermedia. |

**Ejemplo de Payload Exitoso (Iniciar Sesión)**:
```json
{
  "status": "success",
  "message": "Sesión iniciada correctamente.",
  "data": {
    "usuario": {
      "id": 1,
      "username": "admin",
      "nombre": "Super Administrador",
      "sucursal_id": null,
      "is_superuser": true,
      "requiere_cambio_password": false
    },
    "roles": [
      { "id": 1, "nombre": "Administrador" }
    ],
    "permisos": [
      { "id": 1, "codigo": "SUCURSAL_VER", "nombre": "Ver Sucursales" }
    ]
  }
}
```
