# APEX-TON — Instrucciones de Agente IA
> Archivo de configuración canónico para todos los agentes IA que trabajen en este repositorio.
> Versión del documento: sincronizada con `.agents/versionamiento.md`

---

## 1. DESCRIPCIÓN GENERAL DEL PROYECTO

| Campo               | Valor                                                                                  |
|---------------------|----------------------------------------------------------------------------------------|
| **Nombre**          | APEX-TON                                                                               |
| **Propósito**       | Plataforma de gestión financiera y tesorería; automatización de procesos contables diarios y análisis de datos en tiempo real. |
| **Backend**         | `DJANGO/` → Django 5.x + DRF + MySQL + Celery + django-simple-history                |
| **Frontend**        | `Vue/` → Vue 3 + Pinia + PrimeVue + Tailwind CSS + Vite                              |
| **Documentación**   | `docs/backend/` y `docs/frontend/`                                                    |
| **Memoria de IA**   | `.agents/memory/` + `.agents/versionamiento.md`                                       |

---

## 2. ARQUITECTURA DEL BACKEND (`DJANGO/`)

### 2.1 Aplicaciones Django registradas

| App                        | Responsabilidad principal                                               |
|----------------------------|-------------------------------------------------------------------------|
| `configuraciones_globales` | Parámetros del sistema: horario operativo, umbrales, toggles globales. |
| `usuarios`                 | Autenticación, roles, permisos, tabla pivote.                          |
| `sucursales`               | Catálogo de sucursales y su estado operativo.                          |
| `fondos_fijos`             | Fondo fijo por sucursal (relación 1:1).                                |
| `categoria_operativa`      | Categorías y conceptos del catálogo operativo.                         |
| `reportes_diarios`         | Captura diaria, cierre, correos ejecutivos y tareas Celery.            |
| `estado_resultados`        | API de estado de resultados en tiempo real.                            |
| `libro_estado_resultados`  | Snapshot mensual inmutable (cierre mensual).                           |
| `cabina_arquitectura`      | Métricas y vista directiva de alto nivel.                              |
| `core`                     | Modelo base con auditoría (`ModeloBase`), utilidades compartidas.      |

### 2.2 Entidades y relaciones que NO deben romperse

```
Sucursal ──(1:1)──► FondoFijo
Usuario  ──(N:M)──► Rol         (vía usuarios_roles)
Rol      ──(N:M)──► Permiso     (vía roles_permisos)
Usuario  ──(N:1)──► Sucursal    (pertenencia operativa)
Concepto ──(N:1)──► CategoriaOperativa
Concepto ──(N:1)──► RubroContable
MovimientoDiario ──(N:1)──► ReporteDiario
ReporteDiario    ──(N:1)──► Sucursal
```

### 2.3 Matriz de roles

| Rol              | Captura diaria | Cierre manual | Reportes | Admin sistema |
|------------------|:--------------:|:-------------:|:--------:|:-------------:|
| ADMINISTRADOR    | ✅             | ✅            | ✅       | ✅            |
| GERENTE          | ✅             | ✅            | ✅       | ❌            |
| CONTADOR         | ✅             | ❌            | ✅       | ❌            |
| DIRECTOR         | ❌             | ❌            | ✅       | ❌            |

### 2.4 Reglas de negocio invariables

- **Día contable T-1**: toda captura se asocia al día hábil anterior. El frontend **jamás** debe contradecir esta regla.
- **Ventana operativa**: escrituras permitidas únicamente dentro de `HORARIO_APERTURA` → `HORARIO_CIERRE` (configuraciones globales). Fuera de ventana: solo lectura.
- **Cierre diario**: bloquea edición de movimientos del día. Solo ADMINISTRADOR puede reabrir.
- **Cierre mensual**: genera snapshot inmutable en `libro_estado_resultados`. Irreversible.
- **Correo enviado**: el campo `correo_enviado` en `ReporteDiario` evita reenvíos duplicados.
- **Permisos por rol**: prohibido asignar permisos directos por usuario fuera del modelo de roles.

### 2.5 Celery / tareas asíncronas

- Las tareas periódicas viven en `reportes_diarios/tareas.py`.
- El punto de entrada Celery es `backend/celery.py`.
- El cierre automático procesa reportes de los **últimos 5 días**: cierra los que tienen movimientos y deja abiertos los vacíos.
- El cierre manual (`cerrar_actual`) dispara el envío de correo inmediatamente (modelo event-driven, no cron).

