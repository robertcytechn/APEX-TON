from rest_framework import serializers
from .models import ReporteDiario, MovimientoDiario


class MovimientoDiarioSerializer(serializers.ModelSerializer):
    """Serializador completo para MovimientoDiario."""
    concepto_nombre = serializers.CharField(source='concepto.nombre', read_only=True)
    concepto_tipo   = serializers.CharField(source='concepto.tipo', read_only=True)
    categoria_nombre = serializers.CharField(source='concepto.categoria.nombre', read_only=True)

    class Meta:
        model = MovimientoDiario
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )


class MovimientoDiarioListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listado de movimientos."""
    concepto_nombre  = serializers.CharField(source='concepto.nombre', read_only=True)
    categoria_nombre = serializers.CharField(source='concepto.categoria.nombre', read_only=True)
    tipo = serializers.CharField(source='concepto.tipo', read_only=True)

    class Meta:
        model = MovimientoDiario
        fields = (
            'id',
            'concepto',
            'concepto_nombre',
            'categoria_nombre',
            'tipo',
            'monto',
            'monto_divisa',
            'tipo_divisa',
            'detalles_snapshot',
            'notas',
            'creado_en',
            'actualizado_en',
        )


class ReporteDiarioSerializer(serializers.ModelSerializer):
    """Serializador completo para ReporteDiario, incluye movimientos anidados."""
    movimientos   = MovimientoDiarioListSerializer(many=True, read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)

    class Meta:
        model = ReporteDiario
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
            'total_ingresos', 'total_egresos', 'resultado_neto',
            'cerrado_en', 'cerrado_por',
        )


class ReporteDiarioListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listado de reportes."""
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)

    class Meta:
        model = ReporteDiario
        fields = (
            'id', 'sucursal', 'sucursal_nombre', 'fecha_contable',
            'estado_reporte', 'saldo_arrastre_inicio', 'saldo_arrastre_fin',
            'total_ingresos', 'total_egresos', 'resultado_neto',
        )
