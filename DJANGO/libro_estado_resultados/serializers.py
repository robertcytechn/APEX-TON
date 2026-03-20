from rest_framework import serializers
from .models import LibroEstadoResultados


class LibroEstadoResultadosSerializer(serializers.ModelSerializer):
    """Serializador completo para LibroEstadoResultados."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)

    class Meta:
        model = LibroEstadoResultados
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
            'total_ingresos', 'total_egresos', 'resultado_neto',
            'saldo_arrastre_fin', 'desglose_por_rubro',
            'cerrado_en', 'cerrado_por',
        )


class LibroEstadoResultadosListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listado de libros."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)

    class Meta:
        model = LibroEstadoResultados
        fields = (
            'id', 'sucursal', 'sucursal_nombre', 'anio', 'mes',
            'estado_mes', 'total_ingresos', 'total_egresos', 'resultado_neto',
            'saldo_arrastre_inicio', 'saldo_arrastre_fin',
        )
