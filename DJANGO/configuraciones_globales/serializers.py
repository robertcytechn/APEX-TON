from rest_framework import serializers
from .models import ConfiguracionGlobal, PadreRubroContable, RubroContable


class ConfiguracionGlobalSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo ConfiguracionGlobal."""
    valor_tipado = serializers.ReadOnlyField(
        help_text="Valor del campo 'valor' convertido al tipo de dato indicado en 'tipo_valor'."
    )

    class Meta:
        model = ConfiguracionGlobal
        fields = '__all__'
        read_only_fields = ('creado_en', 'actualizado_en', 'eliminado_en',
                            'creado_por', 'actualizado_por', 'eliminado_por',
                            'valor_anterior', 'valor_actual')


class ConfiguracionGlobalPublicaSerializer(serializers.ModelSerializer):
    """Serializador acotado para lectura publica del estado operativo."""

    class Meta:
        model = ConfiguracionGlobal
        fields = ('id', 'clave', 'valor', 'tipo_valor', 'descripcion')


class PadreRubroContableSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo PadreRubroContable."""

    class Meta:
        model = PadreRubroContable
        fields = '__all__'
        read_only_fields = ('creado_en', 'actualizado_en', 'eliminado_en',
                            'creado_por', 'actualizado_por', 'eliminado_por',
                            'valor_anterior', 'valor_actual')

    def validate_clave(self, value):
        clave_limpia = (value or '').strip().upper().replace(' ', '_')
        if not clave_limpia:
            raise serializers.ValidationError('La clave del padre es obligatoria.')

        queryset = PadreRubroContable.objects.filter(clave__iexact=clave_limpia)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Ya existe un padre de rubro con esta clave.')

        return clave_limpia

    def validate_nombre(self, value):
        nombre_limpio = (value or '').strip()
        if not nombre_limpio:
            raise serializers.ValidationError('El nombre del padre es obligatorio.')

        queryset = PadreRubroContable.objects.filter(nombre__iexact=nombre_limpio)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('Ya existe un padre de rubro con este nombre.')

        return nombre_limpio


class RubroContableSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo RubroContable."""
    padre = serializers.PrimaryKeyRelatedField(queryset=PadreRubroContable.objects.all(), required=False)
    padre_clave = serializers.CharField(write_only=True, required=False, allow_blank=False)
    padre_info = PadreRubroContableSerializer(source='padre', read_only=True)

    class Meta:
        model = RubroContable
        fields = '__all__'
        read_only_fields = ('creado_en', 'actualizado_en', 'eliminado_en',
                            'creado_por', 'actualizado_por', 'eliminado_por',
                            'valor_anterior', 'valor_actual')

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

        if attrs.get('padre') is None and self.instance is None:
            raise serializers.ValidationError({'padre': 'El padre del rubro es obligatorio.'})

        nombre = attrs.get('nombre', getattr(self.instance, 'nombre', None))
        padre = attrs.get('padre', getattr(self.instance, 'padre', None))

        if nombre and padre:
            queryset = RubroContable.objects.filter(nombre__iexact=nombre.strip(), padre=padre)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    'nombre': 'Ya existe un rubro con este nombre para el padre seleccionado.'
                })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['padre_clave'] = instance.padre.clave if instance.padre else None
        data['padre_nombre'] = instance.padre.nombre if instance.padre else None
        return data
