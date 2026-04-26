# APEX-TON: Plataforma de Gestión Financiera y Tesorería

Bienvenido a la presentación de la plataforma **APEX-TON**. Este documento ha sido preparado para resolver las preguntas más frecuentes de la mesa directiva y los dueños sobre el funcionamiento central, la seguridad de la información y la automatización del sistema.

---

## 1. El Reporte Diario

**¿Cómo funciona la captura y el control diario del efectivo?**

El reporte diario es el corazón de la operación en las sucursales. Está diseñado para garantizar que cada peso cuadre perfectamente al finalizar la jornada, bajo estrictas reglas de negocio:

*   **Regla de Día Contable (T-1):** Toda captura en el sistema pertenece al "día hábil anterior". Esto significa que la operación de ayer se cuadra y audita hoy. El sistema no permite alterar esta regla, evitando descuadres por cruce de fechas.
*   **Ventana Operativa de Seguridad:** Los usuarios (ej. cajeros o contadores) sólo pueden escribir y guardar datos dentro del horario establecido por la empresa. Fuera de ese horario, el sistema entra en modo de "solo lectura".
*   **Bloqueo por Cierre:** Una vez que el reporte diario se cierra (ya sea manual o automáticamente), **nadie** puede editar sus movimientos. Solo un Administrador de alto nivel tiene el poder de "reabrir" un día si fuese absolutamente necesario.
*   **Transparencia de Saldos:** El sistema separa inteligentemente los registros puramente bancarios de los operativos en la sucursal, asegurando que el "Efectivo Físico Esperado" sea un reflejo 100% real de lo que debe existir en caja.

---

## 2. Envío de Correos y Notificaciones

**¿Cómo nos aseguramos de que los directivos reciban la información a tiempo?**

El sistema cuenta con un motor en segundo plano que garantiza la comunicación ejecutiva sin intervención humana constante.

*   **Notificaciones Inmediatas:** Cuando un gerente o contador realiza un "Cierre Manual" desde el panel de control, el reporte de ese día se envía inmediatamente por correo a la directiva.
*   **Cierres Automáticos (Motor Asíncrono):** Si el personal olvida cerrar el día, el sistema escanea automáticamente los últimos 5 días. Si encuentra días con actividad financiera que quedaron abiertos, **los cierra y envía el reporte por correo de forma autónoma**. Los días en los que la sucursal no operó (sin movimientos) se ignoran inteligentemente.
*   **Protección Anti-Duplicados:** Gracias a un candado de seguridad, es imposible que se envíe el mismo reporte dos veces. Una vez que el correo ha salido con éxito, el día queda marcado, evitando el spam a la directiva.

---

## 3. El Estado de Resultados

**¿Podemos confiar en la salud financiera que reporta el sistema?**

El Estado de Resultados (P&L) en APEX-TON está diseñado para ofrecer visibilidad instantánea, sin perder el rigor contable histórico.

*   **En Tiempo Real:** Los directores pueden visualizar los ingresos, egresos y el margen operativo al instante, basado en los reportes diarios más recientes.
*   **Cierre Mensual Inmutable:** Al finalizar el mes contable, el sistema genera una "fotografía" (Snapshot). Este registro mensual es **irreversible e inmutable**. Garantiza que los libros pasados no puedan ser alterados de forma retroactiva, brindando paz mental en futuras auditorías.
*   **Fórmulas Precisas:** Los cálculos administrativos contemplan todos los factores reales del día a día. Del saldo se descuentan automáticamente los fondos fijos, dólares, saldos por comprobar y mermas/pérdidas, dándole a la directiva la cifra del "dinero real disponible".

---

## 4. Las Estadísticas (Cabina de Arquitectura)

**¿Qué datos tenemos para la toma de decisiones a nivel dirección?**

Para los altos mandos, el sistema omite el ruido operativo y presenta la información de manera gerencial en la **Cabina de Arquitectura** y la vista de **Estadísticas**.

*   **Rastreo de Liquidez (Física vs. Virtual):** El sistema clasifica el dinero automáticamente. En un solo panel, los dueños pueden ver exactamente cuánto capital está en "Efectivo Físico" (cajas y bóvedas) y cuánto es "Liquidez Virtual" (transferencias y bancos).
*   **Métricas de Alto Nivel:** Gráficas e indicadores del rendimiento por sucursal, identificando rápidamente qué locaciones están generando mayor utilidad o dónde están los focos rojos de pérdidas/faltantes.
*   **Vistas Restringidas:** Un cajero jamás podrá ver las estadísticas de la empresa. Todo está segmentado por "Roles". Solo los perfiles de *Director* y *Administrador* tienen acceso al panorama global.
