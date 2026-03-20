from django.db import models
from core.models import ModeloBase


class ConfiguracionUsuario(ModeloBase):
    """
    Preferencias de interfaz y comportamiento personalizadas por usuario.
    Relación 1:1 con Usuario. Se crea automáticamente al registrar el usuario.

    Incluye:
    - Preferencias visuales (tema, color, modo oscuro)
    - Preferencias de idioma y formato numérico
    - Preferencias de notificaciones
    - Campo JSON genérico para extensiones futuras sin migración
    """

    # ── Relación con usuario ─────────────────────────────────────────────────
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='configuracion',
        verbose_name="Usuario",
        help_text="Usuario propietario de estas preferencias de configuración. Relación 1:1."
    )

    # ── Apariencia visual ────────────────────────────────────────────────────
    class Tema(models.TextChoices):
        CLARO   = 'claro',   'Claro'
        OSCURO  = 'oscuro',  'Oscuro'
        SISTEMA = 'sistema', 'Seguir sistema operativo'

    tema = models.CharField(
        max_length=20,
        choices=Tema.choices,
        default=Tema.SISTEMA,
        verbose_name="Tema de color",
        help_text="Preferencia de tema visual: 'claro', 'oscuro' o 'sistema' (sigue la preferencia del SO del usuario)."
    )

    class ColorAcento(models.TextChoices):
        AZUL     = 'azul',     'Azul'
        MORADO   = 'morado',   'Morado'
        VERDE    = 'verde',    'Verde'
        NARANJA  = 'naranja',  'Naranja'
        ROJO     = 'rojo',     'Rojo'
        CYAN     = 'cyan',     'Cyan'
        PERSONALIZADO = 'personalizado', 'Personalizado (usa color_hex)'

    color_acento = models.CharField(
        max_length=20,
        choices=ColorAcento.choices,
        default=ColorAcento.AZUL,
        verbose_name="Color de acento",
        help_text="Color principal de la interfaz seleccionado por el usuario."
    )

    color_hex = models.CharField(
        max_length=7,
        null=True, blank=True,
        verbose_name="Color HEX personalizado",
        help_text="Color en formato hexadecimal (#RRGGBB) cuando color_acento='personalizado'. Ejemplo: '#7C3AED'."
    )

    # ── Densidad y tipografía ────────────────────────────────────────────────
    class Densidad(models.TextChoices):
        COMPACTA  = 'compacta',  'Compacta'
        NORMAL    = 'normal',    'Normal'
        ESPACIOSA = 'espaciosa', 'Espaciosa'

    densidad_ui = models.CharField(
        max_length=20,
        choices=Densidad.choices,
        default=Densidad.NORMAL,
        verbose_name="Densidad de la interfaz",
        help_text="Controla el espaciado general de la UI: 'compacta' para más filas visibles, 'espaciosa' para mejor legibilidad."
    )

    tamano_fuente = models.PositiveSmallIntegerField(
        default=14,
        verbose_name="Tamaño de fuente (px)",
        help_text="Tamaño base de la tipografía en píxeles. Rango recomendado: 12–20px."
    )

    # ── Formato regional ─────────────────────────────────────────────────────
    class FormatoFecha(models.TextChoices):
        DMY  = 'DD/MM/YYYY',  'DD/MM/YYYY'
        MDY  = 'MM/DD/YYYY',  'MM/DD/YYYY'
        YMD  = 'YYYY-MM-DD',  'YYYY-MM-DD'

    formato_fecha = models.CharField(
        max_length=12,
        choices=FormatoFecha.choices,
        default=FormatoFecha.DMY,
        verbose_name="Formato de fecha",
        help_text="Formato preferido para mostrar fechas en la interfaz."
    )

    class SeparadorMiles(models.TextChoices):
        COMA   = ',', 'Coma (1,000.00)'
        PUNTO  = '.', 'Punto (1.000,00)'

    separador_miles = models.CharField(
        max_length=1,
        choices=SeparadorMiles.choices,
        default=SeparadorMiles.COMA,
        verbose_name="Separador de miles",
        help_text="Carácter utilizado como separador de miles en cifras monetarias."
    )

    # ── Navegación y comportamiento ──────────────────────────────────────────
    menu_colapsado = models.BooleanField(
        default=False,
        verbose_name="Menú lateral colapsado",
        help_text="Si es True, el menú lateral de navegación inicia siempre colapsado."
    )

    pagina_inicio = models.CharField(
        max_length=100,
        default='dashboard',
        verbose_name="Página de inicio",
        help_text="Ruta o nombre de la vista que se carga al iniciar sesión (ej. 'dashboard', 'reportes')."
    )

    filas_por_pagina = models.PositiveSmallIntegerField(
        default=25,
        verbose_name="Filas por página en tablas",
        help_text="Número de registros mostrados por defecto en las paginaciones de tablas de datos. Valores comunes: 10, 25, 50, 100."
    )

    # ── Notificaciones ───────────────────────────────────────────────────────
    notificaciones_activas = models.BooleanField(
        default=True,
        verbose_name="Notificaciones activas",
        help_text="Habilita o deshabilita las notificaciones en tiempo real dentro de la aplicación."
    )

    sonido_notificaciones = models.BooleanField(
        default=False,
        verbose_name="Sonido en notificaciones",
        help_text="Si es True, se reproduce un sonido al recibir notificaciones en la app."
    )

    # ── Extensión futura (JSON genérico) ─────────────────────────────────────
    preferencias_extra = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Preferencias adicionales",
        help_text=(
            "Campo JSON de extensión genérica para almacenar preferencias futuras sin necesidad de migración. "
            "Ejemplo: {\"mostrar_tips\": true, \"columnas_ocultas\": [\"rfc\", \"correo\"]}."
        )
    )

    def __str__(self):
        return f"Configuración de {self.usuario.username} (tema={self.tema})"

    class Meta:
        verbose_name = "Configuración de Usuario"
        verbose_name_plural = "Configuraciones de Usuarios"
        db_table = "configuraciones_usuario"
