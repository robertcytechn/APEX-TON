from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from configuraciones_globales.models import ConfiguracionGlobal
from .models import ReporteDiario, MovimientoDiario


# 1) Para qué sirve: detectar si un concepto pertenece a la categoría operativa DOLARES.
# 2) Cómo funciona: evalúa clave/nombre de categoría en mayúsculas para tolerar variantes.
# 3) Qué hace: habilita lógica de conversión automática USD->MXN en validación del serializer.
# 4) Cómo editarla: ajusta condiciones si se agregan claves equivalentes para categorías de divisa.
def _es_categoria_dolares(concepto):
    if not concepto or not getattr(concepto, 'categoria', None):
        return False

    clave = (getattr(concepto.categoria, 'clave', '') or '').strip().upper()
    nombre = (getattr(concepto.categoria, 'nombre', '') or '').strip().upper()
    return clave == 'DOLARES' or nombre == 'DOLARES'


# 1) Para qué sirve: resolver tipo de cambio USD vigente desde configuración global.
# 2) Cómo funciona: intenta claves prioritarias y convierte el valor a Decimal seguro.
# 3) Qué hace: entrega una tasa utilizable para calcular monto en MXN.
# 4) Cómo editarla: incorpora nuevas claves/fuentes de tasa en el arreglo `claves`.
def _obtener_tasa_cambio_dolares():
    # Prioriza la clave nueva solicitada por negocio y mantiene compatibilidad.
    claves = ['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD']
    for clave in claves:
        configuracion = ConfiguracionGlobal.objects.filter(clave=clave).first()
        if not configuracion:
            continue
        valor = configuracion.valor_tipado
        if valor in (None, ''):
            continue
        try:
            return Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            continue
    return None


# 1) Para qué sirve: validar y serializar el detalle completo de un movimiento diario.
# 2) Cómo funciona: incluye campos derivados y en validate aplica reglas especiales para DOLARES.
# 3) Qué hace: normaliza monto_divisa, tipo_divisa y monto convertido con tasa actual.
# 4) Cómo editarla: agrega nuevas validaciones en validate sin romper campos read_only.
class MovimientoDiarioSerializer(serializers.ModelSerializer):
    """Serializador completo para MovimientoDiario."""
    concepto_nombre = serializers.CharField(source='concepto.nombre', read_only=True)
    concepto_tipo   = serializers.CharField(source='concepto.tipo', read_only=True)
    categoria_nombre = serializers.CharField(source='concepto.categoria.nombre', read_only=True)
    archivo_respaldo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MovimientoDiario
        fields = '__all__'
        read_only_fields = (
            'creado_en', 'actualizado_en', 'eliminado_en',
            'creado_por', 'actualizado_por', 'eliminado_por',
            'valor_anterior', 'valor_actual',
        )

    def get_archivo_respaldo_url(self, obj):
        if not obj.archivo_respaldo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.archivo_respaldo.url)
        return obj.archivo_respaldo.url

    def validate(self, attrs):
        attrs = super().validate(attrs)

        concepto = attrs.get('concepto') or getattr(self.instance, 'concepto', None)
        if not _es_categoria_dolares(concepto):
            return attrs

        monto_capturado = attrs.get('monto')
        if monto_capturado is None and self.instance is not None:
            monto_capturado = self.instance.monto_divisa if self.instance.monto_divisa is not None else self.instance.monto

        try:
            monto_dolares = Decimal(str(monto_capturado if monto_capturado is not None else 0)).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            raise serializers.ValidationError({'monto': 'El monto en dólares no es válido.'})

        tasa_cambio_dolares = _obtener_tasa_cambio_dolares()
        if tasa_cambio_dolares is None or tasa_cambio_dolares <= 0:
            raise serializers.ValidationError({'monto': 'No existe una tasa válida en configuraciones globales para TASA_CAMBIO_DOLARES.'})

        attrs['monto_divisa'] = monto_dolares
        attrs['tipo_divisa'] = 'USD'
        attrs['monto'] = (monto_dolares * tasa_cambio_dolares).quantize(Decimal('0.01'))
        return attrs


# 1) Para qué sirve: representar movimientos en listados con payload ligero.
# 2) Cómo funciona: expone datos de concepto/categoría y URL de respaldo mediante método.
# 3) Qué hace: optimiza respuesta para tablas de captura y consulta.
# 4) Cómo editarla: agrega/quita columnas en Meta.fields según necesidades de UI.
class MovimientoDiarioListSerializer(serializers.ModelSerializer):
    """Serializador reducido para listado de movimientos."""
    concepto_nombre  = serializers.CharField(source='concepto.nombre', read_only=True)
    categoria_nombre = serializers.CharField(source='concepto.categoria.nombre', read_only=True)
    tipo = serializers.CharField(source='concepto.tipo', read_only=True)
    medio_liquidez = serializers.CharField(source='concepto.medio_liquidez', read_only=True)
    concepto_requiere_imagen = serializers.BooleanField(source='concepto.requiere_imagen', read_only=True)
    archivo_respaldo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MovimientoDiario
        fields = (
            'id',
            'concepto',
            'concepto_nombre',
            'categoria_nombre',
            'tipo',
            'medio_liquidez',
            'monto',
            'monto_divisa',
            'tipo_divisa',
            'detalles_snapshot',
            'notas',
            'archivo_respaldo',
            'archivo_respaldo_url',
            'concepto_requiere_imagen',
            'creado_en',
            'actualizado_en',
        )

    def get_archivo_respaldo_url(self, obj):
        if not obj.archivo_respaldo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.archivo_respaldo.url)
        return obj.archivo_respaldo.url


# 1) Para qué sirve: serializar un reporte diario completo junto con movimientos anidados.
# 2) Cómo funciona: combina campos del encabezado y relación `movimientos` en modo read-only.
# 3) Qué hace: entrega vista integral del día contable para detalle y cierre.
# 4) Cómo editarla: agrega campos calculados nuevos en serializers read_only si el reporte evoluciona.
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


# 1) Para qué sirve: exponer resumen de reportes diarios para listas y filtros.
# 2) Cómo funciona: incluye solo campos de cabecera y métricas principales.
# 3) Qué hace: reduce tamaño de respuesta en vistas de consulta masiva.
# 4) Cómo editarla: modifica Meta.fields si cambian columnas visibles en frontend.
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
