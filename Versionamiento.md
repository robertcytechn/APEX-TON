Version del sistema: 2.7.0

## Historial de Versiones

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

- Fecha: 2026-04-02
- Autor: Cy tamayo
- Descripcion: Se ajustaron mensajes y estructura de opciones en rubros contables para consumir padres dinamicos desde base de datos.