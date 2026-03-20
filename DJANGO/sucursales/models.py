from django.db import models
from core.models import ModeloBase


class Sucursal(ModeloBase):
    """
    Modelo que representa una sucursal (sala de juegos) del negocio.
    Cada sucursal es operada de manera independiente y tiene su propio
    fondo fijo y flujo de caja.
    """

    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre de la Sucursal",
        help_text="Nombre comercial único que identifica a la sucursal (ej. 'Sala Morelia Centro')."
    )
    clave = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Clave Interna",
        help_text="Código alfanumérico corto de identificación interna de la sucursal (ej. 'MOR-01')."
    )
    direccion = models.TextField(
        null=True, blank=True,
        verbose_name="Dirección",
        help_text="Domicilio completo de la sucursal."
    )
    ciudad = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="Ciudad",
        help_text="Ciudad o municipio donde se ubica la sucursal."
    )
    estado_republica = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="Estado (República)",
        help_text="Entidad federativa donde se ubica la sucursal."
    )
    telefono = models.CharField(
        max_length=20,
        null=True, blank=True,
        verbose_name="Teléfono",
        help_text="Número de teléfono de contacto de la sucursal."
    )
    correo = models.EmailField(
        null=True, blank=True,
        verbose_name="Correo Electrónico",
        help_text="Correo electrónico institucional de la sucursal."
    )
    encargado = models.CharField(
        max_length=150,
        null=True, blank=True,
        verbose_name="Responsable / Encargado",
        help_text="Nombre del responsable operativo de la sucursal."
    )
    fondo_inicial = models.DecimalField(
        max_digits=18, decimal_places=2,
        default=0.00,
        verbose_name="Fondo Inicial",
        help_text="Monto inicial asignado al fondo fijo de la sucursal en moneda nacional (MXN)."
    )

    def __str__(self):
        return f"{self.clave} – {self.nombre}"

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        db_table = "sucursales"
        ordering = ['nombre']
