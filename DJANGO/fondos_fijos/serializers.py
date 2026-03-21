from rest_framework import serializers
from .models import FondoFijo, SucursalFondoFijo


class FondoFijoSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo FondoFijo."""

    class Meta:
        model = FondoFijo
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class SucursalFondoFijoSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo pivote SucursalFondoFijo."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    fondo_fijo_nombre = serializers.CharField(source='fondo_fijo.nombre', read_only=True)

    class Meta:
        model = SucursalFondoFijo
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )
