from rest_framework import serializers
from .models import Rol, Permiso, RolPermiso, Usuario, UsuarioRol


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
