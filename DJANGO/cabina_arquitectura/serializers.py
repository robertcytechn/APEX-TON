from rest_framework import serializers

from configuraciones_globales.models import ConfiguracionGlobal, PadreRubroContable, RubroContable
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


class PadreRubroContableCabinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PadreRubroContable
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )

    def validate_clave(self, value):
        clave_limpia = (value or '').strip().upper().replace(' ', '_')
        if not clave_limpia:
            raise serializers.ValidationError('La clave del padre es obligatoria.')

        queryset = PadreRubroContable.objects.filter(clave__iexact=clave_limpia)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Ya existe un padre con esta clave.')

        return clave_limpia

    def validate_nombre(self, value):
        nombre_limpio = (value or '').strip()
        if not nombre_limpio:
            raise serializers.ValidationError('El nombre del padre es obligatorio.')

        queryset = PadreRubroContable.objects.filter(nombre__iexact=nombre_limpio)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Ya existe un padre con este nombre.')

        return nombre_limpio


class RubroContableCabinaSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(trim_whitespace=True)
    padre = serializers.PrimaryKeyRelatedField(queryset=PadreRubroContable.objects.all(), required=False)
    padre_clave = serializers.CharField(write_only=True, required=False, allow_blank=False)
    padre_info = PadreRubroContableCabinaSerializer(source='padre', read_only=True)

    class Meta:
        model = RubroContable
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )

    def validate_nombre(self, value):
        nombre_limpio = (value or '').strip()
        if not nombre_limpio:
            raise serializers.ValidationError('El nombre del rubro es obligatorio.')

        queryset = RubroContable.objects.filter(nombre__iexact=nombre_limpio)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Ya existe un rubro contable con este nombre.')

        return nombre_limpio

    def validate(self, attrs):
        padre_id = attrs.get('padre')
        padre_clave = self.initial_data.get('padre_clave')

        if padre_id is None and padre_clave:
            clave_limpia = str(padre_clave).strip().upper()
            padre = PadreRubroContable.objects.filter(clave=clave_limpia).first()
            if padre is None:
                raise serializers.ValidationError({'padre_clave': 'No existe un padre de rubro con esta clave.'})
            attrs['padre'] = padre

        if attrs.get('padre') is None and self.instance is None:
            raise serializers.ValidationError({'padre': 'El padre del rubro es obligatorio.'})

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['padre_clave'] = instance.padre.clave if instance.padre else None
        data['padre_nombre'] = instance.padre.nombre if instance.padre else None
        return data
