Version del sistema: 2.16.0

## Historial de Versiones

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