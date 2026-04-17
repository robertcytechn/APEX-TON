Version del sistema: 2.32.0

## Historial de Versiones

- Fecha: 2026-04-17
- Version: 2.32.0
- Autor: Cy tamayo
- Descripcion: Se adapto la configuracion real de Apache para produccion con redireccion HTTP a HTTPS (cytechn.ddns.net), activacion de SSL en el vhost 443, rutas proxy de backend bajo /apex/api y /apex/admin, bloqueo de listado de directorios (Options -Indexes) y uso de paginas de error personalizadas alojadas junto con la aplicacion en /apex/errores.

- Fecha: 2026-04-16
- Version: 2.31.0
- Autor: Cy tamayo
- Descripcion: Se configuro Apache (httpd y vhost) para reforzar seguridad y experiencia de errores en despliegue, desactivando listado de directorios (Index off) y agregando paginas personalizadas para errores 404 (no encontrado), 500/502/503/504 (servidor) y 401/403 (acceso no autorizado), incluyendo uso de ProxyErrorOverride para respuestas del backend proxied bajo /apex.

- Fecha: 2026-04-16
- Version: 2.30.0
- Autor: Cy tamayo
- Descripcion: Se implemento el nuevo Centro de Control exclusivo para ADMINISTRADOR con seguridad dual (router frontend + permisos backend), incluyendo un formulario operativo para gestionar variables del estado de aplicacion con selectores y plantillas predefinidas, gatillos manuales para las tareas Celery activas del modulo reportes_diarios (cierre diario, resumen diario, cierre mensual, sincronizacion de horario y respaldo BD), y un tablero de salud del servidor con metricas de CPU/RAM/disco, estado de base de datos y disponibilidad de workers Celery.

- Fecha: 2026-04-16
- Version: 2.29.0
- Autor: Cy tamayo
- Descripcion: Se refactorizo el control de mantenimiento para consumir en tiempo real las variables de ConfiguracionesGlobales (estado, titulo, mensaje, etiqueta, icono, decoradores, recomendaciones, inicio y fin de actualizacion), eliminando la dependencia de ajustes manuales en archivo; se agrego liberacion automatica local a produccion al alcanzar FIN_ACTUALIZACION y un bypass de contingencia por atajo de teclado en dos pasos (Ctrl+Alt y dentro de 1 segundo Ctrl+Alt+Y) para permitir acceso operativo temporal sin editar base de datos.

- Fecha: 2026-04-16
- Version: 2.28.0
- Autor: Cy tamayo
- Descripcion: Se agrego en ConfiguracionGlobal la bandera visible_para_director para controlar si una variable global puede ser consultada y editada en la cabina de DIRECTOR; se actualizo backend (modelo, migracion, serializers y filtros de API) para que director solo vea/edite variables habilitadas por administracion, y se modifico frontend de cabina ADMINISTRADOR y DIRECTOR para capturar y reflejar este control de acceso por variable.

- Fecha: 2026-04-16
- Version: 2.27.0
- Autor: Cy tamayo
- Descripcion: Se elimino el saldo inicial global por sucursal y se migro el control a saldo inicial mensual por categoria con arrastre automatico, incorporando en backend el campo usa_saldo_inicial en categoria operativa, el nuevo modelo de saldo mensual por sucursal/categoria con bloqueo de edicion, endpoints dedicados para consulta y captura manual inicial, y en frontend la limpieza total de fondo_inicial en cabinas de sucursales (admin/director), el nuevo check de uso de saldo inicial en catalogo operativo y el panel de captura operativa para gestionar saldo inicial mensual por categoria.

- Fecha: 2026-04-16
- Version: 2.26.0
- Autor: Cy tamayo
- Descripcion: Se completo el onboarding de usuarios operativos de cabina director con envio de correo reutilizable en alta y reinicio de contrasena (plantilla HTML/TXT con usuario, contrasena visible y enlaces a dashboard/login), se agrego bandera de primer inicio para forzar cambio de contrasena, se incluyo bloqueo backend para impedir continuar sin actualizar contrasena, se reforzo el guard global/frontend con redireccion automatica a perfil y alerta roja obligatoria, y se habilito en cabina director la edicion de usuarios junto con accion de reiniciar password en un clic con nuevo envio de credenciales.

