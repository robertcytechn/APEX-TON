from django.db import models
from core.models import ModeloBase


class FondoFijo(ModeloBase):
    """
    Catálogo maestro de tipos de fondos fijos.
    No guarda montos, únicamente metadatos descriptivos.
    """

    nombre = models.CharField(
        max_length=120,
        unique=True,
        verbose_name="Nombre",
        help_text="Nombre único del tipo de fondo fijo (ej. 'Caja Chica', 'Juego Vivo')."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Descripción del propósito operativo del fondo fijo dentro de la organización."
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Fondo Fijo"
        verbose_name_plural = "Fondos Fijos"
        db_table = "fondos_fijos"


class SucursalFondoFijo(ModeloBase):
    """
    Relación intermedia que almacena el monto asignado de un fondo fijo por sucursal.
    """

    sucursal = models.ForeignKey(
        'sucursales.Sucursal',
        on_delete=models.PROTECT,
        related_name='asignaciones_fondos_fijos',
        verbose_name="Sucursal",
        help_text="Sucursal a la que se asigna el fondo fijo."
    )
    fondo_fijo = models.ForeignKey(
        FondoFijo,
        on_delete=models.PROTECT,
        related_name='asignaciones_sucursales',
        verbose_name="Fondo fijo",
        help_text="Tipo de fondo fijo del catálogo maestro que se asigna a la sucursal."
    )
    monto_asignado = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0.00,
        verbose_name="Monto asignado",
        help_text="Valor monetario asignado para este fondo fijo en la sucursal, con 2 decimales."
    )

    def __str__(self):
        return f"{self.sucursal.nombre} - {self.fondo_fijo.nombre}: {self.monto_asignado:,.2f}"

    class Meta:
        verbose_name = "Sucursal Fondo Fijo"
        verbose_name_plural = "Sucursales Fondos Fijos"
        db_table = "sucursales_fondos_fijos"
        unique_together = ('sucursal', 'fondo_fijo')
