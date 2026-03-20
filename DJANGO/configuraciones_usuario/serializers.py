from rest_framework import serializers
from .models import ConfiguracionUsuario


class ConfiguracionUsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador completo para ConfiguracionUsuario.
    El campo 'usuario' es de solo lectura; siempre se asigna desde el
    usuario autenticado en la vista, nunca desde el payload del cliente.
    """

    usuario_username = serializers.CharField(
        source='usuario.username',
        read_only=True,
        help_text="Nombre de usuario del propietario de la configuración."
    )
    usuario_nombre = serializers.CharField(
        source='usuario.nombre',
        read_only=True,
        help_text="Nombre completo del propietario."
    )

    class Meta:
        model = ConfiguracionUsuario
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'usuario_nombre',
            # Apariencia
            'tema',
            'color_acento',
            'color_hex',
            'densidad_ui',
            'tamano_fuente',
            # Formato regional
            'formato_fecha',
            'separador_miles',
            # Navegación
            'menu_colapsado',
            'pagina_inicio',
            'filas_por_pagina',
            # Notificaciones
            'notificaciones_activas',
            'sonido_notificaciones',
            # Extensión
            'preferencias_extra',
            # Auditoría (heredados de ModeloBase)
            'estado',
            'creado_en',
            'actualizado_en',
        ]
        read_only_fields = ['id', 'usuario', 'creado_en', 'actualizado_en', 'estado']
