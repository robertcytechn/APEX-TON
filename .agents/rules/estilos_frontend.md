# Estandares frontend UI/UX (Vue)

## 1) Activacion obligatoria de skill

Si la tarea modifica interfaz o experiencia de usuario en `Vue\`, usar skill: `ui-ux-pro-max`.

## 2) Stack y limites

- UI: PrimeVue 4.x
- Estilos: Tailwind CSS 4.x
- No modificar internals de PrimeVue/Tailwind; personalizar en capas del proyecto.
- Mantener enfoque mobile-first y comportamiento responsive.

## 3) Estandar de formularios y tablas

- Todo campo debe indicar obligatorio/opcional.
- Usar placeholders y labels claros en espanol.
- Select y multiselect con busqueda/autocompletado cuando el volumen de opciones lo justifique.
- Tablas con ordenamiento y controles de paginacion consistentes.

## 4) Regla monetaria visual

- Captura monetaria siempre con 2 decimales.
- Visualizacion con separador de miles y 2 decimales.
- Usar `MontoMonedaColoreado` para montos en reportes/tablas/resumenes.

## 5) Organizacion de vistas por rol

Mantener estructura por rol en `Vue\src\views\`:

- `admin\`
- `contador\`
- `director\`

## 6) Integracion con backend

- Mantener contrato API y manejo de sesion via Axios/interceptores.
- No romper menu, rutas ni permisos visuales por rol.
