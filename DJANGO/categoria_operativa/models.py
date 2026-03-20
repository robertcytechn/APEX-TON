from django.db import models
from core.models import ModeloBase
from configuraciones_globales.models import RubroContable


# ─────────────────────────────────────────────────────────────────────────────
#  CATEGORÍA OPERATIVA  (Pestañas)
# ─────────────────────────────────────────────────────────────────────────────

class CategoriaOperativa(ModeloBase):
    """
    Representa una pestaña de agrupación de flujo operativo (ej. ADMINISTRACION, BOOK, BILLPOCKET).
    Es el nivel más alto de la jerarquía operativa. Cada pestaña agrupa conceptos
    de movimiento de dinero relacionados semánticamente.
    """

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de la Categoría",
        help_text="Nombre único de la pestaña operativa (ej. 'ADMINISTRACION', 'BOOK', 'DOLARES')."
    )
    clave = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Clave Interna",
        help_text="Clave alfanumérica abreviada para identificar la categoría en el sistema (ej. 'ADMIN', 'BOOK')."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Explicación del tipo de movimientos que agrupa esta categoría operativa."
    )
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('INGRESO', 'Ingreso'),
            ('EGRESO', 'Egreso'),
            ('MIXTO', 'Mixto'),
        ],
        default='MIXTO',
        verbose_name="Tipo General",
        help_text="Clasificación general del flujo de la pestaña: INGRESO, EGRESO o MIXTO (cuando puede tener ambos)."
    )
    orden = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Orden de Visualización",
        help_text="Número de posición para ordenar las categorías en la interfaz. Menor número = aparece primero."
    )

    def __str__(self):
        return f"{self.clave} – {self.nombre}"

    class Meta:
        verbose_name = "Categoría Operativa"
        verbose_name_plural = "Categorías Operativas"
        db_table = "categorias_operativas"
        ordering = ['orden', 'nombre']


# ─────────────────────────────────────────────────────────────────────────────
#  CONCEPTO  (Hijos de Categoría)
# ─────────────────────────────────────────────────────────────────────────────

class Concepto(ModeloBase):
    """
    Nomenclatura específica de un movimiento dentro de una CategoriaOperativa.
    Ejemplo: 'VENTA DE CAFE' dentro de la pestaña 'ADMINISTRACION'.
    Cada concepto está vinculado a un RubroContable global para la consolidación
    del Estado de Resultados.
    """

    categoria = models.ForeignKey(
        CategoriaOperativa,
        on_delete=models.PROTECT,
        related_name='conceptos',
        verbose_name="Categoría Operativa",
        help_text="Pestaña a la que pertenece este concepto. Un concepto pertenece invariablemente a una única pestaña."
    )
    rubro_contable = models.ForeignKey(
        RubroContable,
        on_delete=models.PROTECT,
        related_name='conceptos',
        verbose_name="Rubro Contable",
        help_text="Rubro contable global al que se conecta este concepto para la consolidación del Estado de Resultados."
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre del Concepto",
        help_text="Nombre del movimiento específico (ej. 'VENTA DE CAFE', 'PAGO DE RENTA')."
    )
    clave = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Clave del Concepto",
        help_text="Código único del concepto en el sistema (ej. 'ADMIN_VENTA_CAFE')."
    )
    tipo = models.CharField(
        max_length=20,
        choices=[('INGRESO', 'Ingreso'), ('EGRESO', 'Egreso')],
        verbose_name="Tipo",
        help_text="Indica si este concepto representa una entrada (Ingreso) o salida (Egreso) de dinero."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Descripción adicional del concepto y en qué contextos se aplica."
    )
    es_recurrente = models.BooleanField(
        default=False,
        verbose_name="¿Es Recurrente?",
        help_text="Indica si este concepto es recurrente (se repite periódicamente o diariamente)."
    )

    def __str__(self):
        return f"[{self.categoria.clave}] {self.nombre}"

    class Meta:
        verbose_name = "Concepto"
        verbose_name_plural = "Conceptos"
        db_table = "conceptos"
        ordering = ['categoria', 'nombre']
        unique_together = ('categoria', 'nombre')


# ─────────────────────────────────────────────────────────────────────────────
#  DETALLE PARAMETRIZADO  (Campos extra por Categoría)
# ─────────────────────────────────────────────────────────────────────────────

class DetalleParametrizado(ModeloBase):
    """
    Permite definir campos contextuales adicionales (clave-valor) para una CategoriaOperativa.
    Ejemplo: la pestaña 'SOBRANTES' puede tener los detalles:
      - 'responsable' (tipo TEXT)
      - 'area_origen'  (tipo TEXT)
      - 'monto_exacto' (tipo DECIMAL)
    Esto permite extender la información de cada pestaña sin modificar el esquema base.
    """

    TIPO_CHOICES = [
        ('TEXT',     'Texto'),
        ('DECIMAL',  'Decimal'),
        ('INT',      'Entero'),
        ('BOOLEAN',  'Booleano'),
        ('DATE',     'Fecha'),
        ('DATETIME', 'Fecha y Hora'),
    ]

    categoria = models.ForeignKey(
        CategoriaOperativa,
        on_delete=models.CASCADE,
        related_name='detalles_parametrizados',
        verbose_name="Categoría Operativa",
        help_text="Pestaña a la que pertenece este detalle parametrizado."
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre del Campo",
        help_text="Nombre descriptivo del campo adicional que se requiere para esta categoría (ej. 'responsable', 'area_origen')."
    )
    clave = models.CharField(
        max_length=80,
        verbose_name="Clave del Campo",
        help_text="Identificador técnico del campo en formato snake_case (ej. 'responsable', 'monto_exacto')."
    )
    tipo_valor = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='TEXT',
        verbose_name="Tipo de Valor",
        help_text="Tipo de dato esperado para este campo: TEXT, DECIMAL, INT, BOOLEAN, DATE o DATETIME."
    )
    requerido = models.BooleanField(
        default=False,
        verbose_name="¿Es requerido?",
        help_text="Indica si este campo es obligatorio al registrar un movimiento en la categoría."
    )
    valor_defecto = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Valor por Defecto",
        help_text="Valor predeterminado que se usa cuando no se proporciona uno explícitamente."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Explicación de para qué sirve este campo adicional y qué tipo de información captura."
    )

    def __str__(self):
        return f"[{self.categoria.clave}] {self.nombre} ({self.get_tipo_valor_display()})"

    class Meta:
        verbose_name = "Detalle Parametrizado"
        verbose_name_plural = "Detalles Parametrizados"
        db_table = "detalles_parametrizados"
        unique_together = ('categoria', 'clave')
        ordering = ['categoria', 'nombre']
