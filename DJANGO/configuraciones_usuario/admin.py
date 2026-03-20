from django.contrib import admin
from .models import ConfiguracionUsuario


@admin.register(ConfiguracionUsuario)
class ConfiguracionUsuarioAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'tema', 'color_acento', 'densidad_ui', 'notificaciones_activas', 'creado_en')
    list_filter   = ('tema', 'color_acento', 'densidad_ui')
    search_fields = ('usuario__username', 'usuario__nombre')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por', 'actualizado_por')
