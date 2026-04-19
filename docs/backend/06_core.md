# Documentación del Módulo: Core (Base y Abstracciones)

Este documento detalla la estructura y propósito del módulo `core`. A diferencia de otras aplicaciones, `core` no posee endpoints expuestos a la API; es una librería de infraestructura interna. Provee clases abstractas, permisos globales y utilidades que estandarizan el comportamiento de todas las entidades transaccionales del backend.

---

## 1. Arquitectura de Modelos (`models.py`)

La piedra angular de la persistencia en el sistema es `ModeloBase`. Todo modelo transaccional y de configuración (excepto tablas intermedias muy simples o modelos nativos) debe heredar de esta clase abstracta.

### 1.1 `ModeloBase` (Clase Abstracta)
Provee de forma nativa a todas las entidades heredadas un sistema de auditoría, máquina de estados y borrado lógico.

- **Máquina de Estados (`estado`):** 
  - Todo registro nace en estado `ACTIVO`.
  - Soporta transiciones explícitas a `INACTIVO`, `BLOQUEADO` y `ELIMINADO`.
- **Auditoría Temporal:**
  - `creado_en`: Timestamp inmutable de creación.
  - `actualizado_en`: Timestamp autogestionado por Django en cada `.save()`.
  - `eliminado_en`: Timestamp de borrado lógico (Soft Delete).
- **Auditoría de Usuarios (Trazabilidad):**
  - `creado_por`, `actualizado_por`, `eliminado_por`: ForeignKeys hacia el modelo `Usuario` con regla `on_delete=models.SET_NULL` para evitar pérdida de datos si se borra al empleado.
- **Auditoría de Valores (Histórico Fino):**
  - `valor_anterior` y `valor_actual`: Campos JSON previstos para llevar trazabilidad de cambios en operaciones críticas que no usen `simple_history`.
- **Métodos de Ciclo de Vida:**
  - En lugar de manipular campos directamente, los modelos dependientes pueden llamar a `.activar()`, `.desactivar()`, `.bloquear()` o `.eliminar_logico(usuario)`.
  - El método nativo `.delete()` de Django está sobreescrito. **Un llamado a `.delete()` nunca borra físicamente la fila, fuerza el llamado a `.eliminar_logico()`.**

### 1.2 `ModeloBaseManager`
Es el *Manager* predeterminado (`objects`) inyectado en `ModeloBase`.
- **Propósito:** Sobreescribe `get_queryset()` inyectando automáticamente `.filter(eliminado_en__isnull=True)`.
- **Impacto:** Cualquier consulta como `Sucursal.objects.all()` jamás devolverá registros eliminados lógicamente, previniendo errores de desarrolladores. 
- Para acceder a los eliminados, se debe invocar al manager secundario: `ModeloBase.todos.all()`.

---

## 2. Permisos y Reglas de Negocio (`permisos.py`)

Centraliza la lógica de autorización (DRF Permissions) asegurando un control de acceso uniforme en todo el sistema.

### 2.1 Control de Horarios Operativos (`VentanaHorariaPermiso`)
Este permiso es vital para la seguridad financiera de la caja operativa.
- **Lógica (`sistema_dentro_de_horario`):** Consulta en vivo las variables globales `HORARIO_APERTURA` y `HORARIO_CIERRE` y las compara contra el reloj interno del servidor (`timezone.now()`). Soporta cruce de medianoche.
- **Aplicación:** Si la solicitud es un método de escritura (`POST`, `PUT`, `PATCH`, `DELETE`) y está fuera de horario, la rechaza con un `403 Forbidden` y un mensaje claro para el usuario. Las lecturas (`GET`) siempre pasan.

### 2.2 Control de Roles (`usuario_tiene_rol`)
La función helper `usuario_tiene_rol` resuelve los privilegios leyendo la tabla intermedia `UsuarioRol` y aplicando reglas amigables (ignora mayúsculas/minúsculas). Además, otorga implícitamente acceso total si `is_superuser` es True. 

Con base en este helper se declaran las siguientes clases de permisos DRF:
- **`EsAdministrador`**: Acceso restringido al rol "ADMINISTRADOR" (o alias como "ADMIN", "ADMINISTRACION"). Usado en cierres contables o reseteos críticos.
- **`EsDirector`**: Acceso restringido al rol "DIRECTOR" para tableros ejecutivos.
- **`EsDirectorOAdministrador`**: Autoriza a cualquiera de los dos perfiles.
- **`EsDirectorOAdministradorEnEscritura`**: Un permiso híbrido. Permite `GET` a cualquier usuario autenticado, pero exige perfil directivo o administrativo para peticiones de mutación (`POST`, `PUT`, `PATCH`, `DELETE`). Es muy utilizado en catálogos como `CategoriaOperativa` o `FondosFijos`.

---

## 3. Guía de Uso Interno

**¿Cómo proteger un nuevo ViewSet?**
```python
from core.permisos import EsAdministrador, VentanaHorariaPermiso

class NuevoModuloViewSet(viewsets.ViewSet):
    # Proteger toda la vista con autenticación, permisos de admin y reloj operativo
    permission_classes = [IsAuthenticated, EsAdministrador, VentanaHorariaPermiso]
```

**¿Cómo crear una nueva entidad rastreable?**
```python
from core.models import ModeloBase

class EntidadNueva(ModeloBase):
    nombre = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'entidad_nueva'
```
*Al heredar de `ModeloBase`, `EntidadNueva` automáticamente gana campos de control, protección contra soft-delete y métodos de ciclo de vida.*
