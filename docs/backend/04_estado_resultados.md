# Documentación del Módulo: Libro de Estado de Resultados

Este documento describe la arquitectura y comportamiento del módulo `libro_estado_resultados`. Este módulo se encarga de generar consolidaciones contables mensuales por sucursal, produciendo un "Snapshot Inmutable" (fotografía) del mes que no se verá afectado por cambios futuros en catálogos o tipos de cambio.

---

## 1. Arquitectura de Modelos (`models.py`)

### 1.1 `LibroEstadoResultados`
Representa el resumen financiero definitivo de un mes operativo.

- **Identificadores Únicos:** Combina `sucursal`, `anio` y `mes`.
- **Estados del Mes:**
  - `estado_mes`: Puede ser `ABIERTO` o `CERRADO`.
- **Totales Contables (Inmutables post-cierre):**
  - `total_ingresos`, `total_egresos`, `resultado_neto`.
  - `saldo_arrastre_inicio`: Saldo final del mes anterior.
  - `saldo_arrastre_fin`: Saldo inicio + neto del mes.
- **Snapshots de Auditoría:**
  - `tipo_cambio_usd_snapshot` y `tipo_cambio_eur_snapshot`: Recuperados de `ConfiguracionGlobal` en el instante exacto del cierre.
  - `desglose_por_rubro` (JSONField): El núcleo de la consolidación. Guarda una lista estructurada con la sumatoria de ingresos y egresos agrupados por `RubroContable`. Si el rubro contable cambia de nombre en el futuro, este JSON preserva la historia de cómo se llamó al momento del cierre.
- **Metadatos de Cierre:**
  - `cerrado_en` y `cerrado_por`: Auditoría de la acción de cierre.

---

## 2. Capa de Serialización (`serializers.py`)

La serialización es directa, exponiendo la información de la base de datos protegiendo los cálculos del lado del servidor.

- **`LibroEstadoResultadosSerializer`**:
  - Inyecta `sucursal_nombre` como campo de solo lectura.
  - Protege (`read_only`) estrictamente todos los campos calculados: `total_ingresos`, `total_egresos`, `resultado_neto`, `saldo_arrastre_fin`, `desglose_por_rubro`, y las auditorías de cierre. No se permite inyección manual de estos datos por la API.
- **`LibroEstadoResultadosListSerializer`**:
  - Excluye el `desglose_por_rubro` (que puede ser un JSON muy pesado) y los metadatos de cierre para agilizar la renderización de la tabla de libros mensuales.

---

## 3. Controladores y Vistas (`views.py`)

El ViewSet `LibroEstadoResultadosViewSet` administra el ciclo de vida del mes contable, aplicando complejas reglas de filtrado para los movimientos.

### 3.1 Reglas de Exclusión Contable (Helpers)
Durante el cierre de mes, NO todos los movimientos suman al total contable. Se aplican heurísticas de exclusión:
- **`_normalizar_texto_rubro()`**: Estandariza strings a mayúsculas sin guiones ni espacios.
- **`_rubro_es_no_contable()`**: Evalúa tanto el rubro hijo como el padre buscando identificadores o palabras clave como `SIN_RUBRO_CONTABLE`, `NO_CONTABLE` o `SIN_GRUPO`.
- **`_rubro_debe_considerarse_en_estado_resultados()`**: Verifica el flag `considerar_en_estado_resultados` del grupo padre del rubro. Si está en `False`, ese grupo es excluido del cálculo `total_ingresos`, `total_egresos` y `resultado_neto`.

### 3.2 Acción `cerrar_mes`
La función más crítica del módulo. Cuando es invocada mediante un POST:
1. **Recolección:** Busca en `MovimientoDiario` todos los movimientos que pertenezcan al año y mes solicitados, cruzando por la `sucursal_id`.
2. **Agrupación y Clasificación:**
   - Itera los movimientos y agrupa sus montos (en MXN) según el `RubroContable` asociado a su `Concepto`.
   - Si no tienen rubro, los manda a una bolsa "SIN_RUBRO_CONTABLE".
3. **Cálculo Condicionado:** 
   - Sumariza ingresos y egresos por rubro.
   - Suma al Total Global (Libro) ÚNICAMENTE aquellos rubros que pasaron la validación de `_rubro_debe_considerarse_en_estado_resultados`.
4. **Fijación de Variables (Snapshot):**
   - Inyecta las tasas USD/EUR vigentes.
   - Guarda el JSON ordenado jerárquicamente por padre.
5. **Cierre:** Cambia a `CERRADO`, estampa la fecha/usuario y guarda el modelo, volviéndolo inmutable a modificaciones por PATCH/PUT en la API.

---

## 4. Referencia de Endpoints API (`urls.py`)

Expuesto mediante DefaultRouter bajo `/api/libro_estado_resultados/libro-estado-resultados/`.

| Endpoint | Acción | Método | Descripción |
|----------|--------|--------|-------------|
| `/` | Listar | GET | Lista resumida. Acepta query params `sucursal_id` y `anio`. |
| `/` | Crear | POST | Inicializa un nuevo mes en estado ABIERTO (requiere sucursal, anio, mes, saldo_arrastre_inicio). |
| `/{id}/` | Detalle | GET | Devuelve cabecera completa con el JSON de `desglose_por_rubro`. |
| `/{id}/` | Actualizar | PATCH | Permite modificar datos menores (como observaciones) *solo si* el mes sigue ABIERTO. |
| `/{id}/` | Eliminar | DELETE | Soft-delete del registro (solo si está ABIERTO). |
| `/{id}/cerrar-mes/` | Cierre | POST | Ejecuta el algoritmo de consolidación, genera los snapshots y sella el registro a estado CERRADO. |

**Ejemplo Estructura Interna del JSON de Desglose**:
```json
[
  {
    "rubro_id": 15,
    "rubro_nombre": "VENTAS BEBIDAS",
    "rubro_tipo": "INGRESO",
    "rubro_padre": "VENTAS GENERALES",
    "rubro_padre_clave": "VTAS_GEN",
    "rubro_padre_considerar_en_estado_resultados": true,
    "total_ingresos": 45000.00,
    "total_egresos": 0.0,
    "resultado_neto": 45000.00
  },
  {
    "rubro_id": "SIN_RUBRO_CONTABLE",
    "rubro_nombre": "SIN RUBRO CONTABLE",
    "rubro_tipo": "NO_CONTABLE",
    "rubro_padre": "SIN GRUPO",
    "rubro_padre_clave": null,
    "rubro_padre_considerar_en_estado_resultados": false,
    "total_ingresos": 1000.0,
    "total_egresos": 0.0,
    "resultado_neto": 1000.0
  }
]
```
