import os
from pathlib import Path

from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.text import slugify
from core.models import ModeloBase
from sucursales.models import Sucursal


# 1) Para qué sirve: normalizar nombres para usarlos de forma segura en rutas.
# 2) Cómo funciona: aplica slugify y reemplaza guiones por guion bajo.
# 3) Qué hace: evita caracteres inválidos en carpetas de media.
# 4) Cómo editarla: ajusta reglas de normalización si se permite otro formato.
def _normalizar_segmento_carpeta(valor, respaldo):
    texto = (str(valor or '')).strip()
    texto_normalizado = slugify(texto, allow_unicode=False).replace('-', '_')
    return texto_normalizado or respaldo


# 1) Para qué sirve: construir ruta de almacenamiento de foto de perfil por casino y usuario.
# 2) Cómo funciona: lee sucursal/id del usuario, crea carpetas si no existen y retorna ruta relativa.
# 3) Qué hace: guarda archivos como media/<casino>/<id_usuario>/images/perfil.ext.
# 4) Cómo editarla: cambia jerarquía si se requiere otro estándar documental.
def construir_ruta_imagen_perfil_usuario(instancia, nombre_archivo):
    sucursal = getattr(instancia, 'sucursal', None)
    nombre_casino = getattr(sucursal, 'nombre', '')
    casino_segmento = _normalizar_segmento_carpeta(nombre_casino, 'casino_global')

    id_usuario = getattr(instancia, 'pk', None) or 'sin_id'
    extension = os.path.splitext(nombre_archivo or '')[1].lower() or '.jpg'
    nombre_final = f"perfil{extension}"

    directorio_absoluto = Path(settings.MEDIA_ROOT) / casino_segmento / str(id_usuario) / 'images'
    directorio_absoluto.mkdir(parents=True, exist_ok=True)

    return f"{casino_segmento}/{id_usuario}/images/{nombre_final}"


# ─────────────────────────────────────────────────────────────────────────────
#  ROL
# ─────────────────────────────────────────────────────────────────────────────

class Rol(ModeloBase):
    """
    Define los roles del sistema (ej. Administrador, Cajero, Auditor).
    Los permisos SIEMPRE se asignan por Rol, nunca directamente a un usuario.
    """

    nombre = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="Nombre del Rol",
        help_text="Nombre único del rol dentro del sistema (ej. 'Administrador', 'Cajero')."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Descripción del alcance y responsabilidades que corresponden a este rol."
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        db_table = "roles"


# ─────────────────────────────────────────────────────────────────────────────
#  PERMISO
# ─────────────────────────────────────────────────────────────────────────────

class Permiso(ModeloBase):
    """
    Permiso granular que puede ser asignado a un Rol.
    Los permisos definen acciones específicas dentro del sistema.
    """

    codigo = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Código del Permiso",
        help_text="Identificador único del permiso en formato MODULO_ACCION (ej. 'SUCURSALES_CREAR')."
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre del Permiso",
        help_text="Nombre descriptivo y legible del permiso (ej. 'Crear Sucursales')."
    )
    modulo = models.CharField(
        max_length=80,
        verbose_name="Módulo",
        help_text="Módulo o sección del sistema al que pertenece el permiso (ej. 'SUCURSALES', 'TESORERÍA')."
    )
    descripcion = models.TextField(
        null=True, blank=True,
        verbose_name="Descripción",
        help_text="Detalle sobre qué permite hacer este permiso dentro del sistema."
    )

    def __str__(self):
        return f"{self.codigo} – {self.nombre}"

    class Meta:
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"
        db_table = "permisos"


# ─────────────────────────────────────────────────────────────────────────────
#  ROL ↔ PERMISO  (tabla intermedia)
# ─────────────────────────────────────────────────────────────────────────────

class RolPermiso(ModeloBase):
    """
    Tabla intermedia que asigna Permisos a Roles.
    Un Rol puede tener múltiples Permisos y un Permiso puede estar en múltiples Roles.
    """

    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        related_name='rol_permisos',
        verbose_name="Rol",
        help_text="Rol al que se le asigna el permiso."
    )
    permiso = models.ForeignKey(
        Permiso,
        on_delete=models.CASCADE,
        related_name='rol_permisos',
        verbose_name="Permiso",
        help_text="Permiso que se le otorga al rol."
    )

    def __str__(self):
        return f"{self.rol.nombre} → {self.permiso.codigo}"

    class Meta:
        verbose_name = "Rol – Permiso"
        verbose_name_plural = "Roles – Permisos"
        db_table = "roles_permisos"
        unique_together = ('rol', 'permiso')


