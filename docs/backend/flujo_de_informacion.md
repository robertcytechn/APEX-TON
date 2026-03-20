# APEX-TON — Flujo de Información del Sistema

> Este documento explica **en qué orden** se configura el sistema y **cómo viaja la información** desde la configuración inicial hasta la generación del Estado de Resultados. Es la guía de referencia para entender la cadena completa de datos.

---

## Fase 0 — Configuración inicial (se hace UNA sola vez)

Estas tablas son el cimiento del sistema. Sin ellas, nada más funciona. Se llenan antes de arrancar operaciones.

### Paso 0.1 — Configuraciones Globales (`configuraciones_globales`)

**¿Para qué sirve?**  
Variables de sistema que aplican a toda la empresa. Son los parámetros de control operativo y financiero.

**¿Qué registros crear primero?**

| Clave | Tipo | Ejemplo | Obligatoria |
|---|---|---|---|
| `HORARIO_APERTURA` | `TIME` | `08:00` | ✅ Sí |
| `HORARIO_CIERRE` | `TIME` | `23:00` | ✅ Sí |
| `TIPO_CAMBIO_USD` | `FLOAT` | `17.25` | ✅ Sí |
| `TIPO_CAMBIO_EUR` | `FLOAT` | `18.90` | Recomendada |

> **¡Importante!** Si `HORARIO_APERTURA` y `HORARIO_CIERRE` no están creados, el sistema no bloqueará capturas fuera de horario (se asume siempre abierto). Configúralos antes de usar el sistema en producción.

---

### Paso 0.2 — Rubros Contables (`rubro_contable`)

**¿Para qué sirve?**  
Categorías contables globales que homologan todos los movimientos de todas las salas bajo la misma nomenclatura. Son el eje del Estado de Resultados.

**Ejemplo:**

| nombre | padre | tipo |
|---|---|---|
| `VENTAS_BEBIDAS` | `INGRESOS` | `INGRESO` |
| `PAGO_RENTA` | `GASTOS` | `EGRESO` |
| `PAGO_MAQUINAS` | `PAGO_MAQUINAS` | `EGRESO` |
| `JUEGO_VIVO_RECAUDO` | `JUEGO_VIVO` | `INGRESO` |

> Créalos pensando en cómo quieres ver agrupado el Estado de Resultados. Cada grupo de movimientos terminará sumándose aquí.

---

### Paso 0.3 — Sucursales (`sucursales`)

**¿Para qué sirve?**  
Representa cada sala de juegos. Todo lo demás (usuarios, reportes, fondos) está anclado a una sucursal.

**¿Qué registrar?**  
Nombre, clave interna (ej. `MOR-01`), ciudad, encargado y fondo inicial en MXN.

---

### Paso 0.4 — Fondos Fijos (`fondos_fijos`)

**¿Para qué sirve?**  
Cada sucursal necesita su propio fondo fijo (caja chica). Es una relación 1:1 con la sucursal.

**¿Cuándo crearlo?**  
Inmediatamente después de crear la sucursal.

```
Sucursal "Sala Morelia Centro" (MOR-01)
    └── FondoFijo: monto_autorizado=$50,000 MXN, saldo_actual=$50,000 MXN
```

---

### Paso 0.5 — Roles y Permisos (`roles`, `permisos`, `roles_permisos`)

**¿Para qué sirven?**  
Definen qué puede hacer cada tipo de usuario en el sistema.

**Roles del sistema:**

| Rol | Descripción breve |
|---|---|
| `ADMINISTRADOR` | Control total. Único que puede reabrir días cerrados |
| `GERENTE` | Igual que Contador por ahora |
| `CONTADOR` | Captura de pestañas históricas |
| `DIRECTOR` | Solo lectura y exportación de reportes |

**Flujo:**
```
Crear Rol → Crear Permiso → Asignar Permiso a Rol (RolPermiso)
```

---

### Paso 0.6 — Usuarios (`usuarios`, `usuarios_roles`)

**¿Para qué sirve?**  
Son las personas que operan el sistema. Cada usuario se asocia a una sucursal y a uno o varios roles.

