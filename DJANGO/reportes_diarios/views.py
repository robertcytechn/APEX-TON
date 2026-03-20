from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import ReporteDiario, MovimientoDiario
from .serializers import (
    ReporteDiarioSerializer, ReporteDiarioListSerializer,
    MovimientoDiarioSerializer, MovimientoDiarioListSerializer,
)


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


def _verificar_reporte_editable(reporte):
    """
    Valida que el reporte pueda ser modificado:
    1. Debe estar en estado ABIERTO.
    2. Debe estar dentro del horario permitido según HORARIO_APERTURA y HORARIO_CIERRE
       configurados en ConfiguracionGlobal.
    Retorna (True, None) si es editable, o (False, Response) si no lo es.
    """
    if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
        return False, respuesta_estandar(
            mensaje="El reporte ya está cerrado y no puede ser modificado.",
            estado="error",
            codigo=status.HTTP_403_FORBIDDEN
        )

    # Validación de horario usando ConfiguracionGlobal
    try:
        from configuraciones_globales.models import ConfiguracionGlobal
        hora_apertura = ConfiguracionGlobal.objects.get(clave='HORARIO_APERTURA').valor_tipado
        hora_cierre   = ConfiguracionGlobal.objects.get(clave='HORARIO_CIERRE').valor_tipado
        ahora = timezone.localtime(timezone.now()).time()
        if hora_apertura and hora_cierre:
            if not (hora_apertura <= ahora <= hora_cierre):
                return False, respuesta_estandar(
                    mensaje=f"Fuera del horario de operación ({hora_apertura} – {hora_cierre}). No se permiten modificaciones.",
                    estado="error",
                    codigo=status.HTTP_403_FORBIDDEN
                )
    except ConfiguracionGlobal.DoesNotExist:
        pass  # Si no están configurados los horarios, no se restringe

    return True, None


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTE DIARIO
# ─────────────────────────────────────────────────────────────────────────────

class ReporteDiarioViewSet(viewsets.ViewSet):
    """
    CRUD para ReporteDiario con acciones de cierre de día.
    Un reporte CERRADO no puede ser modificado.
    El endpoint `cerrar` calcula totales, guarda el snapshot de tipo de cambio
    y bloquea el registro permanentemente.
    """

    def list(self, request):
        qs = ReporteDiario.objects.all()
        sucursal_id = request.query_params.get('sucursal_id')
        if sucursal_id:
            qs = qs.filter(sucursal_id=sucursal_id)
        return respuesta_estandar(data=ReporteDiarioListSerializer(qs, many=True).data, mensaje="Reportes diarios obtenidos.")

    def create(self, request):
        s = ReporteDiarioSerializer(data=request.data)
        if s.is_valid():
            reporte = s.save()
            return respuesta_estandar(data=ReporteDiarioSerializer(reporte).data, mensaje="Reporte diario creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear reporte.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(ReporteDiario, pk=pk)
        return respuesta_estandar(data=ReporteDiarioSerializer(obj).data, mensaje="Reporte diario obtenido.")

    def update(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        editable, error_response = _verificar_reporte_editable(reporte)
        if not editable:
            return error_response
        s = ReporteDiarioSerializer(reporte, data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Reporte actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        editable, error_response = _verificar_reporte_editable(reporte)
        if not editable:
            return error_response
        s = ReporteDiarioSerializer(reporte, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Reporte actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(
                mensaje="No se puede eliminar un reporte cerrado.",
                estado="error", codigo=status.HTTP_403_FORBIDDEN
            )
        reporte.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Reporte diario eliminado (baja lógica).")

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """
        Cierra el día contable:
        1. Recalcula totales de ingresos y egresos desde los movimientos.
        2. Guarda snapshot del tipo de cambio actual desde ConfiguracionGlobal.
        3. Calcula saldo_arrastre_fin = saldo_arrastre_inicio + resultado_neto.
        4. Cambia estado a CERRADO — ya no se puede modificar.
        """
        reporte = get_object_or_404(ReporteDiario, pk=pk)
        if reporte.estado_reporte == ReporteDiario.EstadoReporte.CERRADO:
            return respuesta_estandar(mensaje="El reporte ya está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        # Calcular totales desde los movimientos del día
        from django.db.models import Sum
        movimientos = reporte.movimientos.filter(eliminado_en__isnull=True)
        ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or 0
        egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or 0
        neto = ingresos - egresos

        # Snapshot de tipo de cambio actual
        tipo_cambio_usd = reporte.tipo_cambio_usd_snapshot
        tipo_cambio_eur = reporte.tipo_cambio_eur_snapshot
        try:
            from configuraciones_globales.models import ConfiguracionGlobal
            tc_usd = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_USD').first()
            tc_eur = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_EUR').first()
            if tc_usd:
                tipo_cambio_usd = tc_usd.valor_tipado or reporte.tipo_cambio_usd_snapshot
            if tc_eur:
                tipo_cambio_eur = tc_eur.valor_tipado or reporte.tipo_cambio_eur_snapshot
        except Exception:
            pass

        # Actualizar y cerrar
        reporte.total_ingresos          = ingresos
        reporte.total_egresos           = egresos
        reporte.resultado_neto          = neto
        reporte.saldo_arrastre_fin      = reporte.saldo_arrastre_inicio + neto
        reporte.tipo_cambio_usd_snapshot = tipo_cambio_usd
        reporte.tipo_cambio_eur_snapshot = tipo_cambio_eur
        reporte.estado_reporte          = ReporteDiario.EstadoReporte.CERRADO
        reporte.cerrado_en              = timezone.now()
        reporte.cerrado_por             = request.user if request.user.is_authenticated else None
        reporte.save()

        return respuesta_estandar(data=ReporteDiarioSerializer(reporte).data, mensaje=f"Reporte del día {reporte.fecha_contable} cerrado correctamente.")


# ─────────────────────────────────────────────────────────────────────────────
#  MOVIMIENTO DIARIO
# ─────────────────────────────────────────────────────────────────────────────

class MovimientoDiarioViewSet(viewsets.ViewSet):
    """
    CRUD de movimientos dentro de un ReporteDiario.
    Solo se permiten modificaciones si el reporte está ABIERTO y dentro del horario.
    Soporta filtrado por ?reporte_id= y ?categoria_id=
    """

    def _get_reporte_valido(self, reporte_id):
        """Obtiene el reporte y verifica que sea editable."""
        reporte = get_object_or_404(ReporteDiario, pk=reporte_id)
        editable, error_response = _verificar_reporte_editable(reporte)
        return reporte, editable, error_response

    def list(self, request):
        qs = MovimientoDiario.objects.all()
        reporte_id   = request.query_params.get('reporte_id')
        categoria_id = request.query_params.get('categoria_id')
        if reporte_id:
            qs = qs.filter(reporte_id=reporte_id)
        if categoria_id:
            qs = qs.filter(concepto__categoria_id=categoria_id)
        return respuesta_estandar(data=MovimientoDiarioListSerializer(qs, many=True).data, mensaje="Movimientos obtenidos.")

    def create(self, request):
        reporte_id = request.data.get('reporte')
        if reporte_id:
            reporte = get_object_or_404(ReporteDiario, pk=reporte_id)
            editable, error_response = _verificar_reporte_editable(reporte)
            if not editable:
                return error_response
        s = MovimientoDiarioSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Movimiento registrado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al registrar movimiento.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        return respuesta_estandar(data=MovimientoDiarioSerializer(get_object_or_404(MovimientoDiario, pk=pk)).data, mensaje="Movimiento obtenido.")

    def update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        editable, error_response = _verificar_reporte_editable(mov.reporte)
        if not editable:
            return error_response
        s = MovimientoDiarioSerializer(mov, data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Movimiento actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error al actualizar.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        editable, error_response = _verificar_reporte_editable(mov.reporte)
        if not editable:
            return error_response
        s = MovimientoDiarioSerializer(mov, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Movimiento actualizado parcialmente.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        mov = get_object_or_404(MovimientoDiario, pk=pk)
        editable, error_response = _verificar_reporte_editable(mov.reporte)
        if not editable:
            return error_response
        mov.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Movimiento eliminado (baja lógica).")