# ─────────────────────────────────────────────────────────────────────────────
#  MANAGER DE USUARIO
# ─────────────────────────────────────────────────────────────────────────────

class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        usuario = self.model(username=username, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIO
# ─────────────────────────────────────────────────────────────────────────────

class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Modelo principal de usuario del sistema.
    Extiende AbstractBaseUser para personalizar el login con 'username'.
    La sucursal es opcional: un usuario puede ser global (sin sucursal) o pertenecer a una.
    """

    username = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="Nombre de Usuario",
        help_text="Identificador único para el inicio de sesión."
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre Completo",
        help_text="Nombre completo del usuario."
    )
    correo = models.EmailField(
        null=True, blank=True,
        verbose_name="Correo Electrónico",
        help_text="Correo electrónico del usuario (opcional)."
    )
    foto_perfil = models.ImageField(
        upload_to=construir_ruta_imagen_perfil_usuario,
        null=True,
        blank=True,
        verbose_name="Foto de Perfil",
        help_text="Imagen de perfil del usuario. Se guarda en media/<casino>/<id_usuario>/images/."
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='usuarios',
        verbose_name="Sucursal",
        help_text="Sucursal a la que pertenece el usuario. Puede ser nulo si el usuario es global (aplica a toda la empresa)."
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Indica si el usuario puede iniciar sesión."
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Es Staff",
        help_text="Indica si el usuario tiene acceso al sitio de administración de Django."
    )
    requiere_cambio_password = models.BooleanField(
        default=False,
        verbose_name="Requiere cambio de contraseña",
        help_text="Indica si el usuario debe cambiar su contraseña de forma obligatoria al iniciar sesión."
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
        help_text="Fecha y hora en que se registró el usuario."
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado en",
        help_text="Fecha y hora de la última modificación del usuario."
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombre']

    def __str__(self):
        return f"{self.username} – {self.nombre}"

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuarios"


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIO ↔ ROL  (tabla intermedia)
# ─────────────────────────────────────────────────────────────────────────────

class UsuarioRol(models.Model):
    """
    Tabla intermedia que asigna Roles a Usuarios.
    Un Usuario puede tener múltiples Roles.
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='usuario_roles',
        verbose_name="Usuario",
        help_text="Usuario al que se le asigna el rol."
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        related_name='usuario_roles',
        verbose_name="Rol",
        help_text="Rol que se le asigna al usuario."
    )
    asignado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Asignado en",
        help_text="Fecha y hora en que se asignó el rol al usuario."
    )

    def __str__(self):
        return f"{self.usuario.username} → {self.rol.nombre}"

    class Meta:
        verbose_name = "Usuario – Rol"
        verbose_name_plural = "Usuarios – Roles"
        db_table = "usuarios_roles"
        unique_together = ('usuario', 'rol')


