import json

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.permisos import VentanaHorariaPermiso, EsAdministrador
from .models import ReporteDiario, MovimientoDiario
from .serializers import (
    ReporteDiarioSerializer, ReporteDiarioListSerializer,
    MovimientoDiarioSerializer, MovimientoDiarioListSerializer,
)


# 1) Para qué sirve: homologar la estructura JSON de salida de este módulo.
# 2) Cómo funciona: encapsula datos, mensaje, estado y código HTTP en un Response DRF.
# 3) Qué hace: evita respuestas inconsistentes entre endpoints del mismo ViewSet.
# 4) Cómo editarla: si cambia el contrato API global, ajusta este helper y propaga el mismo patrón.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: calcular el día contable oficial conforme a regla T-1 del negocio.
# 2) Cómo funciona: usa la zona horaria del servidor y resta un día a la fecha local.
# 3) Qué hace: devuelve la fecha que se usa para abrir/cerrar reportes y registrar movimientos.
# 4) Cómo editarla: si el negocio cambia la regla de día contable, modifica esta función central.
def _dia_contable_actual():
    """
    Retorna la fecha contable correcta: siempre el día anterior (T-1) a la fecha
    del servidor en la zona horaria configurada.
    El backend NO acepta la fecha del frontend; la calcula internamente.
    """
    return timezone.localdate() - timezone.timedelta(days=1)


# 1) Para qué sirve: obtener una tasa de cambio válida buscando varias claves configurables.
# 2) Cómo funciona: recorre una lista de claves y devuelve el primer valor tipado disponible.
# 3) Qué hace: abstrae fallback de configuración para USD/EUR u otras variantes.
# 4) Cómo editarla: agrega nuevas claves al arreglo de entrada sin tocar lógica de consumo.
def _obtener_tasa_cambio_por_claves(claves):
    from configuraciones_globales.models import ConfiguracionGlobal

    for clave in claves:
        configuracion = ConfiguracionGlobal.objects.filter(clave=clave).first()
        if not configuracion:
            continue
        valor = configuracion.valor_tipado
        if valor not in (None, ''):
            return valor
    return None


# 1) Para qué sirve: asegurar que cada sucursal tenga reporte diario para el día contable.
# 2) Cómo funciona: usa get_or_create con bloqueo transaccional y encadena saldos del reporte previo.
# 3) Qué hace: devuelve el reporte del día y un indicador de creación para flujo de API.
# 4) Cómo editarla: si cambian snapshots o reglas de arrastre, ajusta defaults y cálculo aquí.
def _obtener_o_crear_reporte_del_dia(sucursal_id):
    """
    Obtiene el ReporteDiario del día contable actual (T-1) para la sucursal dada.
    Si no existe, lo crea automáticamente, encadenando el saldo_arrastre_inicio
    desde el saldo_arrastre_fin del reporte anterior.
    """
    fecha = _dia_contable_actual()

    with transaction.atomic():
        reporte, creado = ReporteDiario.objects.select_for_update().get_or_create(
            sucursal_id=sucursal_id,
            fecha_contable=fecha,
            defaults={'estado_reporte': ReporteDiario.EstadoReporte.ABIERTO}
        )

        if creado:
            # Encadenar saldo de arrastre desde el día anterior
            anterior = ReporteDiario.objects.filter(
                sucursal_id=sucursal_id,
                fecha_contable__lt=fecha,
            ).order_by('-fecha_contable').first()

            if anterior:
                reporte.saldo_arrastre_inicio = anterior.saldo_arrastre_fin

            # Snapshot del tipo de cambio actual
            try:
                tasa_usd = _obtener_tasa_cambio_por_claves(['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD'])
                tasa_eur = _obtener_tasa_cambio_por_claves(['TIPO_CAMBIO_EUR'])
                if tasa_usd is not None:
                    reporte.tipo_cambio_usd_snapshot = tasa_usd
                if tasa_eur is not None:
                    reporte.tipo_cambio_eur_snapshot = tasa_eur
            except Exception:
                pass

            reporte.save()

    return reporte, creado


