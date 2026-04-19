# Normativas Generales de Desarrollo

## Idioma y Localización
- **Lenguaje Obligatorio:** Todo el desarrollo (nombres de variables, funciones, clases, comentarios y documentación) DEBE estar exclusivamente en **Español de México**.
- **Interfaz de Usuario:** Cualquier texto, alerta o elemento visible para el usuario final debe escribirse en español.

## Control de Versiones y Flujo
- **Herramientas:** Uso estricto de **Git** y **GitHub**.
- **Análisis Previo:** Antes de realizar cualquier cambio, es obligatorio revisar tanto el backend como el frontend para comprender la lógica y el funcionamiento del sistema. No se deben aplicar cambios sin entender el impacto global.
- **Consistencia:** Al modificar el backend, asegurar la actualización de views y serializers correspondientes. Al modificar el frontend, garantizar que no se afecte la experiencia del usuario, la interfaz, el menú lateral o el enrutamiento.

## Registro de Cambios (Versionamiento)
- **Historial de Versiones:** Cada cambio significativo debe documentarse en `Versionamiento.md`.
  - **Formato:** Fecha, descripción del cambio, autor (siempre Cy Tamayo) y versión.
  - **Versión Actual:** La primera línea del archivo debe contener la versión actual siguiendo el formato `mayor.minor.patch` (ej. 1.0.0).
- **Cambios Menores:** Las correcciones de errores o cambios menores se registran en la sección "Cambios Menores" del mismo archivo, indicando fecha, descripción y autor (Cy Tamayo).

## Documentación
- Es obligatorio mantener una documentación clara y actualizada, incluyendo comentarios explicativos en funciones, clases y módulos, además de una documentación general sobre arquitectura y flujo de datos.
