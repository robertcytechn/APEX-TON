# Documentación del Frontend: Gestión de Estado (Pinia)

Este documento explica cómo el frontend maneja su memoria temporal y reactividad cruzada utilizando **Pinia** como store global. Los stores están separados por dominio de negocio y encapsulan toda la lógica de caché, validación de permisos y personalización de interfaz.

---

## 1. Store de Sesión (`stores/sesion.js`)

Es el "cerebro" de seguridad del frontend. Administra la autenticación, los roles en memoria y las reglas de autorización del usuario activo.

### 1.1 Persistencia e Hidratación
- Para evitar que la sesión se pierda al presionar F5 (recargar), utiliza el `localStorage` (clave `binsurmx_sesion`) para guardar un *snapshot* del usuario, roles y estado de autenticación.
- La acción `_cargarSesionLocal()` hidrata el store antes de que el router bloquee la pantalla inicial.

### 1.2 Reglas de Evaluación de Roles
Las comprobaciones de seguridad no comparan los roles de forma estricta (case-sensitive) para evitar falsos negativos por espacios o acentos:
- **`normalizarTexto`**: Quita tildes, espacios en blanco y convierte a mayúsculas antes de comparar.
- **`evaluarAccesoPorRol`**: Es el motor de decisiones. Soporta meta-roles dinámicos como:
  - `AUTENTICADO`: Cualquier usuario con sesión.
  - `SUPERUSUARIO` / `STAFF`: Propiedades directas del objeto usuario.
  - `ADMINISTRADOR`: Considera como admin a cualquier persona con el alias "ADMIN", "ADMINISTRADOR", o si es `is_superuser`.

### 1.3 Acciones Clave
- `iniciarSesion(payload)`: Llama a la API (`autenticacionServicio`), parsea roles/permisos, levanta banderas y guarda en `localStorage`.
- `verificarSesionActual()`: Petición silenciosa a la API para validar que la cookie/sesión del backend sigue viva.
- `cerrarSesion()`: Llama a la API para destruir la cookie e invoca `limpiarSesionLocal()` para barrer la memoria.

### 1.4 Getters Críticos (Reactividad)
Estos son usados intensivamente por el Router y los botones de la Interfaz:
- `tienePermiso(codigoPermiso)`: Retorna bool.
- `cumpleAlgunoRoles(rolesRequeridos)`: Retorna bool basado en intersección.
- `esContadorOGerente`, `esAdministrador`: Atajos directos para no ensuciar vistas.

---

## 2. Store de Preferencias de Usuario (`stores/preferenciasUsuario.js`)

Se encarga de sincronizar las elecciones visuales del usuario (ej. modo oscuro) entre tres entornos: El layout de PrimeVue (`layoutConfig`), la memoria de Pinia, y la base de datos (Backend).

### 2.1 Mapeo de Colores PrimeVue
La función `mapearColorAcento` convierte colores de diseño puro (ej. `emerald`, `teal`) a un catálogo semántico en español (`verde`, `azul`, `rojo`) para guardar de forma limpia en la API de configuración.

### 2.2 Sincronización en Tiempo Real
- **Carga (`cargarConfiguracionUsuario`)**: Llama al servicio `obtenerMiConfiguracionUsuario` de la API y muta las propiedades de `layoutConfig` (ej. `layoutConfig.darkTheme`, `layoutConfig.primary`).
- **Debounce de Guardado (`programarGuardadoVisual`)**: Al dar clic para cambiar el modo oscuro, el efecto en UI es inmediato, pero la llamada a la API (`guardarConfiguracionVisual`) se retrasa 450ms. Esto previene saturar el backend si el usuario hace clics muy rápidos en el menú de temas.

---

## 3. Store de Categorías Operativas (`stores/categoriasOperativas.js`)

Centraliza la obtención de las "pestañas" o flujos de caja habilitados, vital para los perfiles de `CONTADOR` o `GERENTE`.

### 3.1 Prevención de Llamadas Redundantes
Implementa un seguro anti-spam (caché) mediante los flags `cargando` y `cargadas`. 
- Si múltiples vistas o componentes solicitan llamar a `cargarCategoriasActivas()`, el store ignora la petición a menos que el parámetro `forzar` sea verdadero, evitando saturar la API.

### 3.2 Construcción Dinámica de Rutas (`getters.rutasCapturaOperativa`)
Toma la respuesta cruda de la API (`categoriasActivas`) y fabrica objetos de navegación listos para inyectarse en el menú de la aplicación:
- Genera la propiedad `ruta`: `/operativo/{id}`.
- Genera la `etiqueta`: nombre de la categoría.
- Inyecta un **ícono semántico** (`pi-arrow-down-left` para INGRESOS, `pi-arrow-up-right` para EGRESOS) evaluando dinámicamente el `tipo` de la categoría.