---

## 3. ARQUITECTURA DEL FRONTEND (`Vue/`)

### 3.1 Estructura de carpetas

```
Vue/src/
├── assets/          # Estilos globales, imágenes, fuentes
├── components/      # Componentes reutilizables (botones, tablas, modales)
├── layout/          # Shell principal, navbar, sidebar
├── router/          # Vue Router — rutas protegidas por rol
├── service/         # Capa de API (Axios) — un archivo por dominio
│   ├── api.js                        # Instancia Axios base + interceptors
│   ├── autenticacionServicio.js
│   ├── capturaOperativaServicio.js
│   ├── cabinaArquitecturaServicio.js
│   ├── estadoResultadosServicio.js
│   ├── reporteDiarioServicio.js
│   ├── notificacionesApi.js
│   └── configuracionUsuarioServicio.js
├── stores/          # Estado global con Pinia
│   ├── sesion.js                     # Autenticación, roles, permisos activos
│   ├── categoriasOperativas.js
│   └── preferenciasUsuario.js
├── utils/           # Helpers, formateadores, constantes
└── views/
    ├── admin/       # Vistas exclusivas ADMINISTRADOR
    ├── contador/    # Captura operativa diaria
    ├── director/    # Lectura / reportería
    ├── reportes/    # Reportes compartidos (Estadísticas, EstadoResultados, etc.)
    └── pages/       # Páginas genéricas (login, 404, etc.)
```

### 3.2 Vistas principales por rol

| Vista                         | Rol(es)           | Descripción                                      |
|-------------------------------|-------------------|--------------------------------------------------|
| `CapturaOperativaCategoria`   | Contador, Gerente | Captura de movimientos por categoría/día         |
| `ReporteDiario`               | Todos             | Vista de reporte del día contable                |
| `Estadisticas`                | Director, Admin   | Métricas ejecutivas + liquidez física/virtual    |
| `EstadoResultados`            | Todos             | P&L en tiempo real                               |
| `DiasContables`               | Todos             | Calendario de días contables abiertos/cerrados   |
| `CatalogoOperativoAdmin`      | Admin             | ABM de categorías, conceptos, rubros, liquidez   |
| `CentroControlAdmin`          | Admin             | Panel de control del sistema                     |
| `SucursalesAdmin`             | Admin             | Gestión de sucursales y fondos fijos             |
| `UsuariosAdmin`               | Admin             | Gestión de usuarios y roles                      |
| `ConfiguracionesGlobalesAdmin`| Admin             | Parámetros del sistema                           |

---

## 4. REGLAS DE TRABAJO DEL AGENTE IA

### 4.1 Regla de análisis previo (OBLIGATORIA antes de cualquier cambio)

```
PASO 1 → Identificar qué capa toca el cambio: DJANGO/, Vue/, o ambas.
PASO 2 → Leer el código relevante existente antes de generar nada nuevo.
PASO 3 → Revisar impacto en: rutas, permisos, contrato API, serializers y vistas.
PASO 4 → Ejecutar el cambio y documentarlo.
```

> ⚠️ **NUNCA asumir cómo funciona el código existente. Siempre leerlo primero.**

### 4.2 Regla de coherencia por capa

| Si cambia…                    | También revisar…                                              |
|-------------------------------|---------------------------------------------------------------|
| Modelo / campo Django         | Migración, serializer, viewset, URL, consumo Axios frontend   |
| Contrato de API (serializer)  | Viewset, permisos, frontend (servicio + store + vista)        |
| Lógica de negocio backend     | Tareas Celery relacionadas, tests, documentación              |
| Componente / vista Vue        | Store Pinia, servicio Axios, permisos de rol en router        |
| Regla de negocio              | Backend + frontend + `docs/` correspondiente                  |

### 4.3 Regla de idioma

- **Frontend (Vue)**: todo texto visible al usuario en **español mexicano** con acentos y signos de puntuación correctos. Prohibido "anio", "seccion", etc.
- **Backend (Django)**: nombres de modelos, campos y relaciones en **español**, siguiendo convenciones Django/DRF. Evitar anglicismos innecesarios.
- **Código interno** (variables, funciones): español para dominio de negocio; inglés solo para patrones técnicos estándar (`queryset`, `serializer`, etc.).

