from rest_framework import serializers
from .models import FondoFijo


class FondoFijoSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo FondoFijo."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)

    class Meta:
        model = FondoFijo
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )
