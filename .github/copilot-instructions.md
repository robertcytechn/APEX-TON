## 2. Stack Tecnológico

El proyecto está dividido en un Backend robusto (API REST) y un Frontend reactivo, orientado a un entorno móvil

### 2.1. Backend
- **Lenguaje:** Python 3.13
- **Framework:** Django 5.2
- **API REST:** Django REST Framework (DRF)
- **Base de Datos:** MySQL

### 2.2. Frontend
- **Framework Core:** Vue.js 3
- **Gestión de Estado:** Pinia
- **Cliente HTTP:** Axios
- **Herramienta de Build:** Vite
- **Tipado:** TypeScript
- **UI & Estilos:** PrimeVue v4.0 (o superior), PrimeFlex, Tailwind CSS v4, Tema Sakai.

## 3. Normativas Generales de Desarrollo

- **Lenguaje Obligatorio:** Todo el desarrollo (nombres de variables, funciones, clases, comentarios y documentación) DEBE estar exclusivamente en **Español de México**.
- **Interfaz de Usuario:** Cualquier texto, alerta o elemento que el usuario final pueda ver debe escribirse en español.
- **Control de Versiones:** Uso estricto de **Git** y **GitHub** para el manejo del código fuente.
- **Revisión y ejecución:** Antes de cualquier cambio revisa backend y frontend para entender la lógica y el funcionamiento del sistema, no hagas cambios sin entender el impacto que pueden tener en el sistema. si modificas o actualizas backend asegurate tambien de alterar views y serializers correspondientes para que el sistema siga funcionando correctamente, si modificas o actualizas frontend asegurate de revisar que los cambios no afecten la experiencia del usuario y que no rompan la interfaz, revisa que los cambios sean consistentes con el diseño y la arquitectura del sistema tambien menu lateral y oruter

## 4. Estándares y Arquitectura de la API (Backend)

### 4.1. Modularidad
- Separar cada módulo lógico en su propia app de Django (Ej. un módulo de inventario deberá estar en la app `inventario`).

### 4.2. Estandarización de Respuestas JSON
- **Regla Estricta:** Todas las respuestas de la API de Django deben devolver una estructura JSON estandarizada. No se permiten respuestas escuetas.
- **Estructura Obligatoria:**
  ```json
  {
    "status": "success",
    "message": "Operación exitosa",
    "data": {} // Objeto o array de objetos correspondientes a la consulta
  }
  ```

### 4.3. Autenticación, Autorización y Permisos
- **Autenticación:** Utilizar **sesiones nativas de Django** (`session auth`). **NUNCA usar JWT.**
- **Módulo de Usuarios:** Se debe usar una app propia llamada `usuarios` que contenga los modelos: `Usuario`, `Rol`, `Permiso`, `Usuario_Rol`, `Rol_Permiso`.
- **Gestión de Permisos:** Los permisos SIEMPRE deben asignarse **por Rol**, nunca por usuario individual (prohibido usar permisos por usuario individualmente).
- **Integración con Frontend:** En Vue, usar `Axios Interceptors` para capturar errores de sesión/autorización y guardar los permisos del rol en cliente para el control de renderizado y acciones.

### 4.4. Trazabilidad y Modelo Base
- **Regla Estricta:** Todos los modelos dependientes (o clases de la BD que manejen transaccionalidad) DEBEN heredar de un `ModeloBase` abstracto.
- **Campos Obligatorios de Auditoría en ModeloBase:**
  - `creado_en`, `actualizado_en`, `eliminado_en`
  - `creado_por`, `actualizado_por`, `eliminado_por`
  - `valor_anterior`, `valor_actual`

### 4.5. Flujo de Creación de Apps y Modelos
- **Módulos DRF Completos:** Cada vez que se crea una nueva aplicación o modelo, es una regla estricta que deben programarse concurrentemente sus correspondientes Serializadores, Vistas (Views - preferentemente ViewSets de DRF) y enrutadores (URLs). No deben dejarse modelos huérfanos sin sus endpoints.
- **Auto-documentación (help_text):** Es obligatorio agregar el atributo `help_text` a absolutamente todos y cada uno de los campos declarados dentro de cualquier modelo. Esto para el óptimo soporte y funcionamiento del esquema en el Django REST Framework.

