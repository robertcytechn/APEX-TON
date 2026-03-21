from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import LibroEstadoResultados
from .serializers import LibroEstadoResultadosSerializer, LibroEstadoResultadosListSerializer
from reportes_diarios.models import ReporteDiario, MovimientoDiario


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


class LibroEstadoResultadosViewSet(viewsets.ViewSet):
    """
    Gestión del Libro de Estado de Resultados mensual (snapshot histórico).

    Endpoints principales:
      list        → GET  /libro-estado-resultados/?sucursal_id=X&anio=X
      retrieve    → GET  /libro-estado-resultados/{id}/
      cerrar_mes  → POST /libro-estado-resultados/{id}/cerrar-mes/
                    (Calcula totales, toma snapshot, cierra el mes permanentemente)
    """

    def list(self, request):
        qs = LibroEstadoResultados.objects.all()
        sucursal_id = request.query_params.get('sucursal_id')
        anio = request.query_params.get('anio')
        if sucursal_id:
            qs = qs.filter(sucursal_id=sucursal_id)
        if anio:
            qs = qs.filter(anio=anio)
        return respuesta_estandar(data=LibroEstadoResultadosListSerializer(qs, many=True).data, mensaje="Libros de estado de resultados obtenidos.")

    def create(self, request):
        """Crear un registro de libro para un mes (estado inicial ABIERTO)."""
        s = LibroEstadoResultadosSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Libro creado.", codigo=status.HTTP_201_CREATED)
        return respuesta_estandar(data=s.errors, mensaje="Error al crear libro.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        libro = get_object_or_404(LibroEstadoResultados, pk=pk)
        return respuesta_estandar(data=LibroEstadoResultadosSerializer(libro).data, mensaje="Libro obtenido.")

    def partial_update(self, request, pk=None):
        libro = get_object_or_404(LibroEstadoResultados, pk=pk)
        if libro.estado_mes == LibroEstadoResultados.EstadoMes.CERRADO:
            return respuesta_estandar(mensaje="El libro ya está cerrado y no puede modificarse.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        s = LibroEstadoResultadosSerializer(libro, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return respuesta_estandar(data=s.data, mensaje="Libro actualizado.")
        return respuesta_estandar(data=s.errors, mensaje="Error.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        libro = get_object_or_404(LibroEstadoResultados, pk=pk)
        if libro.estado_mes == LibroEstadoResultados.EstadoMes.CERRADO:
            return respuesta_estandar(mensaje="No se puede eliminar un libro cerrado.", estado="error", codigo=status.HTTP_403_FORBIDDEN)
        libro.eliminar_logico(usuario=request.user if request.user.is_authenticated else None)
        return respuesta_estandar(mensaje="Libro eliminado (baja lógica).")

    @action(detail=True, methods=['post'], url_path='cerrar-mes')
    def cerrar_mes(self, request, pk=None):
        """
        Cierra el mes:
        1. Agrega todos los movimientos del período.
        2. Calcula desglose por rubro contable (snapshot JSON).
        3. Toma snapshot del tipo de cambio actual.
        4. Calcula saldo_arrastre_fin.
        5. Marca estado_mes = CERRADO. Inmutable desde este momento.
        """
        libro = get_object_or_404(LibroEstadoResultados, pk=pk)

        if libro.estado_mes == LibroEstadoResultados.EstadoMes.CERRADO:
            return respuesta_estandar(mensaje="El mes ya está cerrado.", estado="error", codigo=status.HTTP_400_BAD_REQUEST)

        movimientos = MovimientoDiario.objects.filter(
            reporte__sucursal_id=libro.sucursal_id,
            reporte__fecha_contable__year=libro.anio,
            reporte__fecha_contable__month=libro.mes,
            eliminado_en__isnull=True,
        ).select_related('concepto__rubro_contable')

        total_ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
        total_egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
        resultado_neto = total_ingresos - total_egresos

        # Desglose por rubro como snapshot JSON
        desglose = {}
        for mov in movimientos:
            rubro_nombre = mov.concepto.rubro_contable.nombre if mov.concepto.rubro_contable else 'SIN RUBRO CONTABLE'
            if rubro_nombre not in desglose:
                desglose[rubro_nombre] = {"ingresos": 0, "egresos": 0, "neto": 0}
            if mov.concepto.tipo == 'INGRESO':
                desglose[rubro_nombre]['ingresos'] += float(mov.monto)
            else:
                desglose[rubro_nombre]['egresos'] += float(mov.monto)
        for k in desglose:
            desglose[k]['neto'] = desglose[k]['ingresos'] - desglose[k]['egresos']

        # Snapshot del tipo de cambio actual
        tc_usd = libro.tipo_cambio_usd_snapshot
        tc_eur = libro.tipo_cambio_eur_snapshot
        try:
            from configuraciones_globales.models import ConfiguracionGlobal
            cfg_usd = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_USD').first()
            cfg_eur = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_EUR').first()
            if cfg_usd:
                tc_usd = cfg_usd.valor_tipado or tc_usd
            if cfg_eur:
                tc_eur = cfg_eur.valor_tipado or tc_eur
        except Exception:
            pass

        libro.total_ingresos          = total_ingresos
        libro.total_egresos           = total_egresos
        libro.resultado_neto          = resultado_neto
        libro.saldo_arrastre_fin      = libro.saldo_arrastre_inicio + resultado_neto
        libro.desglose_por_rubro      = desglose
        libro.tipo_cambio_usd_snapshot = tc_usd
        libro.tipo_cambio_eur_snapshot = tc_eur
        libro.estado_mes              = LibroEstadoResultados.EstadoMes.CERRADO
        libro.cerrado_en              = timezone.now()
        libro.cerrado_por             = request.user if request.user.is_authenticated else None
        libro.save()

        return respuesta_estandar(
            data=LibroEstadoResultadosSerializer(libro).data,
            mensaje=f"Mes {libro.anio}/{libro.mes:02d} cerrado correctamente para {libro.sucursal.nombre}."
        )