**Flujo:**
```
Crear Usuario → Asignar Rol al Usuario (UsuarioRol)
```

> Un usuario sin rol asignado no tiene permisos de ningún tipo en la interfaz.

---

### Paso 0.7 — Categorías Operativas + Conceptos (`categorias_operativas`, `conceptos`, `detalles_parametrizados`)

**¿Para qué sirven?**  
Las **categorías** son las pestañas del sistema (ej. `ADMINISTRACION`, `BOOK`, `DOLARES`).  
Los **conceptos** son los nombres específicos de movimientos dentro de cada pestaña (ej. `VENTA DE CAFE`).  
Los **detalles parametrizados** son campos extra que algunas pestañas necesitan (ej. la pestaña `SOBRANTES` necesita saber quién es el responsable y el área de origen).

**Flujo de creación:**
```
1. Crear CategoriaOperativa (pestaña)
       ↓
2. Crear Conceptos que pertenecen a esa categoría
   (cada concepto referencia un RubroContable)
       ↓
3. Crear DetallesParametrizados para la categoría
   (si esa pestaña necesita campos extra)
```

**Ejemplo:**

```
CategoriaOperativa: ADMINISTRACION (tipo=MIXTO)
    ├── Concepto: "VENTA DE CAFE"   → tipo=INGRESO → rubro=VENTAS_BEBIDAS
    ├── Concepto: "PAGO DE RENTA"  → tipo=EGRESO  → rubro=PAGO_RENTA
    └── (sin detalles parametrizados)

CategoriaOperativa: SOBRANTES (tipo=INGRESO)
    ├── Concepto: "SOBRANTE DE CAJA" → tipo=INGRESO → rubro=OTROS_INGRESOS
    └── DetallesParametrizados:
            ├── "responsable"   (TEXT, requerido)
            └── "area_origen"   (TEXT, requerido)
```

---

## Fase 1 — Operación diaria (se repite todos los días)

Una vez que el sistema está configurado, el ciclo diario funciona así:

### El día contable siempre es T-1

> Si hoy es **20 de marzo**, el día contable es **19 de marzo**.  
> El backend calcula esto automáticamente. El frontend **nunca** puede cambiar la fecha.

---

### Paso 1.1 — El sistema abre automáticamente (`ReporteDiario`)

Cuando el primer usuario registra un movimiento, el backend verifica si ya existe un `ReporteDiario` para la sucursal en la fecha contable de hoy (T-1). Si no existe, **lo crea automáticamente** con:

- `fecha_contable` = hoy − 1 día
- `saldo_arrastre_inicio` = `saldo_arrastre_fin` del reporte anterior de esa sucursal
- `tipo_cambio_usd_snapshot` = valor actual de `TIPO_CAMBIO_USD` en ConfiguracionGlobal
- `estado_reporte` = `ABIERTO`

```
ConfiguracionGlobal.TIPO_CAMBIO_USD ──snapshot──► ReporteDiario
ReporteDiario(anterior).saldo_arrastre_fin ──────► ReporteDiario(nuevo).saldo_arrastre_inicio
```

---

### Paso 1.2 — Captura de movimientos (`MovimientoDiario`)

El usuario (Contador o Gerente) registra los movimientos del día.

**¿Qué envía el frontend?**

```json
{
  "sucursal_id": 1,
  "concepto": 5,
  "monto": 1500.00,
  "monto_divisa": null,
  "tipo_divisa": null,
  "detalles_snapshot": {
    "responsable": "Juan López",
    "area_origen": "Caja principal"
  },
  "notas": "Venta del turno matutino"
}
```

**¿Qué hace el backend?**

1. Calcula el `ReporteDiario` correspondiente (T-1 para esa sucursal)
2. Verifica que el reporte esté en estado `ABIERTO`
3. Verifica que la hora actual esté dentro del `HORARIO_APERTURA` – `HORARIO_CIERRE`
4. Ignora cualquier campo `reporte` que haya enviado el frontend
5. Guarda el `MovimientoDiario` con `reporte` asignado internamente

