from django.db import models
from core.models import ModeloBase
from sucursales.models import Sucursal


class LibroEstadoResultados(ModeloBase):
    """
    Snapshot mensual histórico del Estado de Resultados por sucursal.
    Se genera al cerrar el mes y es INMUTABLE una vez creado.

    Regla de negocio: este registro es una foto fija del mes cerrado.
    Cualquier cambio posterior (tipo de cambio, configuraciones, etc.) NO afecta
    los valores ya guardados aquí.
    """

    class EstadoMes(models.TextChoices):
        ABIERTO  = 'ABIERTO',  'Abierto'
        CERRADO  = 'CERRADO',  'Cerrado'

    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='libros_estado_resultados',
        verbose_name="Sucursal",
        help_text="Sucursal a la que corresponde este estado de resultados mensual."
    )
    anio = models.PositiveSmallIntegerField(
        verbose_name="Año",
        help_text="Año contable del período (ej. 2026)."
    )
    mes = models.PositiveSmallIntegerField(
        verbose_name="Mes",
        help_text="Mes contable del período (1=Enero … 12=Diciembre)."
    )
    estado_mes = models.CharField(
        max_length=10,
        choices=EstadoMes.choices,
        default=EstadoMes.ABIERTO,
        verbose_name="Estado del Mes",
        help_text="ABIERTO: mes en curso. CERRADO: mes cerrado e inmutable."
    )

    # ── Snapshot de tipo de cambio al cierre ──────────────────────────────
    tipo_cambio_usd_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=0.0000,
        verbose_name="Tipo de Cambio USD (Snapshot)",
        help_text="Tipo de cambio MXN/USD vigente al momento del cierre del mes. Inmutable."
    )
    tipo_cambio_eur_snapshot = models.DecimalField(
        max_digits=12, decimal_places=4,
        default=0.0000,
        verbose_name="Tipo de Cambio EUR (Snapshot)",
        help_text="Tipo de cambio MXN/EUR vigente al momento del cierre del mes. Inmutable."
    )

    # ── Totales del mes ────────────────────────────────────────────────────
    total_ingresos = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Total Ingresos del Mes",
        help_text="Suma de todos los ingresos del mes. Calculado al cerrar."
    )
    total_egresos = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Total Egresos del Mes",
        help_text="Suma de todos los egresos del mes. Calculado al cerrar."
    )
    resultado_neto = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Resultado Neto del Mes",
        help_text="Diferencia total_ingresos - total_egresos del mes."
    )
    saldo_arrastre_inicio = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Saldo Arrastre Inicio de Mes",
        help_text="Saldo en caja con el que inició el mes (arrastre del mes anterior)."
    )
    saldo_arrastre_fin = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Saldo Arrastre Fin de Mes",
        help_text="Saldo final con el que cerró el mes. Se convierte en el inicio del siguiente."
    )

    # ── Desglose por rubro (snapshot JSON) ───────────────────────────────
    desglose_por_rubro = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Desglose por Rubro Contable",
        help_text="Snapshot JSON con totales agrupados por rubro contable al momento del cierre. Ejemplo: {\"VENTAS_BEBIDAS\": 15000.00, \"PAGO_RENTA\": -8000.00}."
    )

    # ── Metadatos de cierre ────────────────────────────────────────────────
    cerrado_en = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Cerrado en",
        help_text="Fecha y hora en que se cerró el período mensual."
    )
    cerrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='libros_cerrados',
        verbose_name="Cerrado por",
        help_text="Usuario que ejecutó el cierre del mes."
    )
    observaciones = models.TextField(
        null=True, blank=True,
        verbose_name="Observaciones",
        help_text="Notas o comentarios del cierre mensual."
    )

    def __str__(self):
        return f"Estado Resultados {self.anio}/{self.mes:02d} – {self.sucursal.nombre} [{self.estado_mes}]"

    class Meta:
        verbose_name = "Libro Estado de Resultados"
        verbose_name_plural = "Libros Estado de Resultados"
        db_table = "libro_estado_resultados"
        unique_together = ('sucursal', 'anio', 'mes')
        ordering = ['-anio', '-mes', 'sucursal']
