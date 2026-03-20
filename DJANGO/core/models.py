from django.db import models
from django.conf import settings
from django.utils import timezone

class ModeloBaseManager(models.Manager):
    """Manager por defecto que excluye registros físicamente eliminados y los eliminados lógicamente."""
    def get_queryset(self):
        return super().get_queryset().filter(eliminado_en__isnull=True)


class ModeloBase(models.Model):
    """
    Clase abstracta que provee campos de auditoría y máquina de estados
    para todos los modelos transaccionales del sistema.
    Implementa soft-delete (eliminación lógica) vía el campo `eliminado_en`.
    """

    class Estado(models.TextChoices):
        ACTIVO    = 'ACTIVO',    'Activo'
        INACTIVO  = 'INACTIVO',  'Inactivo'
        BLOQUEADO = 'BLOQUEADO', 'Bloqueado'
        ELIMINADO = 'ELIMINADO', 'Eliminado'

    # ── Máquina de estados ──────────────────────────────────────────────
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        verbose_name="Estado",
        help_text="Estado actual del registro dentro del ciclo de vida: ACTIVO, INACTIVO, BLOQUEADO o ELIMINADO."
    )

    # ── Auditoría temporal ──────────────────────────────────────────────
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
        help_text="Fecha y hora de creación del registro."
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
        help_text="Fecha y hora de la última actualización del registro."
    )
    eliminado_en = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Eliminado en",
        help_text="Fecha y hora en que el registro fue marcado como eliminado (Soft Delete). Si es nulo, el registro está vigente."
    )

    # ── Auditoría de usuarios ───────────────────────────────────────────
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="%(app_label)s_%(class)s_creado_por",
        verbose_name="Creado por",
        help_text="Usuario que creó el registro."
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="%(app_label)s_%(class)s_actualizado_por",
        verbose_name="Actualizado por",
        help_text="Usuario que realizó la última actualización."
    )
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="%(app_label)s_%(class)s_eliminado_por",
        verbose_name="Eliminado por",
        help_text="Usuario que eliminó el registro (Soft Delete)."
    )

    # ── Auditoría de valores ────────────────────────────────────────────
    valor_anterior = models.JSONField(
        null=True, blank=True,
        verbose_name="Valor anterior",
        help_text="Estado del registro antes de la última modificación (Auditoría)."
    )
    valor_actual = models.JSONField(
        null=True, blank=True,
        verbose_name="Valor actual",
        help_text="Estado del registro después de la última modificación (Auditoría)."
    )

    # ── Managers ────────────────────────────────────────────────────────
    objects     = ModeloBaseManager()   # Solo registros vigentes (default)
    todos       = models.Manager()      # Todos los registros incluyendo eliminados

    # ── Métodos de ciclo de vida ─────────────────────────────────────────
    def eliminar_logico(self, usuario=None):
        """Realiza un borrado lógico: marca el estado como ELIMINADO y registra la fecha."""
        self.estado = self.Estado.ELIMINADO
        self.eliminado_en = timezone.now()
        self.eliminado_por = usuario
        self.save(update_fields=['estado', 'eliminado_en', 'eliminado_por'])

    def activar(self):
        """Transición de estado hacia ACTIVO."""
        self.estado = self.Estado.ACTIVO
        self.eliminado_en = None
        self.eliminado_por = None
        self.save(update_fields=['estado', 'eliminado_en', 'eliminado_por'])

    def desactivar(self):
        """Transición de estado hacia INACTIVO."""
        self.estado = self.Estado.INACTIVO
        self.save(update_fields=['estado'])

    def bloquear(self):
        """Transición de estado hacia BLOQUEADO."""
        self.estado = self.Estado.BLOQUEADO
        self.save(update_fields=['estado'])

    def delete(self, using=None, keep_parents=False, usuario=None):
        """Sobreescritura de delete() para garantizar eliminación lógica siempre."""
        self.eliminar_logico(usuario=usuario)

    class Meta:
        abstract = True
