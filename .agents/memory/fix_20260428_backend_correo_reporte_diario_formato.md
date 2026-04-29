**Problema**: El correo diario mostraba un resumen que no coincidía visualmente con el Reporte Diario y los adjuntos no replicaban la primera pagina/hoja con la tabla principal y bancos; el cuerpo del email era demasiado detallado y generaba confusion sobre el saldo acumulado.

**Solucion**: Se reestructuro la generacion de Excel para que la hoja Reporte_Diario incluya el resumen, la tabla principal y la tabla de bancos en la misma hoja, y las categorias se envien en hojas posteriores. Se simplifico el cuerpo del correo HTML/TXT para mostrar solo el resumen del reporte diario. Se ajusto el helper de Excel para eliminar la columna interna Tipo_fila.

**Archivos modificados**:
- DJANGO/reportes_diarios/servicios_resumenes_correo.py
- DJANGO/reportes_diarios/templates/reportes_diarios/correos/resumen_diario_ejecutivo.html
- DJANGO/reportes_diarios/templates/reportes_diarios/correos/resumen_diario_ejecutivo.txt
- docs/backend/03_operacion_diaria.md

**Impacto**: El correo diario ahora entrega un resumen ejecutivo en el cuerpo y adjuntos alineados al formato del Reporte Diario con bancos al final y detalle por categoria en hojas/paginas posteriores.

**Lecciones aprendidas**: Mantener los adjuntos y el cuerpo del correo alineados con la vista principal para evitar interpretaciones incorrectas; evitar exponer columnas tecnicas internas en exportaciones para usuarios.
