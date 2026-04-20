from rest_framework import serializers
from .models import Rol, Permiso, RolPermiso, Usuario, UsuarioRol, TicketSoporteTecnico


class PermisoSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo Permiso."""
    class Meta:
        model = Permiso
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class RolPermisoSerializer(serializers.ModelSerializer):
    """Serializador para la tabla intermedia Rol ↔ Permiso."""
    permiso_codigo = serializers.CharField(source='permiso.codigo', read_only=True)
    permiso_nombre = serializers.CharField(source='permiso.nombre', read_only=True)

    class Meta:
        model = RolPermiso
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class RolSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo Rol, incluye sus permisos."""
    permisos = RolPermisoSerializer(source='rol_permisos', many=True, read_only=True)

    class Meta:
        model = Rol
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class UsuarioRolSerializer(serializers.ModelSerializer):
    """Serializador para la tabla intermedia Usuario ↔ Rol."""
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)

    class Meta:
        model = UsuarioRol
        fields = '__all__'
        read_only_fields = ('asignado_en',)


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo Usuario."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    roles = UsuarioRolSerializer(source='usuario_roles', many=True, read_only=True)
    password = serializers.CharField(write_only=True, required=False, help_text="Contraseña del usuario. Solo escritura.")
    foto_perfil_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            'id', 'username', 'nombre', 'correo', 'sucursal', 'sucursal_nombre',
            'foto_perfil', 'foto_perfil_url',
            'is_active', 'is_staff', 'creado_en', 'actualizado_en',
            'roles', 'password',
        )
        read_only_fields = ('creado_en', 'actualizado_en')

    def get_foto_perfil_url(self, obj):
        if not getattr(obj, 'foto_perfil', None):
            return None
        return obj.foto_perfil.url

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        usuario = super().create(validated_data)
        if password:
            usuario.set_password(password)
            usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        usuario = super().update(instance, validated_data)
        if password:
            usuario.set_password(password)
            usuario.save()
        return usuario


class UsuarioListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listados de usuarios."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    foto_perfil_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Usuario
        fields = ('id', 'username', 'nombre', 'correo', 'sucursal_nombre', 'foto_perfil_url', 'is_active')

    def get_foto_perfil_url(self, obj):
        if not getattr(obj, 'foto_perfil', None):
            return None
        return obj.foto_perfil.url


class SolicitudSoporteTecnicoSerializer(serializers.Serializer):
    """Valida solicitudes de soporte técnico enviadas por usuarios autenticados."""

    PROBLEMAS_PRINCIPALES = (
        ('ACCESO', 'No puedo iniciar sesión o perdí acceso'),
        ('CAPTURA', 'Error en captura operativa'),
        ('REPORTES', 'Inconsistencia en reportes o estadísticas'),
        ('RENDIMIENTO', 'Pantalla lenta o bloqueada'),
        ('INTEGRACION', 'Problema con correo, exportación o integración'),
        ('OTRO', 'Otro problema técnico'),
    )

    AREAS_AFECTADAS = (
        ('LOGIN', 'Inicio de sesión y perfil'),
        ('INICIO', 'Panel de inicio'),
        ('CAPTURA_OPERATIVA', 'Captura operativa'),
        ('REPORTE_DIARIO', 'Reporte diario'),
        ('ESTADO_RESULTADOS', 'Estado de resultados'),
        ('ESTADISTICAS', 'Estadísticas y gráficas'),
        ('ADMIN', 'Módulo administrativo'),
        ('DIRECTOR', 'Cabina director'),
        ('SOPORTE', 'Módulo de soporte'),
        ('OTRA', 'Otra área'),
    )

    COMPORTAMIENTOS = (
        ('NO_CARGA', 'No carga / se queda pensando'),
        ('ERROR_VISUAL', 'Error visual o de maquetación'),
        ('ERROR_VALIDACION', 'Mensaje de validación inesperado'),
        ('ERROR_PERMISOS', 'No tengo permisos en una acción esperada'),
        ('DATOS_INCORRECTOS', 'Datos incorrectos o incompletos'),
        ('CIERRE_SESION', 'Se cierra sesión inesperadamente'),
        ('OTRO', 'Otro comportamiento'),
    )

    PRIORIDADES = (
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    )

    DISPOSITIVOS = (
        ('ESCRITORIO', 'Equipo de escritorio'),
        ('LAPTOP', 'Laptop'),
        ('TABLET', 'Tablet'),
        ('MOVIL', 'Móvil'),
        ('NO_APLICA', 'No aplica'),
    )

    problema_principal = serializers.ChoiceField(choices=PROBLEMAS_PRINCIPALES, required=True)
    areas_afectadas = serializers.ListField(
        child=serializers.ChoiceField(choices=AREAS_AFECTADAS),
        allow_empty=False,
        required=True,
    )
    comportamiento_observado = serializers.ChoiceField(choices=COMPORTAMIENTOS, required=True)
    prioridad = serializers.ChoiceField(choices=PRIORIDADES, required=False, default='MEDIA')
    dispositivo = serializers.ChoiceField(choices=DISPOSITIVOS, required=False, default='ESCRITORIO')
    pagina_afectada = serializers.CharField(max_length=300, required=False, allow_blank=True)
    descripcion_detallada = serializers.CharField(min_length=20, max_length=4000, required=True)
    pasos_reproduccion = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    bloqueo_operativo = serializers.BooleanField(required=False, default=False)

    def validate_areas_afectadas(self, value):
        normalizadas = []
        vistos = set()
        for area in value:
            llave = str(area).strip().upper()
            if llave in vistos:
                continue
            vistos.add(llave)
            normalizadas.append(llave)
        if not normalizadas:
            raise serializers.ValidationError('Debes seleccionar al menos un área afectada.')
        return normalizadas


class TicketSoporteTecnicoAdminSerializer(serializers.ModelSerializer):
    """Serializador de consulta para tablero administrativo de tickets de soporte."""

    estado_seguimiento_label = serializers.CharField(source='get_estado_seguimiento_display', read_only=True)
    atendido_por_nombre = serializers.CharField(source='atendido_por.nombre', read_only=True)

    class Meta:
        model = TicketSoporteTecnico
        fields = (
            'id',
            'folio',
            'usuario',
            'usuario_nombre',
            'usuario_username',
            'usuario_correo',
            'usuario_sucursal',
            'usuario_roles',
            'problema_principal',
            'problema_principal_etiqueta',
            'areas_afectadas',
            'areas_afectadas_etiquetas',
            'comportamiento_observado',
            'comportamiento_observado_etiqueta',
            'prioridad',
            'prioridad_etiqueta',
            'dispositivo',
            'dispositivo_etiqueta',
            'pagina_afectada',
            'descripcion_detallada',
            'pasos_reproduccion',
            'bloqueo_operativo',
            'estado_seguimiento',
            'estado_seguimiento_label',
            'notas_seguimiento',
            'atendido_por',
            'atendido_por_nombre',
            'atendido_en',
            'resuelto_en',
            'correo_soporte_enviado',
            'correo_confirmacion_enviado',
            'detalle_error_envio',
            'creado_en',
            'actualizado_en',
        )
        read_only_fields = fields


class TicketSoporteTecnicoSeguimientoSerializer(serializers.Serializer):
    """Valida cambios de estado de seguimiento administrativo para tickets de soporte."""

    estado_seguimiento = serializers.ChoiceField(
        choices=TicketSoporteTecnico.EstadoSeguimiento.choices,
        required=True,
    )
    notas_seguimiento = serializers.CharField(required=False, allow_blank=True, max_length=5000)
