# Estándares y Arquitectura de la API (Backend)

## Modularidad
- Cada módulo lógico debe separarse en su propia aplicación de Django (ej. módulo de inventario $\rightarrow$ app `inventario`).

## Estandarización de Respuestas JSON
- **Regla Estricta:** Todas las respuestas de la API deben seguir una estructura JSON estandarizada.
- **Estructura Obligatoria:**
  ```json
  {
    "status": "success",
    "message": "Operación exitosa",
    "data": {} 
  }
  ```

## Autenticación y Permisos
- **Autenticación:** Utilizar **sesiones nativas de Django** (`session auth`). **PROHIBIDO usar JWT.**
- **Módulo de Usuarios:** App dedicada llamada `usuarios` con los modelos: `Usuario`, `Rol`, `Permiso`, `Usuario_Rol`, `Rol_Permiso`.
- **Gestión de Permisos:** Los permisos se asignan estrictamente **por Rol**, nunca por usuario individual.
- **Integración Frontend:** Usar `Axios Interceptors` en Vue para gestionar errores de sesión y almacenar permisos del rol en el cliente para control de renderizado.

## Trazabilidad y Auditoría
- **Modelo Base:** Todos los modelos dependientes (transaccionales) DEBEN heredar de un `ModeloBase` abstracto.
- **Campos Obligatorios:**
  - `creado_en`, `actualizado_en`, `eliminado_en`
  - `creado_por`, `actualizado_por`, `eliminado_por`
  - `valor_anterior`, `valor_actual`

## Desarrollo de Módulos DRF
- **Implementación Concurrente:** Al crear una app o modelo, se deben programar simultáneamente sus Serializadores, Vistas (preferentemente ViewSets) y enrutadores (URLs).
- **Auto-documentación:** Es obligatorio agregar el atributo `help_text` a todos los campos de los modelos para soporte óptimo en DRF.
