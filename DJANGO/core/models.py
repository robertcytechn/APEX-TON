from django.db import models
from django.conf import settings

class ModeloBase(models.Model):
    """
    Clase abstracta que provee campos de auditoría para todos los modelos
    transaccionales del sistema.
    """
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en", help_text="Fecha y hora de creación del registro.")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado en", help_text="Fecha y hora de la última actualización del registro.")
    eliminado_en = models.DateTimeField(null=True, blank=True, verbose_name="Eliminado en", help_text="Fecha y hora en que el registro fue marcado como eliminado (Soft Delete).")
    
    # Suponiendo que el modelo de Usuario personalizado estará configurado en settings.AUTH_USER_MODEL
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_creado_por",
        verbose_name="Creado por",
        help_text="Usuario que creó el registro."
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_actualizado_por",
        verbose_name="Actualizado por",
        help_text="Usuario que realizó la última actualización."
    )
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_eliminado_por",
        verbose_name="Eliminado por",
        help_text="Usuario que eliminó el registro."
    )
    
    # Variables opcionales para almacenar valores anteriores y actuales en auditorías en texto/json
    valor_anterior = models.JSONField(null=True, blank=True, verbose_name="Valor anterior", help_text="Estado del registro antes de la última modificación (Auditoría).")
    valor_actual = models.JSONField(null=True, blank=True, verbose_name="Valor actual", help_text="Estado del registro después de la última modificación (Auditoría).")

    class Meta:
        abstract = True
