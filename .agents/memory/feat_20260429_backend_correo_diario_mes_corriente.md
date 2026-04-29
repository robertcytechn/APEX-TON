**Problema**: El correo diario generaba adjuntos (PDF/Excel) solo con el dia contable, pero se requiere que reflejen el mes en curso completo (del dia 1 al dia contable actual), similar al filtro de Director en el Reporte Diario.

**Solucion**: Se ajusto la construccion del paquete del correo diario para usar un rango mensual (dia 1 al dia contable) al generar datos, conteos y adjuntos. Se actualizo el texto del periodo en el correo (HTML/TXT) y el encabezado del PDF para mostrar el rango mensual.

**Archivos modificados**:
- DJANGO/reportes_diarios/servicios_resumenes_correo.py
- DJANGO/reportes_diarios/templates/reportes_diarios/correos/resumen_diario_ejecutivo.html
- DJANGO/reportes_diarios/templates/reportes_diarios/correos/resumen_diario_ejecutivo.txt
- docs/backend/03_operacion_diaria.md

**Impacto**: Los correos diarios ahora envian PDF/Excel con el acumulado del mes en curso y el resumen del correo refleja ese rango, manteniendo el formato del Reporte Diario.

**Lecciones aprendidas**: Cuando el correo replica un reporte de UI, hay que alinear el rango temporal con el filtro esperado para evitar discrepancias en acumulados.
