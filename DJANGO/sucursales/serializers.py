from rest_framework import serializers
from .models import Sucursal


class SucursalSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo Sucursal."""

    class Meta:
        model = Sucursal
        fields = '__all__'
        read_only_fields = (
            'fondos_fijos',
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class SucursalListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listados (solo campos esenciales)."""

    class Meta:
        model = Sucursal
        fields = ('id', 'clave', 'nombre', 'ciudad', 'estado_republica', 'encargado', 'estado')