## 5. Arquitectura Lógica de la Base de Datos

### 5.1. Tablas Globales Maestras
Estas tablas no dependen de lógicas divisionales y son pilares del sistema global:
- `configuraciones_globales`
- `rubro_contable`
- `roles`
- `permisos`
- `sucursales`
- `modelobase` (Abstracto)
- `fondos_fijos`

### 5.2. Relaciones Fundamentales
- La tabla principal de `usuarios` hereda de `modelobase` y posee relaciones directas con `sucursal` y `roles`.
- Las preferencias de interfaz se reservan en `configuraciones_de_usuario` (hereda de `modelobase`, relacionada con `usuarios`).
- Cada `sucursal` hereda de `modelobase` e incluye su conexión de `fondos_fijos`.
- **Rubro Contable y Caja Chica:** `rubro_contable` existe globalmente para homologar perfiles de ingresos/egresos en todo el negocio. No obstante, `fondos_fijos` funciona de manera estricta e independiente por cada sucursal.

## 6. Reglas de Negocio: Control Operacional de Tesorería

El núcleo transaccional del sistema es migrar, asimilar y estandarizar la lógica del archivo matriz operativo (`CAJA MUESTRA.xlsx`). El sistema **no debe concebirse como un producto contable estricto**, sino como un registro de transacciones diarias para auditar el movimiento de dinero físico en la sala de juegos. 
*Nota de contexto*: Si el dinero va a bancos se registra como **Egreso** (porque sale de la caja de sala), en contraparte, si la sala se surte de bancos se registra como **Ingreso**.

### 6.1. Pestañas de Agrupación de Flujo
El sistema organizará el flujo categorizando la información en divisiones conocidas como "Pestañas". Las pestañas activas incluyen:
`ADMINISTRACION`, `BOOK`, `BILLPOCKET`, `BAHIA BANORTE`, `BANORTE AHIS`, `BBVB BANCOMER`, `DOLARES`, `PERDIDAS`, `PERMISO`, `SOBRANTES`, `POR COMPROBAR`, `MAQUINAS`, `CAJA CHICA MORELIA`, `COMPARATIVO`, `PRESUPUESTO`, `MAQUINEROS`, `JUEGO VIVO`, `F. fijos`.

### 6.2. Relación de Conceptos 
- **Concepto:** Son las nomenclaturas dadas a movimientos específicos (ej. "VENTA DE CAFE"). 
- Cada concepto **pertenece invariablemente a una única pestaña** y al mismo tiempo está **conectado al `rubro_contable` global** (ej. "VENTAS_BEBIDAS").

### 6.3. Detalles Parametrizados de Pestañas
- Las pestañas requieren información contextual sobre quién, cómo y el origen del movimiento operado por sala (Ej: Pestaña `Sobrantes` documenta monto exacto, responsable y el área que causó el sobrante monetario).
- Para variables monetarias, usar tipos nativos decimales o flotantes de doble precisión (SIEMPRE usar decimales para representar valores en moneda).

### 6.4. Consolidación: Estado de Resultados Automático
El principal objetivo funcional de estructurar pestañas, conceptos y rubros, es la capacidad de generalizar y consolidar toda la operación de ingresos (fondos entrantes a sala o recaudo) frente a los egresos (salida a banco o pagos) en el **Estado de Resultados**, produciéndolo de forma autónoma, fidedigna y completamente en tiempo real a nivel sistémico.

### 7. Reglas de Negocio: Control historico
- la tabla o app libro_estado_resultados es un registro historico de los movimientos que se han realizado en la sala de juegos por mes
- si modificamos el cambio de divisas en configuracion global no se deben de modificar los registros historicos, ya que estos ya fueron guardados con el cambio de divisas que existia en el momento de la transaccion.

### 8. Reglas de Negocio en comportamiento
 - abra tipos de roles 
          * CONTADOR: es el encargado de llenar los campos de las pestañas que requieren de un registro historico, como lo son las pestañas de "POR COMPROBAR", "MAQUINAS", "CAJA CHICA MORELIA", "PRESUPUESTO", "MAQUINEROS", "JUEGO VIVO" solo podra hacer esp
          * GERENTE: tendra los mismos permisos que el contador (por ahora)
          * DIRECTOR: solo podra ver resportes del estado de resultados y comparativos por dia semana mes y año o un filtro personalizado, no podra editar ningun campo de las pestañas historicas graficos y tablas, solo podra ver los datos y exportarlos en pdf o excel, ajustar algunos parametros ejemplo configuraciones globales, fondos fijos para cada casino
          * ADMINISTRADOR: administracion total del sistema en este caso (yo)
- el sistema debe de tener en configuraciones globales un campo "HORARIO_APERTURA" y "HORARIO_CIERRE" que seran las horas en las que se abriran y cerraran las pestañas, fuera de este horario no se podra modificar
- el sistema debe de cerrar el dia creando o cerrando el historico diario y si es fin de mes cerrar el historico de estado de resultados
- el dia contable es un dia anterior ejemplo si hoy es 20 de marzo el dia contable es 19 de marzo


## reglas de estilo de frontend
- siempre usar tailwind para estilos y los componentes mas nuevos de primevue v4 o el mas actual disponible
- no modificar tailwind ni primevue, solo usar sus clases y componentes en caso de necesitar estilos personalizados crear una clase en el archivo style.css
- mantener siempre un modo de trabajo movil first, es decir, que la interfaz se adapte primero a dispositivos moviles y luego a pantallas mas grandes pero manteniendo botones ordenados y accesibles, que no se deformen de tamaño ni se vean mal en ningun dispositivo
- para campos de imput donde sea posible agruparlos o encerrarlos en su propio form para que se vean ordenados y accesibles y para que funcionen los accesos rapidos de teclado de forma nativa
- acomodo de carpetas por rol ejemplo todo loq ue el administardor peude hacer o ver colocarlo en la carpeta admin, todo lo que el contador puede hacer o ver colocarlo en la carpeta contador, todo lo que el director puede hacer o ver colocarlo en la carpeta director ya te ire indicando en que carpeta lo haremos todo esto en la carpeta views
- en cualquier formulario mostrar siempre indicador visual de campo requerido u opcional en la etiqueta (ejemplo: * obligatorio o texto opcional)
- en inputs y selects agregar iconos semanticos y placeholder descriptivo en espanol para mejorar captura y legibilidad
- todo campo monetario debe iniciar y capturarse en formato monetario explicito con 2 decimales (ejemplo: 0.00), no dejar campos vacios para montos
- todo monto mostrado al usuario debe representarse con separador de miles y 2 decimales (ejemplo: 1,450,640.50)
- todo monto mostrado al usuario debe usar segmentacion visual por colores para lectura rapida: cada bloque de miles con color distinto y la parte decimal con color diferenciado
- para cualquier tabla, tarjeta, reporte o resumen que muestre dinero (movimientos, estado de resultados, fondos, ingresos, egresos), usar siempre el componente `MontoMonedaColoreado`
- en formularios con campos monetarios, agregar vista previa coloreada del monto capturado para validar lectura antes de guardar
-a todas las datatables hay que agregar mas dise;o y configuracion ejemplo ver/ocultar columnas reacomodo o reordenamiento de columnas, seleccion de datos mostrados 10,20,50,todos etc
- en todas las datatables, al dar clic en el encabezado de la columna se debe permitir ordenamiento ascendente/descendente, aplicando orden alfabetico o numerico segun corresponda al tipo de dato
- en todos los campos de seleccion de formularios (Select, MultiSelect o equivalentes), habilitar siempre buscador/autocompletado para facilitar la captura y evitar listas largas sin filtro