**Tabla que se llena:** `movimientos_diarios`

```
movimientos_diarios
├── reporte_id  ────────────► reportes_diarios (asignado por backend)
├── concepto_id ────────────► conceptos
│       └── categoria_id ───► categorias_operativas
│       └── rubro_contable_id► rubro_contable
├── monto: 1500.00
└── detalles_snapshot: { "responsable": "Juan López" }
```

---

### Paso 1.3 — Estado de Resultados en tiempo real

En cualquier momento del día, el Director o cualquier usuario puede consultar el estado financiero:

```
GET /api/estado-resultados/?sucursal_id=1&mes=3&anio=2026
```

El endpoint agrega **en tiempo real** todos los `MovimientoDiario` del mes y los agrupa por `CategoriaOperativa` y `RubroContable`.

**Respuesta:**
```json
{
  "fuente": "tiempo_real",
  "total_ingresos": 120000.00,
  "total_egresos": 80000.00,
  "resultado_neto": 40000.00,
  "por_categoria": [
    { "categoria_nombre": "ADMINISTRACION", "total_ingresos": 5000, "total_egresos": 3000 },
    { "categoria_nombre": "BOOK", "total_ingresos": 95000, "total_egresos": 0 }
  ],
  "por_rubro": [
    { "rubro_nombre": "VENTAS_BEBIDAS", "total_ingresos": 5000 },
    { "rubro_nombre": "PAGO_RENTA", "total_egresos": 3000 }
  ]
}
```

---

### Paso 1.4 — Cierre del día (`ReporteDiario → CERRADO`)

Al finalizar el horario operativo, el día se cierra. Esto puede suceder de dos formas:

**Manual** (cualquier usuario autenticado):
```
POST /api/reportes/reportes-diarios/{id}/cerrar/
```

**Automático** (tarea Celery al llegar la hora de cierre).

**¿Qué hace el cierre?**

1. Suma todos los `MovimientoDiario` del reporte:
   - `total_ingresos` = suma de movimientos con `concepto.tipo = INGRESO`
   - `total_egresos` = suma de movimientos con `concepto.tipo = EGRESO`
   - `resultado_neto` = ingresos − egresos
2. Calcula `saldo_arrastre_fin` = `saldo_arrastre_inicio` + `resultado_neto`
3. Guarda snapshot inmutable del tipo de cambio actual
4. Marca `estado_reporte = CERRADO`
5. Registra quién y cuándo cerró

**A partir de este momento, ningún movimiento del día puede modificarse.**

> Solo el rol `ADMINISTRADOR` puede reabrir un día cerrado con:
> `POST /api/reportes/reportes-diarios/{id}/reabrir/`
> Toda reapertura queda registrada en el historial de `django-simple-history`.

---

## Fase 2 — Cierre mensual (se ejecuta al último día del mes)

### Paso 2.1 — Cierre del mes (`LibroEstadoResultados → CERRADO`)

Al cerrarse el último día del mes, la tarea Celery `cerrar_mes_contable` consolida todos los reportes diarios del mes en un registro mensual histórico.

**¿Qué contiene?**

| Campo | Origen |
|---|---|
| `total_ingresos` | Suma de `ReporteDiario.total_ingresos` del mes |
| `total_egresos` | Suma de `ReporteDiario.total_egresos` del mes |
| `resultado_neto` | Total ingresos − total egresos |
| `saldo_arrastre_inicio` | `saldo_arrastre_inicio` del primer reporte del mes |
| `saldo_arrastre_fin` | `saldo_arrastre_fin` del último reporte del mes |
| `tipo_cambio_usd_snapshot` | Tipo de cambio vigente al momento del cierre |
| `desglose_por_rubro` | JSON con totales por cada `RubroContable` |

**Regla crítica de inmutabilidad:**  
Una vez que el `LibroEstadoResultados` está `CERRADO`, **ningún cambio posterior** (tipo de cambio, configuraciones, etc.) modifica estos valores. Son una foto fija del mes.

