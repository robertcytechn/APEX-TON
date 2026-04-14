from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import LibroEstadoResultados
from .serializers import LibroEstadoResultadosSerializer, LibroEstadoResultadosListSerializer
from reportes_diarios.models import ReporteDiario, MovimientoDiario


# 1) Para qué sirve: mantener salida estándar en endpoints del libro histórico mensual.
# 2) Cómo funciona: empaqueta resultado en estructura status/message/data.
# 3) Qué hace: evita inconsistencias entre respuestas de operaciones del libro.
# 4) Cómo editarla: modifica esta función al cambiar el contrato transversal de API.
def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


# 1) Para qué sirve: normalizar cadenas de rubro para validaciones contables.
# 2) Cómo funciona: estandariza texto a mayúsculas con separadores uniformes.
# 3) Qué hace: facilita detección de etiquetas no contables en claves/nombres.
# 4) Cómo editarla: amplía sustituciones si surgen nuevos formatos en catálogo.
def _normalizar_texto_rubro(valor):
    return str(valor or '').strip().replace('-', '_').replace(' ', '_').upper()


# 1) Para qué sirve: identificar rubros no contables en el cierre mensual.
# 2) Cómo funciona: evalúa ausencia de rubro y patrones semánticos de exclusión.
# 3) Qué hace: detecta SIN_RUBRO, SIN_GRUPO o NO_CONTABLE para no impactar totales.
# 4) Cómo editarla: incorpora nuevas palabras clave si negocio agrega nomenclaturas.
def _rubro_es_no_contable(rubro=None, rubro_id=None, rubro_tipo=None, rubro_padre_clave=None, rubro_padre_nombre=None):
    if rubro is not None:
        rubro_id = getattr(rubro, 'id', rubro_id)
        rubro_tipo = getattr(rubro, 'tipo', rubro_tipo)
        padre = getattr(rubro, 'padre', None)
        rubro_padre_clave = getattr(padre, 'clave', rubro_padre_clave) if padre else rubro_padre_clave
        rubro_padre_nombre = getattr(padre, 'nombre', rubro_padre_nombre) if padre else rubro_padre_nombre

    identificador = _normalizar_texto_rubro(rubro_id)
    tipo_rubro = _normalizar_texto_rubro(rubro_tipo)
    padre_clave = _normalizar_texto_rubro(rubro_padre_clave)
    padre_nombre = _normalizar_texto_rubro(rubro_padre_nombre)
    huella_padre = f"{padre_clave} {padre_nombre}"

    if not identificador:
        return True

    if identificador in {'SIN_RUBRO_CONTABLE', 'SINRUBROCONTABLE', 'SIN_RUBRO', 'SINRUBRO'}:
        return True

    if tipo_rubro in {'NO_CONTABLE', 'NOCONTABLE'}:
        return True

    if 'NO_CONTABLE' in huella_padre or 'NOCONTABLE' in huella_padre:
        return True

    if 'SIN_GRUPO' in huella_padre or 'SINGRUPO' in huella_padre:
        return True

    return False


# 1) Para qué sirve: decidir si un rubro entra al total contable del mes.
# 2) Cómo funciona: combina bandera del padre con clasificación no contable.
# 3) Qué hace: evita que rubros no contables alteren total_ingresos/egresos/neto.
# 4) Cómo editarla: mantén aquí la regla maestra para cierre mensual.
def _rubro_debe_considerarse_en_estado_resultados(
    rubro=None,
    rubro_id=None,
    rubro_tipo=None,
    rubro_padre_clave=None,
    rubro_padre_nombre=None,
    considerar_padre=True,
):
    if not bool(considerar_padre):
        return False

    return not _rubro_es_no_contable(
        rubro=rubro,
        rubro_id=rubro_id,
        rubro_tipo=rubro_tipo,
        rubro_padre_clave=rubro_padre_clave,
        rubro_padre_nombre=rubro_padre_nombre,
    )


