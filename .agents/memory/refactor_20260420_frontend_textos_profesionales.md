# Refactor de textos — Frontend profesional

**Fecha:** 2026-04-20
**Tipo:** refactor
**Capa:** frontend

---

## Problema

Los textos visibles al usuario final en el frontend usaban un registro coloquial, informal o técnico incorrecto. Ejemplos:

- Login: "Administra ingresos, egresos y reportes diarios con seguridad por roles." → poco profesional.
- Access.vue: "seccion" sin acento.
- notificacionesApi.js: "No se recibio respuesta del servidor", "Operacion exitosa" → sin acentos.
- AppMenu.vue: "Catalogo operativo" sin acento; "Cabina de Arquitectura" / "Cabina Director" → lenguaje interno no apropiado para menú de usuario.
- InicioAdministrador.vue: "Modo Dios · Centro de mando" → extremadamente informal para plataforma financiera.
- Mantenimiento.vue: "Métricas en desarrollo", "Qué puedes hacer mientras tanto" → registro informal.
- DiasContables.vue: Leyenda con colores ("Verde", "Morado", "Azul", "Rojo") sin semántica operativa.
- SoporteTecnico.vue: "No carga / se queda pensando", "Este problema bloquea mi operación diaria" → muy coloquial.

---

## Solución

Revisión y corrección sistemática de **todos** los textos visibles al usuario final en el frontend, siguiendo criterios:

1. **Registro institucional**: verbos en imperativo formal ("Gestione", "Verifique", "Registre") donde aplique, sin tuteo innecesario.
2. **Corrección ortográfica**: acentos completos en español mexicano.
3. **Semántica operativa**: etiquetas con significado de negocio, no colores arbitrarios.
4. **Sin redundancias**: eliminado "(obligatorio)" junto a asterisco `*`.
5. **Tono financiero**: coherente con plataforma de tesorería empresarial.

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `Vue/src/views/pages/auth/Login.vue` | Descripción de producto, etiquetas de campos, texto de botón |
| `Vue/src/views/pages/auth/Access.vue` | Título, corrección de acento, mensajes de instrucción |
| `Vue/src/views/pages/auth/Error.vue` | Título, descripción, lista de acciones |
| `Vue/src/views/pages/NotFound.vue` | Sin cambios (ya estaba correcto) |
| `Vue/src/views/pages/Mantenimiento.vue` | Etiquetas de sección y estado operativo |
| `Vue/src/views/pages/InicioAdministrador.vue` | Encabezado banner, KPIs, acciones rápidas |
| `Vue/src/views/pages/InicioDirector.vue` | Encabezado, métricas, leyendas de gráficas |
| `Vue/src/views/pages/InicioOperativo.vue` | Encabezado, etiquetas de KPIs, mensaje de éxito |
| `Vue/src/views/pages/PerfilUsuario.vue` | Descripciones de secciones, mensaje de cambio obligatorio |
| `Vue/src/views/pages/SoporteTecnico.vue` | Encabezado, opciones de selector, etiquetas de formulario |
| `Vue/src/views/reportes/DiasContables.vue` | Leyenda operativa, etiquetas de resumen |
| `Vue/src/layout/AppMenu.vue` | Nombres de secciones del menú lateral, corrección de acentos |
| `Vue/src/layout/AppTopbar.vue` | Subtítulo de producto en topbar |
| `Vue/src/layout/AppFooter.vue` | Copyright y descripción del producto |
| `Vue/src/service/notificacionesApi.js` | Mensajes de error de red, timeout y resúmenes de toast |

---

## Impacto

- **Solo capa visual**: ningún cambio en lógica de negocio, rutas, stores o contratos API.
- Compatible con todos los roles (ADMINISTRADOR, DIRECTOR, CONTADOR, GERENTE).
- Los valores de los enums (ej. `'ACCESO'`, `'NO_CARGA'`) **no cambiaron**, solo sus etiquetas label visibles.

---

## Lecciones aprendidas

- Los textos en los servicios (`notificacionesApi.js`) también son mensajes de usuario y deben cuidarse igual que las vistas.
- Las etiquetas de colores en UI operativa deben sustituirse por términos con significado de dominio.
- Evitar lenguaje coloquial ("se queda pensando", "Modo Dios") en plataformas financieras.