- Fecha: 2026-04-16
- Version: 2.25.0
- Autor: Cy tamayo
- Descripcion: Se implemento la nueva cabina de administracion exclusiva para DIRECTOR con rutas y menu dedicados en frontend (sucursales con asistente paso a paso y asignacion automatica de fondos fijos, alta de usuarios operativos CONTADOR/GERENTE con una sola sucursal, un solo rol, correo obligatorio, estado activo por defecto y contrasena aleatoria de 8 digitos mostrada al crear, edicion de configuraciones globales limitada solo al valor, alta/edicion de rubros contables con padre y tipo obligatorios, y acceso al catalogo operativo en formato amigable), ademas de endurecer reglas de backend con endpoints dedicados para director y bloqueo de escrituras de catalogo operativo/fondos a roles DIRECTOR o ADMINISTRADOR.

- Fecha: 2026-04-16
- Version: 2.24.0
- Autor: Cy tamayo
- Descripcion: Se robustecio la tarea Celery de respaldo de base de datos para ejecutar mysqldump local, comprimir automaticamente el resultado en formato configurable (gz/zip), enviar notificacion SMTP de exito con archivo adjunto cuando no supera 25 MB, y disparar correo de alerta en caso de fallo del respaldo o del envio principal.

- Fecha: 2026-04-16
- Version: 2.23.0
- Autor: Cy tamayo
- Descripcion: Se habilito operacion de tareas programadas con RabbitMQ para Windows Server, agregando sincronizacion dinamica del envio diario de correos ejecutivos desde ConfiguracionGlobal.HORARIO_CIERRE, programacion mensual fija el dia 1 a las 08:00, respaldo completo diario de base de datos a las 23:59 mediante tarea Celery y script unico PowerShell para levantar waitress, worker y beat en una sola ejecucion.

- Fecha: 2026-04-16
- Version: 2.22.0
- Autor: Cy tamayo
- Descripcion: Se completo la limpieza de branding y persistencia en frontend para operar solo con BinsurMX, eliminando compatibilidad legacy de llaves locales binsur_mx en store de sesion, guard global de rutas e interceptor API.

- Fecha: 2026-04-16
- Version: 2.21.0
- Autor: Cy tamayo
- Descripcion: Se homologo integralmente el branding del frontend a BinsurMX, actualizando textos visibles (titulo principal, topbar, login y footer), estandarizando identificadores tecnicos de sesion/exportacion en cliente y manteniendo compatibilidad de lectura con llaves locales legadas para no romper sesiones existentes.

- Fecha: 2026-04-16
- Version: 2.20.0
- Autor: Cy tamayo
- Descripcion: Se configuraron los correos ejecutivos para tomar destinatarios desde la variable global DESTINATARIOS_CORREOS en ConfiguracionGlobal (correos separados por comas), se agregaron tareas automaticas de Celery para envio diario y cierre mensual por casino, se creo un archivo de configuracion rapida para horarios/flags de disparadores y se incorporo una guia operativa de uso para sincronizar y ejecutar Celery Beat.

- Fecha: 2026-04-16
- Version: 2.19.0
- Autor: Cy tamayo
- Descripcion: Se implementaron plantillas y logica backend para correos ejecutivos por casino en dos flujos: resumen diario (un correo por sucursal con adjuntos PDF y Excel del libro operativo completo) y cierre mensual (resumen del mes objetivo con adjuntos PDF y Excel del estado de resultados mensual); ademas se agrego un comando de gestion para generar o enviar manualmente estos paquetes sin depender aun de disparadores programados.

- Fecha: 2026-04-16
- Version: 2.18.0
- Autor: Cy tamayo
- Descripcion: Se agrego recorte profesional de imagen en la pagina de perfil de usuario antes de subir el avatar (flujo seleccionar-recortar-confirmar con control de zoom/rotacion) y se incorporo un comando de backend para envio de correo HTML de prueba de BinsurMX con iconos, metricas y estilos tipograficos para validar visualmente los correos automaticos en cuentas reales.

