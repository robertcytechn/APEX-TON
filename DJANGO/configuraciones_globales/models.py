from django.db import models
from simple_history.models import HistoricalRecords
from core.models import ModeloBase


class PadreRubroContable(ModeloBase):
    """
    Catalogo administrable de padres para rubros contables.
    """
    clave = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Clave del Padre",
        help_text="Identificador unico del padre de rubro en formato tecnico (ej. GASTOS)."
    )
    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre del Padre",
        help_text="Nombre visible del padre de rubro para uso en catalogos y formularios."
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripcion",
        help_text="Descripcion opcional del padre de rubro contable."
    )
    considerar_en_estado_resultados = models.BooleanField(
        default=True,
        verbose_name="Considerar en Estado de Resultados",
        help_text="Indica si los rubros de este padre deben impactar los totales generales del estado de resultados."
    )

    class Meta:
        verbose_name = "Padre de Rubro Contable"
        verbose_name_plural = "Padres de Rubros Contables"
        db_table = "padre_rubro_contable"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.clave})"

class ConfiguracionGlobal(ModeloBase):
    """
    Modelo para gestionar variables globales del sistema, como
    el tipo de cambio o parámetros de la empresa que son aplicables a todas
    las sucursales (ej. cambio de divisas).
    """
    TIPO_VALOR_CHOICES = [
        ('STRING', 'Texto'),
        ('INT', 'Entero'),
        ('FLOAT', 'Decimal'),
        ('BOOLEAN', 'Booleano'),
        ('DATE', 'Fecha'),
        ('TIME', 'Hora'),
        ('DATETIME', 'Fecha y Hora'),
        ('JSON', 'JSON'),
    ]

    clave = models.CharField(max_length=100, unique=True, verbose_name="Clave de Configuración", help_text="Identificador único para la variable de configuración (ej. TIPO_CAMBIO_DOLAR).")
    valor = models.TextField(verbose_name="Valor de Configuración", help_text="Valor asignado a la configuración. Se debe tratar según el tipo de valor.")
    tipo_valor = models.CharField(
        max_length=20, 
        choices=TIPO_VALOR_CHOICES, 
        default='STRING', 
        verbose_name="Tipo de Valor",
        help_text="Determina cómo debe ser interpretado o parseado el contenido del campo valor."
    )
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción", help_text="Explicación detallada del propósito u observaciones de esta configuración.")

    @property
    def valor_tipado(self):
        """Devuelve el valor convertido a su tipo correspondiente."""
        import json
        from django.utils.dateparse import parse_date, parse_time, parse_datetime

        if self.valor is None or self.valor == '':
            return None

        try:
            if self.tipo_valor == 'INT':
                return int(self.valor)
            elif self.tipo_valor == 'FLOAT':
                return float(self.valor)
            elif self.tipo_valor == 'BOOLEAN':
                return self.valor.lower() in ('true', '1', 't', 'y', 'yes', 'sí', 'si', 'verdadero')
            elif self.tipo_valor == 'DATE':
                return parse_date(self.valor)
            elif self.tipo_valor == 'TIME':
                return parse_time(self.valor)
            elif self.tipo_valor == 'DATETIME':
                return parse_datetime(self.valor)
            elif self.tipo_valor == 'JSON':
                return json.loads(self.valor)
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.valor # o none para no retornar el valor en texto

        return str(self.valor)

    def __str__(self):
        return f"{self.clave}: {self.valor} ({self.get_tipo_valor_display()})"

    class Meta:
        verbose_name = "Configuración Global"
        verbose_name_plural = "Configuraciones Globales"
        db_table = "configuraciones_globales"

class RubroContable(ModeloBase):
    """
    Modelo para los rubros contables globales (ej. VENTAS_BEBIDAS).
    """
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre del Rubro",
        help_text="Nombre representativo del rubro contable. Debe ser unico dentro de su padre de rubro."
    )
    padre = models.ForeignKey(
        PadreRubroContable,
        on_delete=models.PROTECT,
        related_name="rubros_contables",
        verbose_name="Padre del Rubro",
        help_text="Padre de rubro al que pertenece este rubro para su agrupacion contable."
    )
    tipo = models.CharField(
        max_length=20,
        choices=[('INGRESO', 'Ingreso'), ('EGRESO', 'Egreso')],
        verbose_name="Tipo de Rubro",
        help_text="Clasificación general del rubro indicando si representa entrada (Ingreso) o salida (Egreso) de dinero."
    )
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción", help_text="Detalles adicionales sobre lo que contempla este rubro.")

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"
        
    class Meta:
        verbose_name = "Rubro Contable"
        verbose_name_plural = "Rubros Contables"
        db_table = "rubro_contable"
        constraints = [
            models.UniqueConstraint(fields=["nombre", "padre"], name="uq_rubrocontable_nombre_padre"),
        ]
