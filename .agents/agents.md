# Agent Configuration - BinsurMX

Este proyecto utiliza el directorio `.agents` para centralizar las directivas, reglas y contexto necesarios para que los agentes de IA (Copilot, Gemini, etc.) operen de manera consistente y alineada con los estándares del negocio.

## 📂 Estructura del Directorio `.agents`

### 🛠️ `skills/`
Contiene plantillas de habilidades especializadas.
- `ui-ux-pro-max/`: Directivas avanzadas para diseño de interfaces y experiencia de usuario.

### 📜 `rules/`
Contiene las normativas técnicas y de negocio del proyecto. Los agentes DEBEN consultar estos archivos antes de proponer cambios:
- `stack_tecnologico.md`: Definición de lenguajes, frameworks y versiones.
- `normativas_generales.md`: Reglas de idioma (Español MX), versionamiento y flujo de trabajo.
- `api_backend.md`: Estándares de Django, DRF, respuestas JSON y auditoría.
- `base_de_datos.md`: Arquitectura de tablas y relaciones fundamentales.
- `tesoreria_negocio.md`: Lógica de negocio sobre el control de tesorería y flujo de caja.
- `comportamiento_roles.md`: Definición de roles, permisos y reglas de horarios/cierres.
- `estilos_frontend.md`: Estándares de UI/UX, manejo de montos coloreados y organización de vistas.

### 🧠 `memory/`
Espacio destinado a la persistencia de contexto y memoria a largo plazo del proyecto.

## 🚀 Guía para el Agente
Para asegurar la calidad del código en BinsurMX:
1. **Lee `rules/normativas_generales.md`** para entender el idioma y el flujo de versionamiento.
2. **Consulta `rules/stack_tecnologico.md`** para validar las versiones de las librerías.
3. **Aplica `rules/api_backend.md` y `rules/estilos_frontend.md`** estrictamente en cada implementación.
4. **Verifica la lógica de negocio** en `rules/tesoreria_negocio.md` y `rules/comportamiento_roles.md` antes de alterar flujos transaccionales.
