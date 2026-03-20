from rest_framework import serializers
from .models import CategoriaOperativa, Concepto, DetalleParametrizado


class DetalleParametrizadoSerializer(serializers.ModelSerializer):
    """Serializador completo para DetalleParametrizado."""

    class Meta:
        model = DetalleParametrizado
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class ConceptoSerializer(serializers.ModelSerializer):
    """Serializador completo para Concepto."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    rubro_nombre = serializers.CharField(source='rubro_contable.nombre', read_only=True)

    class Meta:
        model = Concepto
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class ConceptoListSerializer(serializers.ModelSerializer):
    """Serializador reducido de Concepto para listados."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    rubro_nombre = serializers.CharField(source='rubro_contable.nombre', read_only=True)

    class Meta:
        model = Concepto
        fields = ('id', 'clave', 'nombre', 'tipo', 'categoria_nombre', 'rubro_nombre', 'estado')


class CategoriaOperativaSerializer(serializers.ModelSerializer):
    """Serializador completo para CategoriaOperativa, con sus detalles anidados."""
    detalles_parametrizados = DetalleParametrizadoSerializer(many=True, read_only=True)
    conceptos = ConceptoListSerializer(many=True, read_only=True)

    class Meta:
        model = CategoriaOperativa
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class CategoriaOperativaListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listado de categorías."""

    class Meta:
        model = CategoriaOperativa
        fields = ('id', 'clave', 'nombre', 'tipo', 'orden', 'estado')