# 1) Para qué sirve: administrar apertura, consulta y cierre del libro mensual por sucursal.
# 2) Cómo funciona: expone CRUD controlado y acción cerrar_mes con agregación de movimientos.
# 3) Qué hace: genera snapshot histórico inmutable del estado de resultados mensual.
# 4) Cómo editarla: integra nuevas reglas de cierre en cerrar_mes preservando validación de estado.
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
        ).select_related('concepto__rubro_contable__padre')

        # Desglose por rubro como snapshot JSON detallado para consultas historicas.
        desglose = {}
        for mov in movimientos:
            rubro = mov.concepto.rubro_contable
            rubro_id = rubro.id if rubro else 'SIN_RUBRO_CONTABLE'
            rubro_nombre = rubro.nombre if rubro else 'SIN RUBRO CONTABLE'
            rubro_tipo = rubro.tipo if rubro else 'NO_CONTABLE'
            rubro_padre = rubro.padre.nombre if rubro and rubro.padre else 'SIN GRUPO'
            rubro_padre_clave = rubro.padre.clave if rubro and rubro.padre else None
            rubro_padre_considerar = _rubro_debe_considerarse_en_estado_resultados(
                rubro=rubro,
                rubro_id=rubro_id,
                rubro_tipo=rubro_tipo,
                rubro_padre_clave=rubro_padre_clave,
                rubro_padre_nombre=rubro_padre,
                considerar_padre=(bool(rubro.padre.considerar_en_estado_resultados) if rubro and rubro.padre else False),
            )

            if rubro_id not in desglose:
                desglose[rubro_id] = {
                    "rubro_id": rubro_id,
                    "rubro_nombre": rubro_nombre,
                    "rubro_tipo": rubro_tipo,
                    "rubro_padre": rubro_padre,
                    "rubro_padre_clave": rubro_padre_clave,
                    "rubro_padre_considerar_en_estado_resultados": rubro_padre_considerar,
                    "total_ingresos": 0.0,
                    "total_egresos": 0.0,
                    "resultado_neto": 0.0,
                }

            if mov.concepto.tipo == 'INGRESO':
                desglose[rubro_id]['total_ingresos'] += float(mov.monto)
            else:
                desglose[rubro_id]['total_egresos'] += float(mov.monto)

        for rubro_id in desglose:
            desglose[rubro_id]['resultado_neto'] = desglose[rubro_id]['total_ingresos'] - desglose[rubro_id]['total_egresos']

        # Snapshot del tipo de cambio actual
        tc_usd = libro.tipo_cambio_usd_snapshot
        tc_eur = libro.tipo_cambio_eur_snapshot
        try:
            from configuraciones_globales.models import ConfiguracionGlobal
            cfg_usd = ConfiguracionGlobal.objects.filter(clave='TASA_CAMBIO_DOLARES').first()
            if not cfg_usd:
                cfg_usd = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_USD').first()
            cfg_eur = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_EUR').first()
            if cfg_usd:
                tc_usd = cfg_usd.valor_tipado or tc_usd
            if cfg_eur:
                tc_eur = cfg_eur.valor_tipado or tc_eur
        except Exception:
            pass

        rubros_ordenados = sorted(
            list(desglose.values()),
            key=lambda rubro_item: ((rubro_item.get('rubro_padre') or ''), (rubro_item.get('rubro_nombre') or '')),
        )

        rubros_considerados = [
            rubro_item for rubro_item in rubros_ordenados
            if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', False))
        ]
        total_ingresos_considerados = sum(float(rubro_item.get('total_ingresos') or 0) for rubro_item in rubros_considerados)
        total_egresos_considerados = sum(float(rubro_item.get('total_egresos') or 0) for rubro_item in rubros_considerados)
        resultado_neto_considerado = total_ingresos_considerados - total_egresos_considerados

        libro.total_ingresos          = total_ingresos_considerados
        libro.total_egresos           = total_egresos_considerados
        libro.resultado_neto          = resultado_neto_considerado
        libro.saldo_arrastre_fin      = libro.saldo_arrastre_inicio + resultado_neto_considerado
        libro.desglose_por_rubro      = rubros_ordenados
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
