import os
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from simple_history.models import HistoricalRecords
from core.models import ModeloBase
from sucursales.models import Sucursal
from categoria_operativa.models import Concepto


# 1) Para qué sirve: limpiar segmentos de ruta para nombres de carpeta seguros.
# 2) Cómo funciona: aplica slugify y reemplaza guiones por guion bajo.
# 3) Qué hace: devuelve texto normalizado o un valor de respaldo cuando viene vacío.
# 4) Cómo editarla: ajusta reglas de normalización si se permiten más caracteres en rutas.
def _normalizar_segmento_carpeta(valor, respaldo):
    texto = (str(valor or '')).strip()
    texto_normalizado = slugify(texto, allow_unicode=False).replace('-', '_')
    return texto_normalizado or respaldo


# 1) Para qué sirve: construir ruta jerárquica para comprobantes de movimiento diario.
# 2) Cómo funciona: arma segmentos por sucursal/categoría/fecha y agrega UUID al nombre.
# 3) Qué hace: evita sobreescrituras y facilita trazabilidad de archivos de respaldo.
# 4) Cómo editarla: modifica la estructura de carpetas aquí si cambia la política documental.
def construir_ruta_archivo_respaldo(instancia, nombre_archivo):
    """
    Organiza los comprobantes en carpetas por:
    1) sucursal
    2) categoria operativa
    3) fecha contable
    y renombra el archivo con un identificador único para evitar sobreescritura.
    """
    sucursal_nombre = getattr(getattr(instancia, 'reporte', None), 'sucursal', None)
    sucursal_segmento = _normalizar_segmento_carpeta(getattr(sucursal_nombre, 'nombre', ''), 'sin_sucursal')

    categoria_obj = getattr(getattr(instancia, 'concepto', None), 'categoria', None)
    categoria_base = getattr(categoria_obj, 'clave', '') or getattr(categoria_obj, 'nombre', '')
    categoria_segmento = _normalizar_segmento_carpeta(categoria_base, 'sin_categoria')

    fecha_contable = getattr(getattr(instancia, 'reporte', None), 'fecha_contable', None)
    if not fecha_contable:
        fecha_contable = timezone.localdate() - timedelta(days=1)
    fecha_segmento = fecha_contable.strftime('%Y-%m-%d')

    nombre_base, extension = os.path.splitext(nombre_archivo or '')
    nombre_segmento = _normalizar_segmento_carpeta(nombre_base, 'archivo')
    extension_segmento = (extension or '').lower()
    identificador_unico = uuid.uuid4().hex
    nombre_final = f"{nombre_segmento}_{identificador_unico}{extension_segmento}"

    return f"comprobantes/{sucursal_segmento}/{categoria_segmento}/{fecha_segmento}/{nombre_final}"


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTE DIARIO  (Encabezado / Foto del día)
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: almacenar el encabezado histórico del día contable por sucursal.
# 2) Cómo funciona: concentra estados, snapshots, saldos y totales de cierre.
# 3) Qué hace: actúa como entidad principal para agrupar movimientos diarios.
# 4) Cómo editarla: incorpora nuevos campos históricos en este modelo para preservar trazabilidad.
class ReporteDiario(ModeloBase):
    """
    Encabezado del reporte histórico diario por sucursal.
    Representa una "fotografía" contable del día operativo (día contable = día anterior).
    
    Reglas de negocio clave:
    - El día contable es siempre D-1 (si hoy es 20 marzo, el día contable es 19 marzo).
    - Una vez CERRADO, ningún movimiento del día puede ser modificado.
    - Los valores de tipo de cambio se guardan como snapshot en el momento de creación;
      cambios posteriores en ConfiguracionGlobal NO afectan este registro.
    - El saldo_arrastre_inicio viene del saldo_arrastre_fin del reporte anterior.
    """

    class EstadoReporte(models.TextChoices):
        ABIERTO  = 'ABIERTO',  'Abierto'
        CERRADO  = 'CERRADO',  'Cerrado'

    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='reportes_diarios',
        verbose_name="Sucursal",
        help_text="Sucursal a la que pertenece este reporte diario."
    )
    fecha_contable = models.DateField(
        verbose_name="Fecha Contable",
        help_text="Fecha contable del reporte (siempre D-1: el día anterior al día operativo actual). Única por sucursal."
    )
    estado_reporte = models.CharField(
        max_length=10,
        choices=EstadoReporte.choices,
        default=EstadoReporte.ABIERTO,
        verbose_name="Estado del Reporte",
        help_text="ABIERTO: permite modificaciones dentro del horario. CERRADO: registro bloqueado permanentemente."
    )

    # ── Arrastre de saldo ──────────────────────────────────────────────────
    saldo_arrastre_inicio = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Saldo Arrastre Inicio",
        help_text="Saldo en caja al iniciar el día contable. Proviene del saldo_arrastre_fin del reporte anterior de esta sucursal."
    )
    saldo_arrastre_fin = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Saldo Arrastre Fin",
        help_text="Saldo en caja al cierre del día contable. Se convierte en el saldo_arrastre_inicio del siguiente reporte."
    )

    # ── Snapshot de variables globales al momento del corte ───────────────
    tipo_cambio_usd_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=0.0000,
        verbose_name="Tipo de Cambio USD (Snapshot)",
        help_text="Tipo de cambio MXN/USD vigente al momento de crear o cerrar el reporte. Se guarda como snapshot para garantizar integridad histórica."
    )
    tipo_cambio_eur_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=0.0000,
        verbose_name="Tipo de Cambio EUR (Snapshot)",
        help_text="Tipo de cambio MXN/EUR vigente al momento de crear o cerrar el reporte. Se guarda como snapshot."
    )

    # ── Resumen calculado del día ──────────────────────────────────────────
    total_ingresos = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Total Ingresos del Día",
        help_text="Suma total de todos los movimientos de tipo INGRESO del día. Se recalcula automáticamente al cerrar."
    )
    total_egresos = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Total Egresos del Día",
        help_text="Suma total de todos los movimientos de tipo EGRESO del día. Se recalcula automáticamente al cerrar."
    )
    resultado_neto = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Resultado Neto del Día",
        help_text="Diferencia entre total_ingresos y total_egresos. Representa el flujo neto del día contable."
    )

    # ── Metadatos de cierre ────────────────────────────────────────────────
    cerrado_en = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Cerrado en",
        help_text="Fecha y hora exacta en que se realizó el cierre del día contable."
    )
    cerrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reportes_cerrados',
        verbose_name="Cerrado por",
        help_text="Usuario que ejecutó el cierre del día."
    )
    observaciones = models.TextField(
        null=True, blank=True,
        verbose_name="Observaciones",
        help_text="Notas o comentarios adicionales sobre el cierre del día."
    )

    def __str__(self):
        return f"Reporte {self.fecha_contable} – {self.sucursal.nombre} [{self.estado_reporte}]"

    historial = HistoricalRecords(
        verbose_name="Historial de Reporte Diario",
        history_change_reason_field=models.TextField(null=True, blank=True),
    )

    class Meta:
        verbose_name = "Reporte Diario"
        verbose_name_plural = "Reportes Diarios"
        db_table = "reportes_diarios"
        unique_together = ('sucursal', 'fecha_contable')
        ordering = ['-fecha_contable', 'sucursal']


