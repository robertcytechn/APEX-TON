from rest_framework import serializers
from .models import ConfiguracionGlobal, RubroContable


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


class RubroContableSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo RubroContable."""

    class Meta:
        model = RubroContable
        fields = '__all__'
        read_only_fields = ('creado_en', 'actualizado_en', 'eliminado_en',
                            'creado_por', 'actualizado_por', 'eliminado_por',
                            'valor_anterior', 'valor_actual')