- Fecha: 2026-04-16
- Version: 2.17.0
- Autor: Cy tamayo
- Descripcion: Se implemento el modulo de Perfil de Usuario para autogestion de cuenta (consulta de datos personales, actualizacion de correo, cambio de contrasena con validacion de contrasena actual y carga de imagen de perfil), incluyendo endpoint backend dedicado con SessionAuth, almacenamiento de imagen en ruta dinamica por casino y usuario (media/<casino>/<id_usuario>/images), nueva vista frontend responsive y rediseño profesional del topbar para mostrar avatar y accesos directos al perfil.

- Fecha: 2026-04-14
- Version: 2.16.0
- Autor: Cy tamayo
- Descripcion: Se rediseño completamente la vista de Estado de Resultados a una maquetacion anual tipo Excel con columnas de ENERO a DICIEMBRE, agrupacion por padre a la izquierda y rubros contables al centro, manteniendo la fuente de datos actual desde base de datos por mes; ademas se elimino el filtro mensual de la interfaz y su logica asociada para evitar codigo huerfano, conservando el filtro por casino y anio.

- Fecha: 2026-04-14
- Version: 2.15.0
- Autor: Cy tamayo
- Descripcion: Se estandarizaron los nombres de archivos para todas las exportaciones actuales (Estadisticas y Reporte Diario) mediante una plantilla unica reutilizable, aplicada en Excel y PDF SVG con segmentos de modulo, tipo, casino, periodo y marca de tiempo para trazabilidad y uso futuro en nuevas exportaciones.

- Fecha: 2026-04-14
- Version: 2.14.0
- Autor: Cy tamayo
- Descripcion: Se implemento en Reporte Diario la exportacion profesional del libro operativo a Excel compatible con Microsoft Excel (hoja de resumen y hoja tabular) y a PDF vectorial mediante SVG multipagina para evitar distorsion visual; ademas se integraron controles UI de exportacion con validaciones de disponibilidad de datos.

- Fecha: 2026-04-14
- Version: 2.13.0
- Autor: Cy tamayo
- Descripcion: Se rediseño Reporte Diario al formato tipo libro operativo por columnas (Partida, Concepto, Ingreso, Egreso y Saldo) usando categorias de base de datos y saldo acumulado por dia; se habilito filtro por rango de fechas para DIRECTOR/ADMINISTRADOR y se forzo consulta del dia contable actual para CONTADOR/GERENTE; ademas se reforzo el arrastre de efectivo entre dias en backend y se agrego endpoint dedicado de libro operativo con pruebas automatizadas.

- Fecha: 2026-04-14
- Version: 2.12.0
- Autor: Cy tamayo
- Descripcion: Se reforzo Captura Operativa con autoguardado uniforme tras 1 segundo en todos los inputs editables de la tabla y se implemento blindaje de horario de operacion en backend y frontend usando HORARIO_APERTURA/HORARIO_CIERRE, bloqueando modificaciones fuera de ventana (incluyendo captura-rapida y cierre de dia), con pruebas automatizadas de API para validar el bloqueo.

- Fecha: 2026-04-14
- Version: 2.11.0
- Autor: Cy tamayo
- Descripcion: Se agrego exportacion por bloque en Estadisticas (Excel y PDF SVG), se deshabilitaron botones de exportacion cuando no existe informacion y se mejoro la experiencia de captura monetaria en formularios clave limpiando el 0.00 al enfocar y usando inicializacion no intrusiva en montos.

- Fecha: 2026-04-14
- Version: 2.10.0
- Autor: Cy tamayo
- Descripcion: Se robustecio el modulo de Estadisticas corrigiendo el Mapa de conceptos principales para evitar visualizacion vacia, se incorporo drill-down interactivo desde graficas clave, y se agregaron exportaciones ejecutivas: Excel con estructura vertical de bloques analiticos y PDF vectorial (SVG) para evitar distorsion de graficas.

- Fecha: 2026-04-14
- Version: 2.9.0
- Autor: Cy tamayo
- Descripcion: Se rediseño integralmente la vista de Estadisticas para DIRECTOR y ADMINISTRADOR con un tablero ejecutivo avanzado, incorporando ApexCharts en visualizaciones profesionales (flujo diario, distribucion por tipo, impacto por categoria, mapa de conceptos, rendimiento por casino y pulso semanal), KPIs estrategicos derivados, insights automaticos y tablas analiticas robustecidas con busqueda, ordenamiento y configuracion de columnas.

- Fecha: 2026-04-13
- Version: 2.8.3
- Autor: Cy tamayo
- Descripcion: Se mejoro la captura operativa para permitir multiples registros del mismo concepto cuando la categoria tiene detalles parametrizados, habilitando guardado por fila con actualizacion puntual por movimiento; adicionalmente se agrego una alerta visual en Catalogo Operativo al seleccionar rubro no contable o sin rubro, indicando que no impactara el Estado de Resultados.

- Fecha: 2026-04-13
- Version: 2.8.2
- Autor: Cy tamayo
- Descripcion: Se corrigio la logica contable del Estado de Resultados para excluir de los totales cualquier concepto sin rubro contable o asociado a rubros no contables (por ejemplo sin grupo/no contable), tanto en calculo en tiempo real como en lectura/cierre historico mensual.

- Fecha: 2026-04-13
- Version: 2.8.1
- Autor: Cy tamayo
- Descripcion: Se agrego un comando backend para simular un ano completo de operacion del casino con reglas realistas (nomina quincenal, renta mensual, pagos bimestrales de IMSS e INFONAVIT, ingresos diarios y consumo de cocina), y se cargo el ano 2025 para la sucursal de pruebas con el usuario conta.

- Fecha: 2026-04-13
- Version: 2.8.0
- Autor: Cy tamayo
- Descripcion: Se creo la nueva pestaña de Estadisticas exclusiva para DIRECTOR y ADMINISTRADOR, con panel analitico profesional y filtros avanzados por dia, rango de fechas, categoria, casino y tipo de movimiento; incluye KPIs ejecutivos, comparativo contra periodo anterior, graficas de tendencia/distribucion/rankings, tablas detalladas y nuevo endpoint backend de analitica operativa con control estricto de permisos.

- Fecha: 2026-04-10
- Version: 2.7.0
- Autor: Cy tamayo
- Descripcion: Se incorporo un resumen rapido del dia contable para CONTADOR y GERENTE en dashboard y captura operativa, incluyendo avance de movimientos, ingresos, egresos, neto y conceptos recurrentes faltantes; ademas se agrego el boton rojo de Cierre de dia para bloquear completamente el reporte diario del casino actual y se habilitaron endpoints backend dedicados para resumen-actual y cerrar-actual con control de permisos por rol.

- Fecha: 2026-04-09
- Version: 2.6.5
- Autor: Cy tamayo
- Descripcion: Se reforzo la identidad de marca en la landing de Cy Technologies incorporando el eslogan oficial "Bienvenido al futuro" en metadatos, escena de entrada y hero principal para incrementar impacto comunicativo.

- Fecha: 2026-04-09
- Version: 2.6.4
- Autor: Cy tamayo
- Descripcion: Se mejoro la transicion entre la escena de carga y la pagina real en la landing de Cy Technologies, aplicando disolucion suave, entrada progresiva del contenido y bloqueo temporal de efectos hasta finalizar la carga visual.

- Fecha: 2026-04-09
- Version: 2.6.3
- Autor: Cy tamayo
- Descripcion: Se amplio la seccion de tecnologias en la landing institucional de Cy Technologies agregando mas logotipos y capacidades visibles (TypeScript, JavaScript, Node.js, PostgreSQL, Docker, Kubernetes, AWS, Azure, Flutter, Kotlin y Git/GitHub) para fortalecer el posicionamiento de servicios.

