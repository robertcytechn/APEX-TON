from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from configuraciones_globales.models import ConfiguracionGlobal
from .models import ReporteDiario, MovimientoDiario


# 1) Para qué sirve: serializar registros del historial de movimientos con contexto completo.
# 2) Cómo funciona: expone campos del historial y enriquece con datos relacionados (usuario, concepto, sucursal).
# 3) Qué hace: permite auditar cambios con diff visual y filtros por entidades relacionadas.
# 4) Cómo editarla: agrega campos adicionales de history_user o metadatos si evoluciona la auditoría.
class MovimientoDiarioHistorialSerializer(serializers.Serializer):
    """
    Serializador para registros de historial (django-simple-history) de MovimientoDiario.
    Proporciona contexto completo para auditoría: quién, cuándo, qué cambió.
    """
    history_id = serializers.IntegerField(source='id', read_only=True)
    history_date = serializers.DateTimeField(read_only=True)
    history_type = serializers.CharField(read_only=True)
    history_type_display = serializers.SerializerMethodField()
    history_change_reason = serializers.CharField(read_only=True, allow_null=True)

    # Datos del movimiento en este punto histórico
    movimiento_id = serializers.IntegerField(source='id', read_only=True)
    monto = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    monto_divisa = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True, allow_null=True)
    tipo_divisa = serializers.CharField(read_only=True, allow_null=True)
    detalles_snapshot = serializers.JSONField(read_only=True)
    notas = serializers.CharField(read_only=True, allow_null=True)

    # Metadatos temporales del registro histórico
    creado_en = serializers.DateTimeField(read_only=True)
    actualizado_en = serializers.DateTimeField(read_only=True)
    eliminado_en = serializers.DateTimeField(read_only=True, allow_null=True)

    # Relaciones
    reporte_id = serializers.IntegerField(source='reporte_id', read_only=True)
    fecha_contable = serializers.DateField(source='reporte.fecha_contable', read_only=True, allow_null=True)
    sucursal_id = serializers.IntegerField(source='reporte.sucursal_id', read_only=True, allow_null=True)
    sucursal_nombre = serializers.CharField(source='reporte.sucursal.nombre', read_only=True, allow_null=True)

    concepto_id = serializers.IntegerField(source='concepto_id', read_only=True)
    concepto_nombre = serializers.CharField(source='concepto.nombre', read_only=True, allow_null=True)
    concepto_clave = serializers.CharField(source='concepto.clave', read_only=True, allow_null=True)
    categoria_nombre = serializers.CharField(source='concepto.categoria.nombre', read_only=True, allow_null=True)
    categoria_id = serializers.IntegerField(source='concepto.categoria_id', read_only=True, allow_null=True)

    # Usuario que realizó el cambio
    usuario_id = serializers.IntegerField(source='history_user_id', read_only=True, allow_null=True)
    usuario_nombre = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()

    # Diff con versión anterior
    diff = serializers.SerializerMethodField()

    def get_history_type_display(self, obj):
        tipos = {
            '+': 'Creación',
            '~': 'Modificación',
            '-': 'Eliminación'
        }
        return tipos.get(obj.history_type, obj.history_type)

    def get_usuario_nombre(self, obj):
        if obj.history_user:
            return obj.history_user.get_full_name() or obj.history_user.username
        return 'Sistema'

    def get_usuario_email(self, obj):
        if obj.history_user:
            return obj.history_user.email
        return None

    def get_diff(self, obj):
        """
        Calcula diferencias entre esta versión y la anterior.
        Retorna un dict con campos cambiados, valores anterior y nuevo.
        """
        if obj.history_type == '+':
            return {'tipo': 'creacion', 'cambios': None}

        if obj.history_type == '-':
            return {'tipo': 'eliminacion', 'cambios': None}

        # Buscar versión anterior
        version_anterior = obj.prev_record
        if not version_anterior:
            return {'tipo': 'modificacion', 'cambios': None, 'nota': 'Versión anterior no disponible'}

        campos_a_comparar = [
            'monto', 'monto_divisa', 'tipo_divisa', 'detalles_snapshot', 'notas'
        ]

        cambios = []
        for campo in campos_a_comparar:
            valor_anterior = getattr(version_anterior, campo, None)
            valor_nuevo = getattr(obj, campo, None)

            # Normalizar para comparación
            if valor_anterior == '' or valor_anterior == {}:
                valor_anterior = None
            if valor_nuevo == '' or valor_nuevo == {}:
                valor_nuevo = None

            if valor_anterior != valor_nuevo:
                cambios.append({
                    'campo': campo,
                    'valor_anterior': valor_anterior,
                    'valor_nuevo': valor_nuevo,
                    'etiqueta': self._etiqueta_campo(campo)
                })

        return {
            'tipo': 'modificacion',
            'cambios': cambios,
            'cantidad_cambios': len(cambios)
        }

    def _etiqueta_campo(self, campo):
        etiquetas = {
            'monto': 'Monto (MXN)',
            'monto_divisa': 'Monto en Divisa',
            'tipo_divisa': 'Tipo de Divisa',
            'detalles_snapshot': 'Detalles Parametrizados',
            'notas': 'Notas'
        }
        return etiquetas.get(campo, campo.replace('_', ' ').title())


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