# 1) Para qué sirve: normalizar texto numérico capturado desde UI con coma/punto mixto.
# 2) Cómo funciona: detecta patrón decimal y transforma a formato interpretable por Decimal.
# 3) Qué hace: previene errores por separadores regionales en monto y monto_divisa.
# 4) Cómo editarla: añade nuevas reglas de parsing si se soportan otros formatos locales.
def _normalizar_texto_decimal(valor):
    if not isinstance(valor, str):
        return valor

    texto = valor.strip()
    if not texto:
        return texto

    if ',' in texto and '.' in texto:
        if texto.rfind(',') > texto.rfind('.'):
            return texto.replace('.', '').replace(',', '.')
        return texto.replace(',', '')

    if ',' in texto:
        return texto.replace('.', '').replace(',', '.')

    return texto


# 1) Para qué sirve: construir payload seguro para serializador de movimientos.
# 2) Cómo funciona: clona request.data, fuerza reporte_id del backend y normaliza campos numéricos/JSON.
# 3) Qué hace: elimina dependencia de datos sensibles enviados por frontend.
# 4) Cómo editarla: agrega aquí cualquier campo nuevo que requiera limpieza previa a validación.
def _construir_datos_movimiento(request, reporte_id):
    datos = request.data.copy()
    datos['reporte'] = reporte_id
    datos.pop('sucursal_id', None)

    if 'monto' in datos:
        datos['monto'] = _normalizar_texto_decimal(datos.get('monto'))
    if 'monto_divisa' in datos:
        datos['monto_divisa'] = _normalizar_texto_decimal(datos.get('monto_divisa'))

    detalles = datos.get('detalles_snapshot')
    if isinstance(detalles, str):
        try:
            detalles_parseados = json.loads(detalles)
        except json.JSONDecodeError:
            detalles_parseados = {}
        datos['detalles_snapshot'] = detalles_parseados if isinstance(detalles_parseados, dict) else {}

    return datos


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTE DIARIO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: exponer API de encabezado del día contable (reporte diario).
# 2) Cómo funciona: combina permisos, filtros, cierres y reaperturas sobre ReporteDiario.
# 3) Qué hace: gobierna ciclo de vida ABIERTO/CERRADO de cada jornada por sucursal.
# 4) Cómo editarla: agrega nuevas acciones de negocio como métodos @action en este ViewSet.
class ReporteDiarioViewSet(viewsets.ViewSet):
    """
    CRUD para ReporteDiario con acciones de cierre y reapertura.

    Permisos:
        - Lectura (GET): solo autenticación.
        - Escritura (POST/PATCH/DELETE): requiere estar DENTRO del horario de operación.
        - Reapertura: exclusivo para ADMINISTRADOR.
        - Cierre: puede ejecutarlo cualquier usuario autenticado (la validación
          de rol se delega a las reglas de negocio del frontend y a los roles).
    """

    def get_permissions(self):
        """Aplica VentanaHorariaPermiso solo a operaciones de escritura."""
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), VentanaHorariaPermiso()]
        if self.action == 'reabrir':
            return [IsAuthenticated(), EsAdministrador()]
        return [IsAuthenticated()]

    def list(self, request):
        qs = ReporteDiario.objects.all()
        sucursal_id = request.query_params.get('sucursal_id')
        anio = request.query_params.get('anio')
        mes = request.query_params.get('mes')
        dia = request.query_params.get('dia')

        if sucursal_id:
            qs = qs.filter(sucursal_id=sucursal_id)

        try:
            if anio not in (None, ''):
                qs = qs.filter(fecha_contable__year=int(anio))
            if mes not in (None, ''):
                mes_valor = int(mes)
                if mes_valor < 1 or mes_valor > 12:
                    raise ValueError('mes fuera de rango')
                qs = qs.filter(fecha_contable__month=mes_valor)
            if dia not in (None, ''):
                dia_valor = int(dia)
                if dia_valor < 1 or dia_valor > 31:
                    raise ValueError('dia fuera de rango')
                qs = qs.filter(fecha_contable__day=dia_valor)
        except ValueError:
            return respuesta_estandar(
                mensaje="Los parámetros 'anio', 'mes' y 'dia' deben ser enteros válidos.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        return respuesta_estandar(data=ReporteDiarioListSerializer(qs, many=True, context={'request': request}).data, mensaje="Reportes diarios obtenidos.")

    @action(detail=False, methods=['get'], url_path='actual')
    def actual(self, request):
        """
        Obtiene (o crea) el reporte del día contable actual (T-1) para la sucursal indicada.
        """
        sucursal_id = request.query_params.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El parámetro 'sucursal_id' es obligatorio.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )
        reporte, creado = _obtener_o_crear_reporte_del_dia(sucursal_id)
        return respuesta_estandar(
            data=ReporteDiarioSerializer(reporte, context={'request': request}).data,
            mensaje="Reporte del día contable creado automáticamente." if creado else "Reporte del día contable obtenido."
        )

    def create(self, request):
        """Crea un ReporteDiario para una sucursal. La fecha contable es asignada automáticamente (T-1)."""
        sucursal_id = request.data.get('sucursal')
        if not sucursal_id:
            return respuesta_estandar(mensaje="El campo 'sucursal' es obligatorio.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        reporte, creado = _obtener_o_crear_reporte_del_dia(sucursal_id)
        mensaje = "Reporte diario creado automáticamente." if creado else "Ya existe un reporte para el día contable actual."
        codigo = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
        return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje=mensaje, codigo=codigo)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ReporteDiario, pk=pk)
        return respuesta_estandar(data=ReporteDiarioSerializer(obj, context={'request': request}).data, mensaje="Reporte diario obtenido.")

    def partial_update(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El reporte está cerrado. Use el flujo de reapertura si es necesario.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = ReporteDiarioSerializer(reporte, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje="Reporte actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="No se puede eliminar un reporte cerrado.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        reporte.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje="Reporte diario eliminado (baja lógica).")

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """
        Cierre manual del día contable.
        Usa transaction.atomic + select_for_update para evitar condiciones de carrera.
        El cierre automático lo ejecuta la tarea Celery `cerrar_dia_contable`.
        """
        with transaction.atomic():
            reporte = ReporteDiario.todos.select_for_update().get(pk=pk)
            if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
                return respuesta_estandar(mensaje="El reporte ya está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

            from django.db.models import Sum
            movimientos = reporte.movimientos.filter(eliminado_en__isnull=True)
            ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
            egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
            neto = ingresos - egresos

            # Snapshot del tipo de cambio al momento del cierre
            try:
                tasa_usd = _obtener_tasa_cambio_por_claves(['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD'])
                tasa_eur = _obtener_tasa_cambio_por_claves(['TIPO_CAMBIO_EUR'])
                if tasa_usd is not None:
                    reporte.tipo_cambio_usd_snapshot = tasa_usd
                if tasa_eur is not None:
                    reporte.tipo_cambio_eur_snapshot = tasa_eur
            except Exception:
                pass

            reporte.total_ingresos     = ingresos
            reporte.total_egresos      = egresos
            reporte.resultado_neto     = neto
            reporte.saldo_arrastre_fin = reporte.saldo_arrastre_inicio + neto
            reporte.estado_reporte     = ReporteDiario.EstadoReporte.CERRADO
            reporte.cerrado_en         = timezone.now()
            reporte.cerrado_por        = request.user
            reporte.save()

        return respuesta_estandar(data=ReporteDiarioSerializer(reporte, context={'request': request}).data, mensaje=f"Reporte del día {reporte.fecha_contable} cerrado correctamente.")

    @action(detail=True, methods=['post'], url_path='reabrir')
    def reabrir(self, request, pk=None):
        """
        Reabre un reporte cerrado. EXCLUSIVO para ADMINISTRADOR.
        Deja rastro en el historial de simple_history (quién y cuándo reabrió).
        Tras la reapertura, el día puede ser modificado nuevamente si el horario lo permite.
        """
        with transaction.atomic():
            reporte = ReporteDiario.todos.select_for_update().get(pk=pk)
            if reporte.estado_reporte != ReporteDiario.EstadoReporte.CERRADO:
                return respuesta_estandar(mensaje="El reporte no está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

            reporte.estado_reporte = ReporteDiario.EstadoReporte.ABIERTO
            reporte.cerrado_en     = None
            reporte.cerrado_por    = None
            # El motivo de reapertura queda en el history con el usuario autenticado
            reporte._history_user  = request.user
            reporte.save()

        return respuesta_estandar(
            data=ReporteDiarioSerializer(reporte, context={'request': request}).data,
            mensaje=f"Reporte del día {reporte.fecha_contable} reabierto por {request.user.username}. Queda registrado en el historial."
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MOVIMIENTO DIARIO
# ─────────────────────────────────────────────────────────────────────────────

# 1) Para qué sirve: exponer API de líneas de captura operativa del día.
# 2) Cómo funciona: vincula concepto+sucursal al reporte T-1 y aplica restricciones de cierre/horario.
# 3) Qué hace: crea, actualiza, lista y elimina movimientos con validación de estado contable.
# 4) Cómo editarla: integra nuevas reglas de captura en create/captura_rapida antes del serializer.
class MovimientoDiarioViewSet(viewsets.ViewSet):
    """
    CRUD de movimientos diarios.

    Regla crítica de T-1: El backend IGNORA cualquier `reporte` o `fecha_contable`
    enviada por el frontend. El reporte se asigna automáticamente por el backend
    según la sucursal del movimiento y el día contable actual (T-1).

    Soporta filtrado por ?reporte_id= y ?categoria_id=
    """

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), VentanaHorariaPermiso()]
        return [IsAuthenticated()]

    def list(self, request):
        qs = MovimientoDiario.objects.all()
        if reporte_id := request.query_params.get('reporte_id'):
            qs = qs.filter(reporte_id=reporte_id)
        if categoria_id := request.query_params.get('categoria_id'):
            qs = qs.filter(concepto__categoria_id=categoria_id)
        return respuesta_estandar(data=MovimientoDiarioListSerializer(qs, many=True, context={'request': request}).data, mensaje="Movimientos obtenidos.")

    def create(self, request):
        """
        Registra un movimiento. El backend calcula automáticamente el ReporteDiario (T-1).
        El frontend DEBE enviar: concepto, monto, sucursal_id (y opcionalmente: monto_divisa, tipo_divisa, detalles_snapshot, notas).
        El campo 'reporte' que envíe el frontend es IGNORADO.
        """
        sucursal_id = request.data.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(mensaje="El campo 'sucursal_id' es obligatorio.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id)

        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día contable ya fue cerrado. No se pueden agregar movimientos.",
                estado="error", codigo=status.HTTP_403_FORBIDDEN
            )

        # Construir datos ignorando el 'reporte' del frontend y forzando el calculado
        datos = _construir_datos_movimiento(request, reporte.pk)

        s = MovimientoDiarioSerializer(data=datos)
        if s.is_valid():
            mov = s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento registrado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al registrar movimiento.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='captura-rapida')
    def captura_rapida(self, request):
        """
        Crea o actualiza automáticamente el movimiento del día contable para un concepto.
        Se usa para capturas por tabla con autoguardado en frontend.
        """
        sucursal_id = request.data.get('sucursal_id')
        concepto_id = request.data.get('concepto')

        if not sucursal_id or not concepto_id:
            return respuesta_estandar(
                mensaje="Los campos 'sucursal_id' y 'concepto' son obligatorios.",
                estado="error",
                codigo=status.HTTP_400_BAD_REQUEST
            )

        reporte, _ = _obtener_o_crear_reporte_del_dia(sucursal_id)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día contable ya fue cerrado. No se pueden registrar cambios.",
                estado="error",
                codigo=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            movimiento_existente = MovimientoDiario.objects.filter(
                reporte_id=reporte.id,
                concepto_id=concepto_id
            ).first()

            datos = _construir_datos_movimiento(request, reporte.id)

            if movimiento_existente:
                serializador = MovimientoDiarioSerializer(movimiento_existente, data=datos, partial=True)
            else:
                serializador = MovimientoDiarioSerializer(data=datos)

            if not serializador.is_valid():
                return respuesta_estandar(
                    data=serializador.errors,
                    mensaje="Error al guardar captura rápida.",
                    estado="error",
                    codigo=status.HTTP_400_BAD_REQUEST
                )

            movimiento = serializador.save()

        mensaje = "Movimiento actualizado en captura rápida." if movimiento_existente else "Movimiento creado en captura rápida."
        return respuesta_estandar(
            data=MovimientoDiarioSerializer(movimiento, context={'request': request}).data,
            mensaje=mensaje,
            codigo=status.HTTP_200_OK if movimiento_existente else status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=MovimientoDiarioSerializer(get_object_or_404(MovimientoDiario, pk=pk), context={'request': request}).data, mensaje="Movimiento obtenido.")

    def update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El día está cerrado. Edite dejando rastro en el historial mediante una reapertura.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = MovimientoDiarioSerializer(mov, data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El día está cerrado.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = MovimientoDiarioSerializer(mov, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=MovimientoDiarioSerializer(mov, context={'request': request}).data, mensaje="Movimiento actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        if mov.reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="El día está cerrado. Para anular un movimiento contable use el flujo de contrapartida.",
                estado="error", codigo=status.HTTP_403_FORBIDDEN
            )
        mov.eliminar_logico(usuario=request.user)
        return respuesta_estandar(mensaje="Movimiento eliminado (baja lógica).")