- Fecha: 2026-04-09
- Version: 2.6.2
- Autor: Cy tamayo
- Descripcion: Se agrego una escena de entrada animada en la landing de Cy Technologies y una seccion final profesional con logotipos de tecnologias (Android, C#, .NET, Python, Vue.js, Django, MySQL y APIs), manteniendo el estilo corporativo dinamico de la pagina.

- Fecha: 2026-04-09
- Version: 2.6.1
- Autor: Cy tamayo
- Descripcion: Se actualizo la landing institucional de Cy Technologies con mayor dinamismo visual (particulas ambientales, orbita SVG, brillo interactivo y cinta animada), ampliacion de textos y portafolio a medida para software web, escritorio y Android, eliminando botones de contacto para una presentacion informativa.

- Fecha: 2026-04-09
- Version: 2.6.0
- Autor: Cy tamayo
- Descripcion: Se creo una pagina de presentacion institucional en la carpeta cytechnologies con enfoque informativo para Cy Technologies, incluyendo diseno profesional movil primero, estilos CSS dinamicos, componentes visuales SVG y animaciones de interfaz.

- Fecha: 2026-04-09
- Version: 2.5.5
- Autor: Cy tamayo
- Descripcion: Se alineo el backend Django al despliegue en subcarpeta configurando FORCE_SCRIPT_NAME en '/apex' y ajustando STATIC_URL y MEDIA_URL para que sirvan recursos bajo la misma base de dominio.

- Fecha: 2026-04-09
- Version: 2.5.4
- Autor: Cy tamayo
- Descripcion: Se configuro el frontend para despliegue en subruta agregando base '/apex/' en Vite y el uso de BASE_URL en Vue Router para compatibilidad con proyectos hermanos o estructuras por carpetas.

- Fecha: 2026-04-09
- Version: 2.5.3
- Autor: Cy tamayo
- Descripcion: Se aplico la misma restriccion por rol al selector de casino en reportes; CONTADOR y GERENTE ya no pueden ver ni usar ese filtro y solo consultan su sucursal asignada, mientras DIRECTOR y ADMINISTRADOR/SUPERUSUARIO mantienen el control completo del filtro en Estado de Resultados, Reporte Diario y Dias Contables.

- Fecha: 2026-04-09
- Version: 2.5.2
- Autor: Cy tamayo
- Descripcion: Se ajusto la visibilidad por rol en reportes para que CONTADOR y GERENTE no vean filtros de fecha ni botones especiales como conversion a USD; esos controles quedan disponibles solo para DIRECTOR y ADMINISTRADOR/SUPERUSUARIO, mostrando en su lugar texto informativo con fecha o mes en curso en Estado de Resultados, Reporte Diario y Dias Contables.

- Fecha: 2026-04-02
- Version: 2.5.1
- Autor: Cy tamayo
- Descripcion: Se endurecio la regla de dia contable para considerar cerrado por antiguedad todo dia que exceda 5 dias al pasado, bloqueando creacion y edicion de reportes y movimientos; ademas se limito el DatePicker de captura al rango permitido y se aclaro la leyenda del calendario de dias contables.

- Fecha: 2026-04-03
- Version: 2.5.0
- Autor: Cy tamayo
- Descripcion: Se implemento el control profesional de dia contable con selector DatePicker en captura operativa (por defecto T-1), bloqueo de fechas futuras y de dias cerrados, soporte backend para capturar por fecha_contable, y una nueva vista de Dias Contables con calendario mensual y semaforizacion operativa (verde, morado, azul, rojo).

- Fecha: 2026-04-02
- Version: 2.4.0
- Autor: Cy tamayo
- Descripcion: Se reforzo el estado de resultados con indicadores visuales de rubros y padres que impactan o no el total general, se mejoro profesionalmente el formulario de padres de rubros con validaciones y mensajes claros, y se ampliaron los datos de respuesta para mostrar montos considerados y no considerados de forma transparente.

- Fecha: 2026-04-02
- Version: 2.3.0
- Autor: Cy tamayo
- Descripcion: Se separo la gestion de padres de rubros en una vista propia de cabina de arquitectura, se elimino el filtro por dia del estado de resultados para trabajar solo por mes-anio-casino, y se agrego la bandera por padre para decidir si impacta o no los totales generales del estado de resultados manteniendo visibles todos los rubros.

- Fecha: 2026-04-02
- Version: 2.2.0
- Autor: Cy tamayo
- Descripcion: Se adapto backend y frontend para operar rubros con padres dinamicos por relacion, incluyendo cabina de arquitectura, gestion visual de padres de rubro, cierres historicos y estado de resultados con compatibilidad para snapshots legados.

- Fecha: 2026-04-02
- Version: 2.1.0
- Autor: Cy tamayo
- Descripcion: Se normalizo el campo padre de rubros contables a un catalogo dinamico con tabla propia, migracion de datos conservando relaciones existentes, nuevos endpoints CRUD de padres y ajuste de serializers/views para operar padres por id o clave sin perder compatibilidad de consumo.

## Cambios Menores

- Fecha: 2026-04-17
- Autor: Cy tamayo
- Descripcion: Se corrigio bootstrap de Celery en servidor para evitar `AppRegistryNotReady` y fallas al resolver `-A backend`: en `backend/celery.py` se elimino autodiscovery forzado, se agrego import explicito de tareas (`reportes_diarios.tasks` y `reportes_diarios.tareas`), en `backend/__init__.py` se expuso `app/celery` y en `scripts/iniciar_servicios_binsurmq.ps1` se actualizo worker/beat para ejecutar `python -m celery -A backend.celery:app`.

- Fecha: 2026-04-17
- Autor: Cy tamayo
- Descripcion: Se reforzo `scripts/iniciar_servicios_binsurmq.ps1` para detener correctamente servicios en segundo plano sin requerir Administrador de tareas: ahora mata arbol de procesos (padre e hijos) y limpia procesos huerfanos de waitress, celery worker y celery beat mediante patrones de linea de comando.

- Fecha: 2026-04-17
- Autor: Cy tamayo
- Descripcion: Se corrigio el registro de tareas Celery en servidor para evitar `Received unregistered task` en `reportes_diarios.ejecutar_backup_bd`: se reforzo autodiscovery en `backend/celery.py` para `tasks.py` y `tareas.py`, se agrego `reportes_diarios/tasks.py` como puente de compatibilidad y se actualizo `scripts/iniciar_servicios_binsurmq.ps1` para iniciar worker con `--include=reportes_diarios.tareas,reportes_diarios.tasks`.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se endurecio la tarea de respaldo BD para servidores con restricciones de permisos en media: la ruta de bitacora ahora se resuelve con fallback automatico (media/logs -> runtime/logs -> carpeta temporal), se evita fallo previo al try principal y se devuelve indicador de bitacora_local_activa para diagnostico operativo.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se reforzo Centro de Control en cabina_arquitectura para ejecucion manual de tareas Celery con diagnostico de broker/workers al momento del despacho, bitacora persistente en media/logs/centro_control y nuevo endpoint de consulta por task_id para distinguir estados PENDING/STARTED/SUCCESS/FAILURE y confirmar si una tarea fue tomada por worker.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se reforzo la tarea `reportes_diarios.ejecutar_backup_bd` con manejo de excepciones por etapa y bitacora tecnica persistente en `media/logs/backups_bd` (inicio, configuracion, mysqldump, compresion, notificacion, error con traza completa), ademas de incluir `archivo_log` en el resumen para diagnostico rapido desde operacion.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se reforzo la tarea manual y automatica de respaldo BD para resolver destinatarios con claves legacy (DESTINATARIOS_RESPALDO_BD/DESTINATARIO_BACKUP), fallback a SMTP configurado y continuidad de generacion del archivo de respaldo aun cuando no existan destinatarios de correo; se agregaron pruebas para esta resolucion de destinatarios.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se reforzo la apertura publica del login en usuarios (acciones csrf e iniciar-sesion sin clases de autenticacion), se agregaron pruebas API para evitar regresiones de 403 en inicio de sesion y se ajusto el vhost SSL de Apache con ServerAlias localhost/127.0.0.1, Location explicito para /apex/api y X-Forwarded-Proto para despliegue HTTPS local.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio el 403 en inicio de sesion bajo despliegue HTTPS/proxy ajustando CSRF_TRUSTED_ORIGINS en backend y habilitando SECURE_PROXY_SSL_HEADER; ademas se reforzo frontend en autenticacion para obtener y enviar token CSRF explicito antes del POST de login.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio el script DJANGO/scripts/iniciar_servicios_binsurmq.ps1 para evitar cierre inesperado de la consola principal por conflicto con la variable reservada de PowerShell PID; se renombro el parametro interno de verificacion de procesos y se mantuvo el modo de consola de control persistente.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se ajusto DJANGO/scripts/iniciar_servicios_binsurmq.ps1 para iniciar waitress/worker/beat en segundo plano con ventanas ocultas y mantener una sola consola principal persistente con menu de control (estado, reinicio por servicio, reinicio total y detener todo); adicionalmente se robustecio la autorizacion de ADMINISTRADOR en backend para Centro de Control (compatibilidad de roles administrativos y staff) y se agrego bootstrap automatico de cookie CSRF en frontend antes de peticiones mutables para evitar 403 al ejecutar tareas manuales.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se ajusto DJANGO/scripts/iniciar_servicios_binsurmq.ps1 para priorizar Python del sistema en servidor (sin depender de .venv), con fallback opcional al entorno virtual, registro en log del ejecutable Python resuelto y construccion automatica de CELERY_BROKER_URL a partir de variables CELERY_BROKER_* cuando no existe URL directa.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se mejoro el bypass de mantenimiento con modo toggle por atajo Ctrl+Alt+Y (sin ventana de tiempo), permitiendo activar y desactivar al repetir la combinacion, y se agrego reaccion inmediata del router para bloquear de nuevo cuando el bypass se desactiva en mantenimiento activo.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se robustecio el script DJANGO/scripts/iniciar_servicios_binsurmq.ps1 agregando logs de arranque y archivos stdout/stderr por servicio (waitress, celery worker, celery beat) para diagnosticar errores aunque la consola se cierre.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio el modo mantenimiento en frontend para usuarios sin sesion, agregando endpoint publico backend de configuraciones de mantenimiento y reintento rapido de sincronizacion para evitar que la aplicacion muestre login por defecto cuando la base de datos indica mantenimiento activo.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio la construccion de URL base de API en frontend para evitar rutas relativas en Apache (ejemplo /apex/auth/apex/api), normalizando VITE_API_BASE_URL a ruta absoluta y usando por defecto /apex/api/ en produccion y /api/ en desarrollo.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio el despliegue frontend para evitar errores MIME en modulos JS, fijando base publica configurable en Vite (por defecto /apex/) y agregando redireccion legacy de /binsur-mx hacia /apex en Apache.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se agrego STATIC_ROOT en DJANGO/backend/settings.py para habilitar django.contrib.staticfiles y evitar el error ImproperlyConfigured al ejecutar collectstatic.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se corrigio la importacion de Cropper en la vista de perfil para usar el modulo ESM de cropperjs y evitar el error en runtime sobre export default al abrir la pagina de Perfil de Usuario.

- Fecha: 2026-04-16
- Autor: Cy tamayo
- Descripcion: Se ajusto la validacion de rubros contables para permitir nombres repetidos cuando pertenecen a padres distintos y bloquear duplicados solo cuando coinciden nombre y padre.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se actualizo la configuracion de correo Django para Google Workspace/Gmail (smtp.gmail.com), se agrego plantilla de clave de aplicacion en DJANGO/.env.example y se documento su uso para envio SMTP con cuenta institucional.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se preparo Django para envio de correos SMTP con configuracion por variables de entorno, carga automatica de DJANGO/.env y plantilla DJANGO/.env.example para activar el buzon robertot@gbentretenimiento.com en cuanto se reciba la clave.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se estandarizo la pantalla de mantenimiento con catalogo configurable de estados operativos (mantenimiento general, actualizacion de software, mantenimiento de infraestructura, migracion de datos y contingencia operativa), decoradores visuales por estado, barra de progreso ligada a la cuenta regresiva y eliminacion de botones de navegacion/notas administrativas.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se agrego temporizador de reactivacion en la pagina de mantenimiento, tomando fecha y hora exacta desde src/utils/estadoAplicacion.js para mostrar una cuenta regresiva en tiempo real hasta la reactivacion del sistema.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se agrego modo de mantenimiento configurable en frontend con pantalla dedicada (/mantenimiento) y control centralizado en src/utils/estadoAplicacion.js para alternar de forma rapida entre operacion normal y mantenimiento desde una sola bandera.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se realizo limpieza tecnica en frontend eliminando servicios mock huerfanos no referenciados (CountryService, CustomerService, NodeService, PhotoService y ProductService) y se robustecio el guard de ruteo operativo para evitar fallos de navegacion cuando falle la carga asincrona de categorias.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se corrigio el orden de captura en categorias con detalles parametrizados para mostrar primero la columna de Monto y despues las columnas de detalles, mejorando el flujo de registro monetario en Captura Operativa.

- Fecha: 2026-04-15
- Autor: Cy tamayo
- Descripcion: Se ajusto el KPI de Estadisticas reemplazando "Ticket promedio" por "Monto promedio por movimiento" y se dividio su lectura en ingreso y egreso tanto en la tarjeta del tablero como en la hoja de resumen de la exportacion a Excel.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se corrigieron todas las exportaciones PDF activas del frontend en reportes (Reporte Diario y Estadisticas) eliminando la dependencia runtime de svg2pdf/font-family-papandreou; ahora las salidas PDF se generan con jsPDF y conversion de graficas/paginas a imagen en memoria, evitando el error de modulo en navegador.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se mejoro la exportacion de Estado de Resultados Anual a Excel aplicando estilos por celda (encabezados, padres, rubros, totales y resumenes) con colores, bordes y alineacion para conservar la jerarquia visual del reporte y evitar la hoja plana en blanco.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se corrigieron las exportaciones de Estado de Resultados Anual: el PDF ahora se genera de forma vectorial directa con jsPDF (sin conversion SVG) para evitar el error de modulo en tiempo de ejecucion, y el Excel se construye desde la tabla HTML renderizada para conservar exactamente la misma estructura visual (padres, rubros y todos los meses, incluso en 0) que se muestra en pantalla.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se agregaron en Estado de Resultados Anual los botones de exportacion a Excel y PDF SVG, incluyendo generacion de archivos con plantilla de nombre estandar, hoja de resumen y tabla anual detallada, asi como documento PDF vectorial multipagina para conservar nitidez sin distorsion.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se optimizo nuevamente la tabla anual de Estado de Resultados para mayor adaptabilidad: se redujo mas el ancho de la columna de rubro contable y de las columnas mensuales, se eliminaron los totales anuales por fila para dejar un unico acumulado anual al final, y se reforzaron breakpoints responsive para laptop y movil respetando el estilo visual del reporte.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se ajusto la vista anual de Estado de Resultados para mejorar responsividad: se habilito desplazamiento horizontal visible con barra de scroll y se compactaron anchos de columnas, paddings y tipografias para aprovechar mejor el espacio en pantalla de PC y evitar que se oculte informacion en resoluciones menores.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se agrego en Reporte Diario una fila de EFECTIVO FISICO ESPERADO EN SALA con base en el saldo final del periodo, y se aplico resaltado visual con fondo diferenciado para identificar rapidamente las filas de TOTAL y EFECTIVO.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se ajusto el Reporte Diario para eliminar la columna de fecha y la tarjeta duplicada de casino, y en consultas por rango se consolido cada categoria en una sola fila acumulando ingresos y egresos del periodo.

- Fecha: 2026-04-14
- Autor: Cy tamayo
- Descripcion: Se corrigio el autoguardado en Captura Operativa para que los campos numericos guarden automaticamente tras 1 segundo de inactividad durante la escritura, sin depender de cambiar de input.

- Fecha: 2026-04-13
- Autor: Cy tamayo
- Descripcion: Se agrego en captura operativa el boton para eliminar filas de conceptos capturados, con confirmacion de seguridad, limpieza de estado local y eliminacion del movimiento persistido cuando ya existe en base de datos.

- Fecha: 2026-04-13
- Autor: Cy tamayo
- Descripcion: Se mejoro la tabla de conceptos en Catalogo Operativo para mostrar el rubro contable con su padre en formato "Nombre rubro - Nombre padre"; adicionalmente se expuso esta informacion combinada desde el serializer de conceptos.

- Fecha: 2026-04-13
- Autor: Cy tamayo
- Descripcion: Se corrigio el selector de rubro contable en alta/edicion de conceptos para mostrar etiqueta legible en formato "Nombre rubro - Nombre padre", evitando que se visualice el ID del padre.

- Fecha: 2026-04-10
- Autor: Cy tamayo
- Descripcion: Se endurecio el endpoint de cierre de dia contable para exigir fecha_contable explicita y se agregaron pruebas automatizadas de API que validan cierre puntual por fecha sin afectar otros dias abiertos.

- Fecha: 2026-04-10
- Autor: Cy tamayo
- Descripcion: Se retiro el panel de resumen del dia contable en captura operativa para centralizarlo solo en dashboard, y se reforzo el flujo de cierre para confirmar y enviar explicitamente la fecha contable que se cierra sin afectar otros dias abiertos.

- Fecha: 2026-04-02
- Autor: Cy tamayo
- Descripcion: Se ajustaron mensajes y estructura de opciones en rubros contables para consumir padres dinamicos desde base de datos.