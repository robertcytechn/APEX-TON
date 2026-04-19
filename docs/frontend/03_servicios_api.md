# Documentación del Frontend: Capa de Servicios y API

Este módulo define la capa de comunicación HTTP (Axios) entre el frontend en Vue y el backend en Django. Su propósito es centralizar la gestión de errores, inyección de tokens de seguridad y la retroalimentación visual automática para el usuario.

---

## 1. Configuración Base (`service/api.js`)

Es la instancia central de Axios (`const api = axios.create(...)`). Todos los servicios de la aplicación deben importar y utilizar esta instancia en lugar de invocar a `axios` directamente.

### 1.1 Inyección de Seguridad (CSRF)
Django requiere un token CSRF para operaciones de mutación (`POST`, `PUT`, `PATCH`, `DELETE`).
- **Interceptor de Petición:** Antes de enviar una solicitud de mutación, verifica si el token (`csrftoken`) existe en las cookies del navegador. Si no existe, pausa la solicitud, hace un `GET /usuarios/csrf/` para obtenerlo e inyectarlo, y luego reanuda la petición original.

### 1.2 Manejo de Errores Globales y Caducidad de Sesión
- **Interceptor de Respuesta:** Si el backend responde con un `401 Unauthorized` o `403 Forbidden` (y no es un endpoint de login/sesión libre), el interceptor asume que la sesión caducó.
- **Acción:** Activa una bandera de bloqueo (`redireccionandoLogin`), borra el snapshot de Pinia en el `localStorage` e invoca al `router.replace('/auth/login')` para expulsar al usuario automáticamente, evitando que la UI quede en un estado roto.

---

## 2. Sistema de Notificaciones Automáticas (`notificacionesApi.js`)

Para evitar escribir repetitivamente `toast.add(...)` en cada vista después de hacer un `POST` o `PUT`, el frontend cuenta con un procesador global acoplado a la instancia de Axios.

### 2.1 Lógica de "Lista Blanca" (`REGLAS_LISTA_BLANCA_NOTIFICACIONES`)
Las notificaciones automáticas solo se disparan para rutas que implican cambios de estado (mutaciones) y que están dadas de alta en la lista blanca mediante expresiones regulares (`Regex`). Por ejemplo:
- `/cabina-arquitectura/`
- `/categorias/` o `/conceptos/`
- Operaciones en `/reportes-diarios/cerrar-actual/`
*Nota: Las lecturas (GET) son ignoradas silenciosamente para no abrumar al usuario.*

### 2.2 Extracción de Mensajes de Backend (`extraerMensajeError`)
Cuando ocurre un `HTTP 400 Bad Request`, el error suele venir en un JSON anidado (ej. `{"data": {"monto": ["Debe ser mayor a 0"]}}`). 
Esta utilidad:
1. Aplana el objeto de errores.
2. Limpia claves internas (como `non_field_errors`).
3. Concatena los errores en un mensaje legible (ej. "Monto: Debe ser mayor a 0 | Observaciones: Requerido").
4. Manda llamar al componente `<Toast>` global de PrimeVue a través de `agregarToast()`.

---

## 3. Servicios por Dominio (Patrón Wrapper)

Los endpoints del backend están mapeados en archivos aislados dentro de `service/` para separar la lógica HTTP de la lógica de los componentes `.vue`.

Ejemplos principales:
- **`autenticacionServicio.js`**: `iniciarSesion`, `cerrarSesion`, `obtenerSesionActual`.
- **`cabinaArquitecturaServicio.js`**: CRUD para los catálogos operativos, sucursales y usuarios de administración.
- **`capturaOperativaServicio.js`**: Recupera las categorías y conceptos disponibles para el contador, y envía los reportes diarios.
- **`estadoResultadosServicio.js`**: Obtiene los cierres mensuales o históricos.
