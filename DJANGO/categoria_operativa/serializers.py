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
    rubro_nombre = serializers.CharField(source='rubro_contable.nombre', read_only=True, allow_null=True)
    rubro_padre_nombre = serializers.SerializerMethodField(read_only=True)
    rubro_nombre_con_padre = serializers.SerializerMethodField(read_only=True)

    def get_rubro_padre_nombre(self, obj):
        rubro = getattr(obj, 'rubro_contable', None)
        padre = getattr(rubro, 'padre', None) if rubro else None
        return getattr(padre, 'nombre', None)

    def get_rubro_nombre_con_padre(self, obj):
        rubro = getattr(obj, 'rubro_contable', None)
        if not rubro:
            return None
        nombre_rubro = getattr(rubro, 'nombre', None) or 'SIN RUBRO'
        nombre_padre = getattr(getattr(rubro, 'padre', None), 'nombre', None) or 'SIN PADRE'
        return f"{nombre_rubro} - {nombre_padre}"

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
    rubro_nombre = serializers.CharField(source='rubro_contable.nombre', read_only=True, allow_null=True)
    rubro_padre_nombre = serializers.SerializerMethodField(read_only=True)
    rubro_nombre_con_padre = serializers.SerializerMethodField(read_only=True)

    def get_rubro_padre_nombre(self, obj):
        rubro = getattr(obj, 'rubro_contable', None)
        padre = getattr(rubro, 'padre', None) if rubro else None
        return getattr(padre, 'nombre', None)

    def get_rubro_nombre_con_padre(self, obj):
        rubro = getattr(obj, 'rubro_contable', None)
        if not rubro:
            return None
        nombre_rubro = getattr(rubro, 'nombre', None) or 'SIN RUBRO'
        nombre_padre = getattr(getattr(rubro, 'padre', None), 'nombre', None) or 'SIN PADRE'
        return f"{nombre_rubro} - {nombre_padre}"

    class Meta:
        model = Concepto
        fields = (
            'id',
            'categoria',
            'rubro_contable',
            'clave',
            'nombre',
            'tipo',
            'medio_liquidez',
            'descripcion',
            'es_recurrente',
            'requiere_imagen',
            'categoria_nombre',
            'rubro_nombre',
            'rubro_padre_nombre',
            'rubro_nombre_con_padre',
            'estado',
        )


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
        fields = ('id', 'clave', 'nombre', 'tipo', 'orden', 'usa_saldo_inicial', 'estado')
