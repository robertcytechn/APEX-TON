from rest_framework import serializers

from configuraciones_globales.models import ConfiguracionGlobal, RubroContable
from sucursales.models import Sucursal
from usuarios.models import Rol, Usuario, UsuarioRol


class RolCabinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class UsuarioCabinaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, help_text='Contrasena para acceso del usuario.')
    roles_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        help_text='IDs de roles a asignar al usuario.'
    )
    roles = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            'id', 'username', 'nombre', 'correo', 'sucursal',
            'is_active', 'is_staff', 'password', 'roles_ids', 'roles', 'creado_en', 'actualizado_en'
        )
        read_only_fields = ('creado_en', 'actualizado_en')

    def get_roles(self, obj):
        return [
            {
                'id': usuario_rol.rol_id,
                'nombre': usuario_rol.rol.nombre,
            }
            for usuario_rol in obj.usuario_roles.select_related('rol').all()
        ]

    def validate_roles_ids(self, value):
        roles_unicos = list(dict.fromkeys(value or []))
        total_existentes = Rol.objects.filter(id__in=roles_unicos).count()
        if total_existentes != len(roles_unicos):
            raise serializers.ValidationError('Uno o mas roles no existen.')
        return roles_unicos

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and not attrs.get('roles_ids'):
            raise serializers.ValidationError({'roles_ids': ['Debes asignar al menos un rol.']})
        return attrs

    def _sincronizar_roles(self, usuario, roles_ids):
        if roles_ids is None:
            return

        UsuarioRol.objects.filter(usuario=usuario).exclude(rol_id__in=roles_ids).delete()
        roles_actuales = set(UsuarioRol.objects.filter(usuario=usuario).values_list('rol_id', flat=True))

        for rol_id in roles_ids:
            if rol_id in roles_actuales:
                continue
            UsuarioRol.objects.create(usuario=usuario, rol_id=rol_id)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        roles_ids = validated_data.pop('roles_ids', None)
        usuario = Usuario(**validated_data)
        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()
        usuario.save()
        self._sincronizar_roles(usuario, roles_ids)
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        roles_ids = validated_data.pop('roles_ids', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        self._sincronizar_roles(instance, roles_ids)
        return instance


class SucursalCabinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'
        read_only_fields = (
            'fondos_fijos',
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class ConfiguracionGlobalCabinaSerializer(serializers.ModelSerializer):
    valor_tipado = serializers.ReadOnlyField()

    class Meta:
        model = ConfiguracionGlobal
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class RubroContableCabinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubroContable
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )
