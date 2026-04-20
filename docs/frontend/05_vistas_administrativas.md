# Documentación del Frontend: Vistas Administrativas y Directivas

Este módulo agrupa todas las pantallas de gestión de catálogos y parámetros maestros (`/views/admin/` y `/views/director/`). La UI en esta capa se rige por el uso intensivo de componentes de tablas de datos (`DataTable` de PrimeVue), formularios modales (Diálogos) y validaciones estrictas.

---

## 1. Patrón de Diseño General (CRUD UI)

Prácticamente todas las vistas administrativas comparten una estructura arquitectónica común basada en Componentes de PrimeVue:
- **`DataTable`**: Renderización de listas con soporte para búsqueda, paginación local o remota.
- **`Toolbar`**: Botonera superior para invocar modales de creación (Ej. "Nueva Sucursal").
- **`Dialog`**: Modales superpuestos para formularios de Alta y Edición de un registro particular, manteniendo el contexto de la tabla detrás.
- **Manejo de Estados Locales (`ref`)**: Las vistas mantienen variables para `dialogVisible`, `registroEnEdicion` y arreglos como `listaSucursales` para hacer la vista reactiva ante respuestas exitosas de los servicios Axios.

---

## 2. Cabina de Arquitectura (`views/admin/`)

Destinado a la configuración profunda del sistema (Rol `ADMINISTRADOR`).

### 2.1 Gestión de Operaciones (`CatalogoOperativoAdmin.vue`)
La vista más compleja de la administración. Es una UI jerárquica para construir el flujo de caja:
- Configura las **Categorías Operativas** (Pestañas).
- Permite vincularle **Conceptos** a cada categoría.
- Permite construir dinámicamente **Detalles Parametrizados** (definiendo el `tipo_valor`: INT, DECIMAL, TEXT), los cuales el `CapturaOperativaCategoria.vue` usará para renderizar inputs extras al Contador.

### 2.2 Gestión de Personal y Accesos (`UsuariosAdmin.vue` y `RolesAdmin.vue`)
- `UsuariosAdmin`: Permite asignar perfiles de usuario, seleccionar su `Sucursal` base y vincularle un `Rol`.
- `RolesAdmin`: Asigna códigos de permiso granulares (ej. `autorizar_reembolso`) a un rol específico, lo cual después el `sesionStore` parsea vía `tienePermiso()`.

### 2.3 Contabilidad (`PadresRubrosContablesAdmin.vue` y `RubrosContablesAdmin.vue`)
- Construyen el árbol de jerarquías para el estado de resultados. Permiten prender o apagar la bandera `considerar_en_estado_resultados`.

### 2.4 Centro de Control (`CentroControlAdmin.vue`)
- Pantalla de alto riesgo. Invoca acciones masivas como cierres de mes forzados, reapertura de días cerrados y sincronización de tipos de cambio de emergencia.

---

## 3. Cabina Directiva (`views/director/`)

Estas vistas (ej. `SucursalesDirector.vue`, `UsuariosDirector.vue`) son versiones simplificadas y seguras de las de Administrador.

### 3.1 Patrón "Solo Lectura" (Read-Only)
- Se omite por completo el `Toolbar` de creación.
- No existen botones de acciones por fila (Editar / Borrar).
- La tabla (`DataTable`) sirve únicamente como un reporte visual con opciones para exportar a CSV o buscar, aprovechando los permisos `EsDirector` o `EsDirectorOAdministradorEnEscritura` del backend (que devuelven 403 si el Director intentara inyectar un POST/PUT malicioso saltándose la UI).

---

## 4. Tableros de Inicio por Rol (`views/pages/`)

La pantalla de Inicio dejó de usar una plantilla vacía y ahora resuelve componentes específicos por perfil.

### 4.1 `InicioAdministrador.vue` (Modo Dios)
- Consolida indicadores de operación anual (ingresos, egresos, neto, movimientos).
- Muestra conteo de usuarios/sucursales activas y estado de aplicación del Centro de Control.
- Incluye accesos rápidos a módulos críticos: Centro de Control, Usuarios, Sucursales y Catálogo Operativo.
- Usa carga resiliente con `Promise.allSettled`: si un módulo falla, los demás bloques sí se renderizan (carga parcial controlada).

### 4.2 `InicioDirector.vue` (Ejecutivo)
- Enfocado en análisis de negocio: recaudado por casino, ranking y tendencia diaria de ingresos/egresos.
- Consume `GET /estado-resultados/estadisticas/` con filtros por período para mostrar acumulados hasta fecha.
- Presenta visualización directa de desempeño por sala para toma de decisiones.
- Optimiza rendimiento inicial: período por defecto "Año en curso" y muestreo de series largas para evitar bloqueos al renderizar gráficas masivas.

### 4.3 `SoporteTecnico.vue`
- Reemplaza el acceso previo a página no encontrada dentro del menú de Soporte.
- Muestra formulario de ticket para cualquier usuario autenticado.
- La tarjeta de responsable con datos de contacto (nombre, teléfonos y correos) solo es visible para `DIRECTOR` y `ADMINISTRADOR`.
- Incluye formulario de ticket con selectores de problema/áreas/comportamiento y descripción detallada.
- Envía solicitudes al endpoint `POST /usuarios/soporte-tecnico/solicitudes/`, incluyendo datos del usuario autenticado.
- Acceso habilitado para cualquier perfil con sesión activa.

### 4.4 `SoporteTecnicoAdmin.vue`
- Vista exclusiva de `ADMINISTRADOR` para operar la bandeja de tickets de soporte.
- Muestra histórico de eventos con folio, solicitante, problema, prioridad y estado de seguimiento.
- Permite filtrar por estado, buscar por texto y abrir detalle de cada ticket.
- Incluye flujo de seguimiento para actualizar estado (`NUEVO`, `EN_PROCESO`, `COMPLETADO`, `DESCARTADO`) y registrar notas internas.