```
saldo_arrastre_fin del mes actual ──────────► saldo_arrastre_inicio del mes siguiente
```

---

### Paso 2.2 — Consulta de meses cerrados

Cuando se consulta el Estado de Resultados de un mes ya cerrado, el endpoint devuelve directamente el snapshot histórico del `LibroEstadoResultados` **sin recalcular nada**:

```
GET /api/estado-resultados/?sucursal_id=1&mes=2&anio=2026
→ fuente: "snapshot_historico"  ← datos del libro cerrado
```

---

## Resumen visual del flujo completo

```
CONFIGURACIÓN INICIAL (una vez)
───────────────────────────────────────────────────────────
ConfiguracionGlobal → define horarios y tipos de cambio
RubroContable       → define cómo se agrupan los ingresos/egresos
Sucursal            → registra cada sala de juegos
FondoFijo           → asigna fondo a cada sucursal (1:1)
Rol + Permiso       → define qué puede hacer cada tipo de usuario
Usuario + UsuarioRol→ crea operadores y les asigna rol
CategoriaOperativa  → crea las pestañas (BOOK, ADMIN, DOLARES...)
Concepto            → los movimientos específicos de cada pestaña
DetalleParametrizado→ campos extra que requiere cada pestaña


CICLO DIARIO (todos los días en horario operativo)
───────────────────────────────────────────────────────────
        08:00 hrs (HORARIO_APERTURA)
           │
           ▼
       ReporteDiario (T-1) ← se crea automáticamente al primer movimiento
           │  ├── saldo_arrastre_inicio ← saldo_arrastre_fin del día anterior
           │  └── tipo_cambio_snapshot  ← ConfiguracionGlobal actual
           │
           ▼
     MovimientoDiario × N  ← el Contador registra movimientos durante el día
           │  ├── concepto → CategoriaOperativa → RubroContable
           │  └── detalles_snapshot (JSON inmutable)
           │
           ▼
     EstadoResultados (tiempo real) ← suma de MovimientoDiarios del mes
           │
        23:00 hrs (HORARIO_CIERRE)
           │
           ▼
     ReporteDiario.cerrar()
           │  ├── total_ingresos, total_egresos, resultado_neto
           │  ├── saldo_arrastre_fin = inicio + neto
           │  └── estado_reporte = CERRADO (inmutable)


CIERRE MENSUAL (último día del mes)
───────────────────────────────────────────────────────────
     LibroEstadoResultados
           │  ├── snapshot: totales, tipo de cambio, desglose por rubro
           │  └── estado_mes = CERRADO (INMUTABLE para siempre)
           │
           ▼
     EstadoResultados (modo snapshot) ← meses pasados se leen del libro, sin recalcular
```

---

## Preguntas frecuentes

**¿Qué pasa si se olvida registrar un movimiento?**  
Si el día aún está `ABIERTO` y estamos en horario, se puede agregar normalmente. Si el día ya cerró, el `ADMINISTRADOR` debe reabrirlo, agregar el movimiento y volver a cerrar manualmente.

**¿Qué pasa si el tipo de cambio cambió después de cerrar un reporte?**  
No afecta los reportes ya cerrados. Los snapshots son inmutables por diseño.

**¿Puedo consultar el State de Resultados de cualquier mes pasado?**  
Sí. Si el mes está cerrado, el endpoint devuelve el snapshot histórico al instante. Si el mes está en curso, agrega en tiempo real.

**¿Cómo sé cuánto dinero hay en caja ahora mismo?**  
Consulta `FondoFijo.saldo_actual` de la sucursal, o suma el `saldo_arrastre_fin` del último `ReporteDiario` cerrado + los movimientos del día en curso.

**¿En qué orden creo todo desde cero?**
```
1. ConfiguracionGlobal (horarios + tipos de cambio)
2. RubroContable
3. Sucursal
4. FondoFijo (por cada sucursal)
5. Rol → Permiso → RolPermiso
6. Usuario → UsuarioRol
7. CategoriaOperativa → Concepto → DetalleParametrizado
8. ¡Listo! El sistema puede operar.
```