class TicketSoporteTecnico(ModeloBase):
    """
    Registro histórico de tickets de soporte técnico levantados desde frontend.
    Persiste datos del formulario y metadatos del usuario para trazabilidad.
    """

    class EstadoSeguimiento(models.TextChoices):
        NUEVO = 'NUEVO', 'Nuevo'
        EN_PROCESO = 'EN_PROCESO', 'En proceso'
        COMPLETADO = 'COMPLETADO', 'Completado'
        DESCARTADO = 'DESCARTADO', 'Descartado'

    folio = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        verbose_name='Folio',
        help_text='Folio único del ticket de soporte (ej. ST-20260419-120300-15-AB12CD).',
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_soporte_levantados',
        verbose_name='Usuario solicitante',
        help_text='Usuario autenticado que levantó el ticket.',
    )
    usuario_nombre = models.CharField(
        max_length=180,
        verbose_name='Nombre del usuario',
        help_text='Nombre visible del usuario al momento de levantar el ticket.',
    )
    usuario_username = models.CharField(
        max_length=100,
        verbose_name='Username del usuario',
        help_text='Identificador de cuenta del usuario al momento de levantar el ticket.',
    )
    usuario_correo = models.EmailField(
        null=True,
        blank=True,
        verbose_name='Correo del usuario',
        help_text='Correo del usuario al momento de levantar el ticket.',
    )
    usuario_sucursal = models.CharField(
        max_length=180,
        blank=True,
        default='',
        verbose_name='Sucursal del usuario',
        help_text='Sucursal asociada al usuario al momento de levantar el ticket.',
    )
    usuario_roles = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Roles del usuario',
        help_text='Lista de roles del usuario al momento de levantar el ticket.',
    )

    problema_principal = models.CharField(
        max_length=40,
        verbose_name='Problema principal (código)',
        help_text='Clave del problema principal seleccionado en formulario.',
    )
    problema_principal_etiqueta = models.CharField(
        max_length=220,
        verbose_name='Problema principal',
        help_text='Etiqueta textual del problema principal.',
    )
    areas_afectadas = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Áreas afectadas (códigos)',
        help_text='Lista de claves de áreas afectadas seleccionadas.',
    )
    areas_afectadas_etiquetas = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Áreas afectadas',
        help_text='Lista de etiquetas de áreas afectadas seleccionadas.',
    )
    comportamiento_observado = models.CharField(
        max_length=50,
        verbose_name='Comportamiento observado (código)',
        help_text='Clave de comportamiento observado seleccionada.',
    )
    comportamiento_observado_etiqueta = models.CharField(
        max_length=220,
        verbose_name='Comportamiento observado',
        help_text='Etiqueta textual del comportamiento observado.',
    )
    prioridad = models.CharField(
        max_length=20,
        default='MEDIA',
        verbose_name='Prioridad (código)',
        help_text='Clave de prioridad seleccionada.',
    )
    prioridad_etiqueta = models.CharField(
        max_length=60,
        default='Media',
        verbose_name='Prioridad',
        help_text='Etiqueta textual de prioridad.',
    )
    dispositivo = models.CharField(
        max_length=20,
        default='ESCRITORIO',
        verbose_name='Dispositivo (código)',
        help_text='Clave del dispositivo reportado.',
    )
    dispositivo_etiqueta = models.CharField(
        max_length=80,
        default='Equipo de escritorio',
        verbose_name='Dispositivo',
        help_text='Etiqueta textual de dispositivo.',
    )
    pagina_afectada = models.CharField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='Página afectada',
        help_text='Ruta/pantalla reportada por el usuario.',
    )
    descripcion_detallada = models.TextField(
        verbose_name='Descripción detallada',
        help_text='Descripción principal del incidente.',
    )
    pasos_reproduccion = models.TextField(
        blank=True,
        default='',
        verbose_name='Pasos para reproducir',
        help_text='Secuencia opcional para reproducir el incidente.',
    )
    bloqueo_operativo = models.BooleanField(
        default=False,
        verbose_name='Bloqueo operativo',
        help_text='Indica si el incidente bloquea operación diaria del usuario.',
    )

    estado_seguimiento = models.CharField(
        max_length=20,
        choices=EstadoSeguimiento.choices,
        default=EstadoSeguimiento.NUEVO,
        verbose_name='Estado de seguimiento',
        help_text='Estado de atención administrativa del ticket.',
    )
    notas_seguimiento = models.TextField(
        blank=True,
        default='',
        verbose_name='Notas de seguimiento',
        help_text='Notas internas del administrador sobre el avance/cierre.',
    )
    atendido_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_soporte_atendidos',
        verbose_name='Atendido por',
        help_text='Administrador que actualizó el estado del ticket por última vez.',
    )
    atendido_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Atendido en',
        help_text='Fecha y hora de la última actualización de seguimiento.',
    )
    resuelto_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Resuelto en',
        help_text='Fecha y hora en que el ticket fue marcado como completado.',
    )

    correo_soporte_enviado = models.BooleanField(
        default=False,
        verbose_name='Correo a soporte enviado',
        help_text='Indica si el correo al canal de soporte técnico se envió correctamente.',
    )
    correo_confirmacion_enviado = models.BooleanField(
        default=False,
        verbose_name='Correo de confirmación enviado',
        help_text='Indica si se notificó al usuario solicitante con folio del ticket.',
    )
    detalle_error_envio = models.TextField(
        blank=True,
        default='',
        verbose_name='Detalle de error de envío',
        help_text='Detalle técnico de errores de envío de correo (si aplica).',
    )

    def __str__(self):
        return f"{self.folio} - {self.problema_principal_etiqueta}"

    class Meta:
        verbose_name = 'Ticket de Soporte Técnico'
        verbose_name_plural = 'Tickets de Soporte Técnico'
        db_table = 'tickets_soporte_tecnico'
        ordering = ['-creado_en']