# ─────────────────────────────────────────────────────────────────────────────
#  MOVIMIENTO DIARIO  (Líneas del Reporte)
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: registrar cada movimiento individual asociado a un reporte diario.
# 2) Cómo funciona: vincula concepto/reporte y guarda monto, detalles snapshot y respaldo.
# 3) Qué hace: representa la unidad transaccional base para cálculos de ingresos/egresos.
# 4) Cómo editarla: agrega campos de captura nuevos manteniendo compatibilidad de historial.
class MovimientoDiario(ModeloBase):
    """
    Registro individual de un movimiento dentro de un ReporteDiario.
    Cada movimiento corresponde a un Concepto de una CategoriaOperativa y captura
    el monto en el momento del registro.
    
    Los detalles parametrizados de la categoría se almacenan como snapshot en JSON
    para garantizar inmutabilidad histórica.
    """

    reporte = models.ForeignKey(
        ReporteDiario,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name="Reporte Diario",
        help_text="Reporte diario al que pertenece este movimiento."
    )
    concepto = models.ForeignKey(
        Concepto,
        on_delete=models.PROTECT,
        related_name='movimientos_diarios',
        verbose_name="Concepto",
        help_text="Concepto operativo que clasifica este movimiento (ej. 'VENTA DE CAFE')."
    )

    # ── Valores del movimiento ─────────────────────────────────────────────
    monto = models.DecimalField(
        max_digits=18, decimal_places=2,
        verbose_name="Monto",
        help_text="Monto del movimiento en la moneda base (MXN). Siempre positivo; el tipo (ingreso/egreso) viene del concepto."
    )
    monto_divisa = models.DecimalField(
        max_digits=18, decimal_places=2,
        null=True, blank=True,
        verbose_name="Monto en Divisa",
        help_text="Monto en divisa extranjera si aplica (ej. USD o EUR). Nulo si el movimiento es solo en MXN."
    )
    tipo_divisa = models.CharField(
        max_length=10,
        null=True, blank=True,
        verbose_name="Tipo de Divisa",
        help_text="Código de la divisa del campo monto_divisa (ej. 'USD', 'EUR'). Nulo si solo aplica MXN."
    )

    # ── Snapshot de detalles parametrizados ───────────────────────────────
    detalles_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Detalles Parametrizados (Snapshot)",
        help_text="Valores de los detalles parametrizados de la categoría al momento del registro, guardados como JSON inmutable. Ejemplo: {\"responsable\": \"Juan\", \"area_origen\": \"Caja\"}."
    )

    # ── Metadatos ─────────────────────────────────────────────────────────
    notas = models.TextField(
        null=True, blank=True,
        verbose_name="Notas",
        help_text="Observaciones o aclaraciones específicas de este movimiento."
    )
    archivo_respaldo = models.FileField(
        upload_to=construir_ruta_archivo_respaldo,
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Archivo de Respaldo",
        help_text="Comprobante opcional del movimiento (imagen, PDF u otro archivo permitido)."
    )

    def __str__(self):
        return f"{self.reporte.fecha_contable} | {self.concepto.nombre} – ${self.monto:,.2f}"

    historial = HistoricalRecords(
        verbose_name="Historial de Movimiento Diario",
        history_change_reason_field=models.TextField(null=True, blank=True),
    )

    class Meta:
        verbose_name = "Movimiento Diario"
        verbose_name_plural = "Movimientos Diarios"
        db_table = "movimientos_diarios"
        ordering = ['reporte', 'concepto__categoria__orden']
