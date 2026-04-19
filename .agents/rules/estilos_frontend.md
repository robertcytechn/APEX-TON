# Estándares de Frontend

## Estilos y Componentes
- **Tecnologías:** Usar Tailwind CSS para estilos y los componentes más recientes de PrimeVue v4.
- **Personalización:** Prohibido modificar el core de Tailwind o PrimeVue. Estilos personalizados deben ir en `style.css`.
- **Diseño:** Enfoque **Mobile First**. La interfaz debe adaptarse primero a móviles y luego a pantallas grandes, manteniendo botones accesibles y sin deformaciones.
- **Estructura de Formularios:** Agrupar campos en formularios (`form`) para mejorar el orden y habilitar accesos rápidos de teclado nativos.

## UX y UI
- **Indicadores:** Mostrar siempre si un campo es `* obligatorio` o `opcional` en la etiqueta.
- **Accesibilidad:** Agregar iconos semánticos y placeholders descriptivos en español en inputs y selects.
- **Tablas (DataTables):** 
  - Implementar diseño avanzado: ver/ocultar columnas, reordenamiento, selección de cantidad de datos (10, 20, 50, todos).
  - Habilitar ordenamiento ascendente/descendente al hacer clic en los encabezados.
- **Selectores:** Habilitar buscador/autocompletado en `Select` y `MultiSelect`.

## Manejo de Montos Monetarios
- **Captura:** Los campos monetarios deben iniciar y capturarse con formato explícito de 2 decimales (ej. `0.00`). Prohibido dejar campos vacíos.
- **Visualización:**
  - Usar separador de miles y 2 decimales (ej. `1,450,640.50`).
  - **Segmentación Visual:** Usar colores distintos para cada bloque de miles y un color diferente para la parte decimal.
  - **Componente:** Usar obligatoriamente el componente `MontoMonedaColoreado` en tablas, tarjetas, reportes o resúmenes de dinero.
  - **Validación:** Agregar vista previa coloreada del monto en formularios antes de guardar.

## Organización de Vistas
- Las carpetas en `views` deben organizarse por rol:
  - `/admin`: Acciones y vistas del Administrador.
  - `/contador`: Acciones y vistas del Contador.
  - `/director`: Acciones y vistas del Director.
