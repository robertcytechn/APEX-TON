from django.db import models
from core.models import ModeloBase
from sucursales.models import Sucursal


class FondoFijo(ModeloBase):
    """
    Representa el fondo fijo (caja chica) asignado a una sucursal específica.
    Cada sucursal opera su propio fondo de manera independiente.
    El saldo_actual se recalcula en base a los movimientos registrados.
    """

    sucursal = models.OneToOneField(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='fondo_fijo',
        verbose_name="Sucursal",
        help_text="Sucursal a la que pertenece este fondo fijo. Relación única (1:1)."
    )
    monto_autorizado = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Monto Autorizado",
        help_text="Monto máximo autorizado para el fondo fijo de la sucursal en MXN."
    )
    saldo_actual = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Saldo Actual",
        help_text="Saldo disponible actual en el fondo fijo. Se actualiza con cada movimiento registrado."
    )
    moneda = models.CharField(
        max_length=10,
        default='MXN',
        verbose_name="Moneda",
        help_text="Código de la moneda en que opera el fondo fijo (ej. MXN, USD)."
    )
    observaciones = models.TextField(
        null=True, blank=True,
        verbose_name="Observaciones",
        help_text="Notas o comentarios adicionales relevantes para la administración del fondo."
    )

    def __str__(self):
        return f"Fondo Fijo – {self.sucursal.nombre} (${self.saldo_actual:,.2f} {self.moneda})"

    class Meta:
        verbose_name = "Fondo Fijo"
        verbose_name_plural = "Fondos Fijos"
        db_table = "fondos_fijos"