### 4.4 Regla de documentación

Actualizar documentación **solo cuando el comportamiento cambie**:

- Backend: `docs/backend/*.md`
- Frontend: `docs/frontend/*.md`
- Instrucciones de agente: este archivo (`.github/copilot-instructions.md`)

---

## 5. VERSIONAMIENTO Y MEMORIA DE CAMBIOS

### 5.1 Git

- Commits en español, descriptivos y atómicos.
- Formato sugerido: `[tipo] descripción breve` donde tipo es `feat`, `fix`, `refactor`, `docs`, `chore`.

### 5.2 Registro en `.agents/versionamiento.md`

Al inicio del archivo debe existir el campo `version_actual: vX.Y.Z` (Mayor.Menor.Parche).

Cada entrada de cambio debe incluir:

```markdown
## vX.Y.Z — YYYY-MM-DD
**Autor:** Jose Roberto Tamayo Montejano
**Resumen:** Una línea describiendo qué cambió.
**Capa(s):** backend | frontend | ambas
**Detalle:** `.agents/memory/<archivo>.md`
```

### 5.3 Archivos de memoria en `.agents/memory/`

Nombre del archivo: `<tipo>_<fecha>_<capa>_<descripcion_corta>.md`

Ejemplo: `fix_20260419_backend_cierre_correo_duplicado.md`

Contenido obligatorio:
- **Problema**: qué falló o qué se necesitaba.
- **Solución**: qué se implementó y por qué.
- **Archivos modificados**: lista con paths relativos.
- **Impacto**: qué otras partes del sistema se ven afectadas.
- **Lecciones aprendidas**: qué evitar en el futuro.

---

## 6. WORKFLOWS DE TRABAJO

> Esta sección define los protocolos paso a paso según el tipo de trabajo a realizar.
> El agente debe identificar el workflow aplicable **antes de escribir cualquier código**.

---

### WF-01 · Solo Backend (nuevo modelo, endpoint o lógica de negocio)

```
[1] Leer modelos existentes relacionados (models.py de la app afectada y de core/).
[2] Leer serializers.py y views.py de la misma app.
[3] Definir/modificar modelo → generar migración.
[4] Actualizar serializer (campos, validaciones, permisos por rol).
[5] Actualizar o crear ViewSet/APIView y registrar URL.
[6] Verificar impacto en tareas Celery si el modelo participa en flujos asíncronos.
[7] Actualizar docs/backend/<app>.md.
[8] Registrar cambio en .agents/versionamiento.md y .agents/memory/.
```

**Checklist de calidad backend:**
- [ ] Migración creada y sin conflictos.
- [ ] Serializer retorna solo los campos necesarios por rol.
- [ ] ViewSet tiene permisos explícitos (`permission_classes`).
- [ ] Ninguna ruta nueva rompe las existentes en `backend/urls.py`.
- [ ] Regla T-1 respetada si el endpoint toca días contables.
- [ ] Si hay correo o tarea asíncrona: `correo_enviado` actualizado correctamente.

---

### WF-02 · Solo Frontend (nuevo componente, vista o mejora de UI)

```
[1] Identificar el rol que accede a la vista (Admin, Contador, Director, Gerente).
[2] Leer el servicio Axios relacionado en Vue/src/service/.
[3] Leer el store Pinia relacionado en Vue/src/stores/.
[4] Crear/modificar el componente o vista.
[5] Registrar la ruta en Vue/src/router/ con guard de rol si aplica.
[6] Actualizar el store si el estado compartido cambia.
[7] Verificar textos: español mexicano, acentos, sin anglicismos en UI.
[8] Actualizar docs/frontend/<vista>.md.
[9] Registrar cambio en .agents/versionamiento.md y .agents/memory/.
```

**Checklist de calidad frontend:**
- [ ] Componente usa el servicio Axios correspondiente (no llama a `fetch` directamente).
- [ ] Estado sensible (sesión, permisos) leído desde `stores/sesion.js`.
- [ ] Vista protegida por guard de rol en el router.
- [ ] Todos los textos en español mexicano con acentos.
- [ ] No hay lógica de negocio duplicada que ya exista en el backend.
- [ ] Manejo de error y estado de carga implementados.

