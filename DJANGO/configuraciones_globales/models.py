from django.db import models
from simple_history.models import HistoricalRecords
from core.models import ModeloBase

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
    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre del Rubro", help_text="Nombre representativo y único del rubro contable.")
    padre = models.CharField(max_length=150, verbose_name="Padre del Rubro", choices=[
        ('NINGUNO', 'Ninguno'), 
        ('INGRESOS', 'Ingresos'),
        ('GASTOS', 'Gastos'),
        ('CARGAR_FISCALES', 'Cargar Fiscales'),
        ('COCINA','Cosina'),
        ('JUEGO_VIVO', 'Juego Vivo'),
        ('PAGO_MAQUINAS', 'Pago Maquinas'),
        ('OTROS_INGRESOS', 'Otros Ingresos'),
        ('OTROS_GASTOS', 'Otros Gastos')], default='NINGUNO', help_text="Categoría o pestaña general a la que pertenece este rubro para su agrupación.")
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
