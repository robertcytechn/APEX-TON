# Documentación del Módulo: Configuraciones y Catálogos Maestros

Este documento engloba tres módulos fundamentales para la parametrización del sistema: `categoria_operativa`, `configuraciones_globales` y `configuraciones_usuario`. Estos módulos proveen los catálogos base, variables de entorno y preferencias de experiencia de usuario que gobiernan el comportamiento del resto de las aplicaciones.

---

## 1. Módulo `categoria_operativa`

Define la estructura jerárquica de la captura de movimientos diarios. Agrupa las transacciones en "pestañas" (Categorías) y "opciones" (Conceptos).

### 1.1 Arquitectura de Modelos
- **`CategoriaOperativa`**: Representa una pestaña de flujo operativo (ej. ADMINISTRACION, BOOK, BILLPOCKET). Determina si la pestaña requiere manejar un `usa_saldo_inicial`.
- **`Concepto`**: Nomenclatura específica de un movimiento (ej. 'VENTA DE CAFE').
  - **Relaciones:** Se ata invariablemente a una `CategoriaOperativa` y, de forma opcional, a un `RubroContable` (para que el movimiento impacte en el Libro de Estado de Resultados).
  - **Banderas:** `es_recurrente` (para mostrar alertas de faltantes al cierre) y `requiere_imagen` (para solicitar comprobantes).
- **`DetalleParametrizado`**: Permite definir campos dinámicos extra por categoría (ej. un campo 'responsable' tipo TEXT, o 'monto_exacto' tipo DECIMAL). Al registrar un movimiento, los valores de estos detalles se guardan en el JSON `detalles_snapshot` del `MovimientoDiario`.
- **`SaldoInicialCategoriaMensual`**: Tabla de arrastre de saldos. Para categorías que manejan caja propia (ej. SOBRANTES o PRESTAMOS), mantiene un historial mes a mes que puede generarse automáticamente al cierre del mes anterior.

### 1.2 Controladores (`views.py`)
- Los ViewSets (`CategoriaOperativaViewSet`, `ConceptoViewSet`, `DetalleParametrizadoViewSet`) están fuertemente protegidos por el permiso `EsDirectorOAdministradorEnEscritura`.
- Soportan métodos custom de estado: `@action activar`, `desactivar` y `bloquear`.

---

## 2. Módulo `configuraciones_globales`

Administra las variables del entorno del negocio y el catálogo jerárquico contable.

### 2.1 Arquitectura de Modelos
- **`PadreRubroContable`**: Nivel más alto de la contabilidad (ej. INGRESOS GENERALES, GASTOS OPERATIVOS). Contiene un flag crucial `considerar_en_estado_resultados` que determina si todos sus hijos sumarán a los netos del cierre de mes.
- **`RubroContable`**: Categoría contable específica (ej. VENTAS BEBIDAS, PAGO DE RENTA) que pertenece a un Padre. Los `Conceptos` de la operación diaria se mapean a estos rubros.
- **`ConfiguracionGlobal`**: Almacén clave-valor universal.
  - Soporta valores dinámicos a través de la propiedad `@property valor_tipado` que casteará automáticamente el string guardado a `INT`, `FLOAT`, `BOOLEAN`, `DATE` o `JSON` dependiendo de lo especificado en `tipo_valor`.
  - Usado extensivamente para definir `TIPO_CAMBIO_USD` y `TIPO_CAMBIO_EUR` que son consumidos al vuelo por la API.

### 2.2 Endpoints Especiales (`views.py`)
- **`ConfiguracionGlobalPublicaMantenimientoAPIView`**: Un endpoint desprotegido (`AllowAny`) que permite al frontend de inicio de sesión consultar si el sistema se encuentra en modo mantenimiento (ej. leyendo `ESTADO_APLICACION`). Filtra explícitamente solo un set seguro de claves públicas.

---

## 3. Módulo `configuraciones_usuario`

Provee la capa de personalización de UI/UX a nivel individual. Funciona bajo un esquema "Autoservicio" (Self-Service).

### 3.1 Arquitectura de Modelos
- **`ConfiguracionUsuario`**: Relación `OneToOne` con el modelo `Usuario`.
- **Capacidades de Personalización:**
  - **Apariencia:** `tema` (claro, oscuro, sistema), `color_acento` (azul, morado... o `personalizado` vía `color_hex`).
  - **Tipografía/Densidad:** `densidad_ui` y `tamano_fuente`.
  - **Internacionalización:** `formato_fecha` (DMY, MDY, YMD) y `separador_miles`.
  - **Navegación:** `menu_colapsado`, `pagina_inicio`, `filas_por_pagina`.
  - **Extensión Abierta:** `preferencias_extra` es un `JSONField` previsto para almacenar nuevos flags de UI sin requerir migraciones de base de datos.

### 3.2 Controladores (`views.py`)
- **Ruta principal: `/api/configuracion_usuario/mi-configuracion/`**:
  - `GET`: Si el usuario no tiene configuración, el sistema la genera automáticamente con defaults (Lazy Creation) y la retorna.
  - `PATCH`: Actualiza preferencias. Ignora cualquier intento de alterar el campo `usuario` desde el payload.
- **Ruta: `/api/configuracion_usuario/mi-configuracion/restablecer/`**:
  - Elimina el registro del usuario y genera uno nuevo completamente limpio.
- **Auditoría:** Los endpoints list/retrieve generales del ViewSet bloquean el acceso cruzado; un usuario no puede ver la configuración de otro, salvo que posea el rol `ADMINISTRADOR`.

---

## 4. Referencia de Endpoints API (Resumen)

| Módulo Base | Endpoint Principal | Método | Descripción |
|-------------|--------------------|--------|-------------|
| `categoria_operativa` | `/api/categorias/` | GET, POST | Maestro de Pestañas operativas. |
| `categoria_operativa` | `/api/conceptos/` | GET, POST | Conceptos (Acepta filtro `?categoria_id=X`). |
| `categoria_operativa` | `/api/detalles-parametrizados/` | GET, POST | Campos extra (Acepta filtro `?categoria_id=X`). |
| `configuraciones_globales` | `/api/configuraciones/` | GET, POST | Variables globales del sistema (ej. tasas de cambio). |
| `configuraciones_globales` | `/api/configuraciones/publicas/mantenimiento/` | GET | Estado público del sistema (Sin token). |
| `configuraciones_globales` | `/api/padres-rubros/` | GET, POST | Agrupadores contables nivel 1. |
| `configuraciones_globales` | `/api/rubros/` | GET, POST | Rubros contables nivel 2. |
| `configuraciones_usuario` | `/api/configuracion-usuario/mi-configuracion/` | GET, PATCH | Acceso y edición de preferencias del usuario autenticado. |
