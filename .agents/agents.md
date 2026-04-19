# Agent Configuration - BinsurMX

Este archivo describe la configuración y estructura del directorio `.agents` para el proyecto BinsurMX, que contiene las habilidades, reglas y flujos de trabajo necesarios para que los agentes puedan operar de manera efectiva dentro del marco de desarrollo establecido.
    > Proyecto y nombre de aplicaicon BinsurMX - Sistema de Gestión de Tesorería

## 📂 Estructura del Directorio `.agents`

### 🛠️ `skills/`
Contiene plantillas de habilidades especializadas.
- `ui-ux-pro-max/`: Directivas avanzadas para diseño de interfaces y experiencia de usuario.
- `django-pro/`: Directivas avanzadas para el desarrollo profesional con Django.
- `planning/`: Habilidades de planificación estratégica y estructuración de tareas.
- `agent-memory-systems/`: Sistemas avanzados de memoria y gestión de contexto para agentes.

### 📜 `rules/`
Contiene las normativas técnicas y de negocio del proyecto. Los agentes DEBEN consultar estos archivos antes de proponer cambios:
- `stack_tecnologico.md`: Definición de lenguajes, frameworks y versiones.
- `normativas_generales.md`: Reglas de idioma (Español MX), versionamiento y flujo de trabajo.
- `api_backend.md`: Estándares de Django, DRF, respuestas JSON y auditoría.
- `base_de_datos.md`: Arquitectura de tablas y relaciones fundamentales.
- `tesoreria_negocio.md`: Lógica de negocio sobre el control de tesorería y flujo de caja.
- `comportamiento_roles.md`: Definición de roles, permisos y reglas de horarios/cierres.
- `estilos_frontend.md`: Estándares de UI/UX, manejo de montos coloreados y organización de vistas.

### 🔄 `workFlows/`
Define la metodología y los flujos de trabajo específicos para la ejecución de tareas en este proyecto.

### 🧠 `memory/`
Espacio destinado a la persistencia de contexto y memoria a largo plazo del proyecto.

## 🚀 Guía para el Agente
Para asegurar la calidad del código en BinsurMX:
1. **Lee `rules/normativas_generales.md`** para entender el idioma y el flujo de versionamiento.
2. **Consulta `rules/stack_tecnologico.md`** para validar las versiones de las librerías.
3. **Aplica `rules/api_backend.md` y `rules/estilos_frontend.md`** estrictamente en cada implementación.
4. **Verifica la lógica de negocio** en `rules/tesoreria_negocio.md` y `rules/comportamiento_roles.md` antes de alterar flujos transaccionales.
