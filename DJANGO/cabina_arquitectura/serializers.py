from decimal import Decimal
import secrets

from django.db import transaction
from rest_framework import serializers

from configuraciones_globales.models import ConfiguracionGlobal, PadreRubroContable, RubroContable
from fondos_fijos.models import FondoFijo, SucursalFondoFijo
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


class FondoAsignadoDirectorEntradaSerializer(serializers.Serializer):
    fondo_fijo = serializers.PrimaryKeyRelatedField(
        queryset=FondoFijo.objects.all(),
        help_text='Identificador del fondo fijo del catálogo maestro.'
    )
    monto_asignado = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal('0.00'),
        help_text='Monto inicial asignado al fondo fijo para la sucursal.'
    )


class SucursalDirectorCabinaSerializer(serializers.ModelSerializer):
    fondos_asignados = FondoAsignadoDirectorEntradaSerializer(
        many=True,
        required=False,
        write_only=True,
        help_text='Listado de montos por fondo fijo para la sucursal nueva.'
    )
    fondos_asignados_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Sucursal
        fields = (
            'id', 'nombre', 'clave', 'direccion', 'ciudad', 'estado_republica',
            'telefono', 'correo', 'encargado', 'fondo_inicial',
            'fondos_asignados', 'fondos_asignados_detalle',
            'creado_en', 'actualizado_en'
        )
        read_only_fields = ('creado_en', 'actualizado_en', 'fondos_asignados_detalle')

    def validate_fondos_asignados(self, value):
        ids_fondos = [item['fondo_fijo'].id for item in (value or [])]
        if len(ids_fondos) != len(set(ids_fondos)):
            raise serializers.ValidationError('No puedes repetir fondos fijos en la misma sucursal.')
        return value

    def get_fondos_asignados_detalle(self, obj):
        asignaciones = obj.asignaciones_fondos_fijos.select_related('fondo_fijo').all().order_by('fondo_fijo__nombre')
        return [
            {
                'id': asignacion.id,
                'fondo_fijo': asignacion.fondo_fijo_id,
                'fondo_fijo_nombre': asignacion.fondo_fijo.nombre,
                'monto_asignado': asignacion.monto_asignado,
            }
            for asignacion in asignaciones
        ]

    def create(self, validated_data):
        fondos_asignados = validated_data.pop('fondos_asignados', [])
        request = self.context.get('request')
        usuario = request.user if request and request.user.is_authenticated else None

        montos_por_fondo = {
            item['fondo_fijo'].id: item['monto_asignado']
            for item in fondos_asignados
        }

        with transaction.atomic():
            sucursal = Sucursal.objects.create(
                **validated_data,
                creado_por=usuario,
            )

            for fondo in FondoFijo.objects.all().order_by('nombre'):
                SucursalFondoFijo.objects.create(
                    sucursal=sucursal,
                    fondo_fijo=fondo,
                    monto_asignado=montos_por_fondo.get(fondo.id, Decimal('0.00')),
                    creado_por=usuario,
                )

        return sucursal


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


class ConfiguracionGlobalDirectorCabinaSerializer(serializers.ModelSerializer):
    valor_tipado = serializers.ReadOnlyField()

    class Meta:
        model = ConfiguracionGlobal
        fields = (
            'id',
            'clave',
            'valor',
            'tipo_valor',
            'descripcion',
            'valor_tipado',
            'actualizado_en',
        )
        read_only_fields = ('clave', 'tipo_valor', 'descripcion', 'valor_tipado', 'actualizado_en')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None:
            raise serializers.ValidationError('No tienes permiso para crear nuevas variables globales.')

        errores = {}
        for campo in ('clave', 'tipo_valor', 'descripcion'):
            if campo not in self.initial_data:
                continue
            valor_enviado = self.initial_data.get(campo)
            valor_actual = getattr(self.instance, campo, None)
            if str(valor_enviado) != str(valor_actual):
                errores[campo] = ['Solo puedes modificar el valor de la variable global.']

        if errores:
            raise serializers.ValidationError(errores)

        return attrs


class UsuarioDirectorCabinaSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField(required=True, allow_blank=False)
    sucursal = serializers.PrimaryKeyRelatedField(queryset=Sucursal.objects.all(), required=True, allow_null=False)
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), write_only=True, required=False)
    rol_info = serializers.SerializerMethodField(read_only=True)
    contrasena_generada = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            'id', 'username', 'nombre', 'correo',
            'sucursal', 'sucursal_nombre',
            'rol', 'rol_info',
            'is_active', 'requiere_cambio_password', 'contrasena_generada',
            'creado_en', 'actualizado_en'
        )
        read_only_fields = ('creado_en', 'actualizado_en', 'contrasena_generada', 'rol_info', 'sucursal_nombre', 'requiere_cambio_password')

    @staticmethod
    def _normalizar_nombre_rol(nombre_rol):
        return str(nombre_rol or '').strip().upper()

    def get_rol_info(self, obj):
        asignacion = obj.usuario_roles.select_related('rol').first()
        if not asignacion:
            return None
        return {
            'id': asignacion.rol_id,
            'nombre': asignacion.rol.nombre,
        }

    def get_contrasena_generada(self, obj):
        return self.context.get('contrasena_generada')

    def validate_rol(self, value):
        nombre_rol = self._normalizar_nombre_rol(value.nombre)
        if nombre_rol not in {'CONTADOR', 'GERENTE'}:
            raise serializers.ValidationError('Solo puedes crear usuarios con rol CONTADOR o GERENTE.')
        return value

    @staticmethod
    def generar_contrasena_numerica():
        return ''.join(secrets.choice('0123456789') for _ in range(8))

    def validate(self, attrs):
        attrs = super().validate(attrs)

        correo_final = attrs.get('correo', getattr(self.instance, 'correo', None))
        if not str(correo_final or '').strip():
            raise serializers.ValidationError({'correo': ['El correo electronico es obligatorio.']})

        queryset_correo = Usuario.objects.filter(correo__iexact=str(correo_final).strip())
        if self.instance is not None:
            queryset_correo = queryset_correo.exclude(pk=self.instance.pk)
        if queryset_correo.exists():
            raise serializers.ValidationError({'correo': ['Ya existe otro usuario con este correo electronico.']})

        sucursal_final = attrs.get('sucursal', getattr(self.instance, 'sucursal', None))
        if not sucursal_final:
            raise serializers.ValidationError({'sucursal': ['Debes asignar el usuario a un casino.']})

        if self.instance is None and attrs.get('rol') is None:
            raise serializers.ValidationError({'rol': ['Debes seleccionar un rol operativo para crear el usuario.']})

        return attrs

    def _asignar_rol_unico(self, usuario, rol):
        if rol is None:
            return

        UsuarioRol.objects.filter(usuario=usuario).delete()
        UsuarioRol.objects.create(usuario=usuario, rol=rol)

    def create(self, validated_data):
        rol = validated_data.pop('rol', None)
        contrasena_generada = self.generar_contrasena_numerica()
        request = self.context.get('request')

        usuario = Usuario(**validated_data)
        usuario.is_active = True
        usuario.is_staff = False
        usuario.requiere_cambio_password = True
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            usuario.creado_por = request.user
            usuario.actualizado_por = request.user
        usuario.set_password(contrasena_generada)
        usuario.save()

        self._asignar_rol_unico(usuario, rol)

        self._contrasena_generada = contrasena_generada
        return usuario

    def update(self, instance, validated_data):
        rol = validated_data.pop('rol', None)
        request = self.context.get('request')

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            instance.actualizado_por = request.user
        instance.save()

        if rol is not None:
            self._asignar_rol_unico(instance, rol)

        return instance


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

        padre = attrs.get('padre', getattr(self.instance, 'padre', None))
        if padre is None:
            raise serializers.ValidationError({'padre': 'El padre del rubro es obligatorio.'})

        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None))
        if not tipo:
            raise serializers.ValidationError({'tipo': 'El tipo del rubro es obligatorio.'})

        nombre = attrs.get('nombre', getattr(self.instance, 'nombre', None))

        if nombre and padre:
            queryset = RubroContable.objects.filter(nombre__iexact=nombre.strip(), padre=padre)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    'nombre': 'Ya existe un rubro contable con este nombre para el padre seleccionado.'
                })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['padre_clave'] = instance.padre.clave if instance.padre else None
        data['padre_nombre'] = instance.padre.nombre if instance.padre else None
        return data