---

### WF-03 · Full-Stack (feature que toca backend y frontend simultáneamente)

```
[1] Ejecutar WF-01 completo para la parte backend.
[2] Verificar contrato de API (campos devueltos, tipos, permisos).
[3] Ejecutar WF-02 completo para la parte frontend.
[4] Probar el flujo end-to-end: autenticación → request → respuesta → render.
[5] Actualizar docs/backend/ y docs/frontend/ en el mismo commit o PR.
[6] Registrar cambio en .agents/versionamiento.md y .agents/memory/.
```

**Checklist adicional full-stack:**
- [ ] El contrato API (campos, tipos, nombres) es idéntico entre serializer y servicio Axios.
- [ ] Los permisos de rol en backend y en el router de Vue son consistentes.
- [ ] La regla T-1 es coherente en ambas capas.
- [ ] Se actualizaron ambos conjuntos de docs.

---

### WF-04 · Nueva Página / Vista completa

```
[1] Definir: ¿quién accede? ¿qué datos necesita? ¿qué acciones permite?
[2] Si requiere nuevos endpoints → ejecutar WF-01 primero.
[3] Crear la vista en Vue/src/views/<rol>/<NombreVista>.vue.
[4] Registrar ruta en router con meta de roles permitidos.
[5] Agregar entrada en el menú lateral (layout/) si corresponde.
[6] Crear servicio Axios en Vue/src/service/ si no existe.
[7] Documentar en docs/frontend/.
[8] Registrar en .agents/versionamiento.md.
```

---

### WF-05 · Corrección de Bug

```
[1] Reproducir el bug y anotar: capa afectada, síntoma, condición de fallo.
[2] Buscar en .agents/memory/ si ya existe un registro similar.
[3] Leer el código afectado completo antes de proponer fix.
[4] Aplicar el fix mínimo que resuelva el problema sin efectos colaterales.
[5] Verificar que los flujos relacionados siguen funcionando.
[6] Registrar en .agents/memory/ con prefijo fix_.
[7] Actualizar .agents/versionamiento.md (incrementar parche Z).
```

---

### WF-06 · Refactor o Mejora de Código Existente

```
[1] Leer TODO el código a refactorizar antes de proponer cambios.
[2] Definir el alcance: ¿qué mejora y qué NO cambia?
[3] Ejecutar el refactor manteniendo el contrato externo (API o props de componente).
[4] Verificar que ningún test existente se rompe.
[5] Actualizar documentación si la estructura cambia.
[6] Registrar en .agents/memory/ con prefijo refactor_.
```

---

### WF-07 · Cierre de Sesión de Trabajo (fin de tarea o conversación significativa)

```
[1] Crear archivo de memoria en .agents/memory/ con todos los cambios de la sesión.
[2] Actualizar .agents/versionamiento.md con la nueva versión.
[3] Verificar que docs/ estén al día.
[4] Proponer mensaje de commit Git descriptivo al usuario.
```

---

### WF-08 · Trabajo con Celery / Tareas Asíncronas

```
[1] Leer backend/celery.py y la app de tareas relacionada (ej: reportes_diarios/tareas.py).
[2] Identificar si la tarea es periódica (beat) o disparada por evento.
[3] Verificar que el flag de control (ej: correo_enviado) esté implementado para idempotencia.
[4] Implementar o modificar la tarea.
[5] Asegurar manejo de errores y logging dentro de la tarea.
[6] Documentar el comportamiento en docs/backend/.
[7] Registrar en .agents/memory/.
```

---

### Tabla de selección rápida de workflow

| Situación                                           | Workflow(s) a usar          |
|-----------------------------------------------------|-----------------------------|
| Nuevo modelo o endpoint Django                      | WF-01                       |
| Nuevo componente o mejora visual Vue                | WF-02                       |
| Feature completa (back + front)                     | WF-03                       |
| Nueva página/vista con ruta propia                  | WF-04 (+ WF-01 si necesita) |
| Bug reportado o detectado                           | WF-05                       |
| Refactor / limpieza de código                       | WF-06                       |
| Fin de sesión / cierre de tarea                     | WF-07                       |
| Tarea Celery nueva o modificada                     | WF-08                       |
| Cambio que afecta > 3 archivos o > 2 capas          | WF-03                       |