# Documentación del Frontend: Arquitectura y Navegación

Este documento detalla la estructura base, el punto de entrada, el enrutamiento y la construcción dinámica de la interfaz principal (Layout) del proyecto APEX-TON (Vue.js).

---

## 1. Punto de Entrada (`main.js` y `App.vue`)

### `main.js`
Es el archivo de inicialización de la aplicación Vue 3. 
- **Gestión de Estado:** Registra `pinia` de forma centralizada.
- **Enrutamiento:** Inyecta el `router` global.
- **UI Framework (PrimeVue):** Inicializa PrimeVue utilizando el sistema de diseño moderno **Aura** con soporte para modo oscuro (`darkModeSelector: '.app-dark'`).
- **Servicios Globales:** Registra `ToastService` y `ConfirmationService` para notificaciones y diálogos en toda la app.

### `App.vue`
Actúa como el nodo raíz del DOM. 
- Inyecta el componente global `<Toast />` para permitir que el servicio de notificaciones dispare alertas visuales.
- Renderiza el `<router-view />` principal de mayor nivel.
- Ejecuta `registrarInstanciaToastApi(toast)` para que la capa de red (Axios) pueda disparar errores visuales sin importar en qué vista se encuentre el usuario.

---

## 2. Enrutamiento y Seguridad (`router/index.js`)

El archivo de configuración de Vue Router no solo define los endpoints del frontend, sino que actúa como un **guardia de seguridad estricto (Navigation Guard)**.

### 2.1 Definición de Rutas (Jerarquía)
Las rutas están agrupadas bajo un componente de presentación (Layout):
- **Raíz (`/`)**: Utiliza `AppLayout.vue` como plantilla, que a su vez renderiza un `router-view` hijo para las vistas internas.
- **Páginas de Error/Login**: Se renderizan fuera de `AppLayout.vue` (ocupan pantalla completa).

### 2.2 Metadatos Críticos de las Rutas (`meta`)
Cada ruta especifica su nivel de acceso mediante atributos `meta`:
- `publica: true`: No exige token de sesión (ej. Login, Mantenimiento).
- `requiereSesion: true`: Obliga al usuario a estar logueado.
- `requiereRoles: ['DIRECTOR', 'ADMINISTRADOR']`: Verifica contra el array de roles del usuario en el store.
- `requiereAdmin: true`: Verifica el flag `esAdministrador` del store.

### 2.3 Guardia de Navegación (`router.beforeEach`)
Antes de cada cambio de página, se ejecuta una cadena de validaciones de seguridad:
1. **Estado de Mantenimiento:** Sincroniza la variable global `ESTADO_APLICACION`. Si el backend está cerrado, redirige forzosamente a `/mantenimiento` (a menos que exista un Bypass explícito).
2. **Restauración de Sesión:** Verifica si hay un token persistido (`localStorage`). Si la sesión no ha sido verificada en memoria, invoca a `sesionStore.verificarSesionActual()`.
3. **Flujo de Contraseña:** Si el usuario es nuevo y su flag `requiereCambioPassword` es `true`, lo encierra en la ruta `/pages/perfil#seguridad` obligándolo a definir una clave.
4. **Validación de Roles:** Rechaza intentos de acceso a módulos no permitidos enviando al usuario a `/auth/access` (Página 403).
5. **Redirección Dinámica Operativa:** Si un `CONTADOR` o `GERENTE` accede a la ruta base `/operativo`, el router invoca `obtenerPrimeraRutaOperativa()` y lo redirige automáticamente a la primera pestaña de categoría operativa que tenga habilitada.

---

## 3. Arquitectura del Layout (`layout/`)

El Layout (`AppLayout.vue`) es la estructura visual compartida por casi todas las pantallas internas de la aplicación. Se compone de 3 áreas principales:

### 3.1 `AppTopbar.vue` (Barra Superior)
- Muestra el nombre y avatar inicial del usuario logueado.
- Contiene el menú contextual (`Menu`) para "Mi perfil", "Seguridad" y "Cerrar sesión".
- Ofrece un botón (`alternarModoOscuro`) que llama a `toggleDarkMode()` e interactúa con el `preferenciasUsuarioStore` para guardar la elección en el backend.
- Invoca al componente `<AppConfigurator />` que permite modificar la paleta de colores (`color_acento`) y tamaño de fuente (`tamano_fuente`).

### 3.2 `AppSidebar.vue` y `AppMenu.vue` (Menú Lateral Dinámico)
- El Sidebar envuelve al `AppMenu.vue`, cuyo arreglo lógico de navegación (`model`) es **reactivo e inteligente**.
- El arreglo del menú se construye evaluando dinámicamente:
  - `sesionStore.cumpleAlgunoRoles(['ADMINISTRADOR'])`: Muestra el bloque "Cabina de Arquitectura" (Usuarios, Sucursales, Catálogos).
  - `sesionStore.cumpleAlgunoRoles(['DIRECTOR'])`: Muestra la "Cabina Director" (Modo solo lectura).
  - `sesionStore.cumpleAlgunoRoles(['CONTADOR', 'GERENTE'])`: Llama al `categoriasOperativasStore` para obtener las pestañas del día y renderizar un link por cada categoría activa.
- Utiliza recursividad mediante el componente `<AppMenuItem />` para pintar links (`to`), íconos de PrimeIcons y separadores.

### 3.3 `AppFooter.vue`
- Elemento sencillo al final del contenedor principal. Muestra los créditos de BinsurMX.
