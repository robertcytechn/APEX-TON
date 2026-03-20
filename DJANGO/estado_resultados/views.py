from django.db import models
from django.db.models import Sum, Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from reportes_diarios.models import ReporteDiario, MovimientoDiario


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


class EstadoResultadosAPIView(APIView):
    """
    Endpoint de agregación en tiempo real del Estado de Resultados.
    
    Parámetros de query:
      - sucursal_id (obligatorio): ID de la sucursal.
      - mes (opcional): Número de mes 1-12. Por defecto el mes actual.
      - anio (opcional): Año de 4 dígitos. Por defecto el año actual.

    Respuesta: ingresos/egresos agrupados por categoría y rubro contable.
    
    GET /api/estado-resultados/?sucursal_id=1&mes=3&anio=2026
    """

    def get(self, request):
        sucursal_id = request.query_params.get('sucursal_id')
        if not sucursal_id:
            return respuesta_estandar(
                mensaje="El parámetro 'sucursal_id' es obligatorio.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        hoy = timezone.localdate()
        try:
            mes  = int(request.query_params.get('mes', hoy.month))
            anio = int(request.query_params.get('anio', hoy.year))
        except ValueError:
            return respuesta_estandar(
                mensaje="Los parámetros 'mes' y 'anio' deben ser números enteros.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar movimientos del período solicitado
        movimientos = MovimientoDiario.objects.filter(
            reporte__sucursal_id=sucursal_id,
            reporte__fecha_contable__year=anio,
            reporte__fecha_contable__month=mes,
            eliminado_en__isnull=True,
        ).select_related(
            'concepto__categoria',
            'concepto__rubro_contable',
        )

        if not movimientos.exists():
            return respuesta_estandar(
                data={
                    "sucursal_id": sucursal_id,
                    "periodo": f"{anio}/{mes:02d}",
                    "total_ingresos": 0,
                    "total_egresos": 0,
                    "resultado_neto": 0,
                    "por_categoria": [],
                    "por_rubro": [],
                },
                mensaje=f"Sin movimientos registrados para {anio}/{mes:02d}."
            )

        # ── Totales globales ───────────────────────────────────────────────
        total_ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or 0
        total_egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or 0
        resultado_neto = total_ingresos - total_egresos

        # ── Desglose por Categoría Operativa ──────────────────────────────
        por_categoria = {}
        for mov in movimientos:
            cat = mov.concepto.categoria
            key = cat.id
            if key not in por_categoria:
                por_categoria[key] = {
                    "categoria_id":     cat.id,
                    "categoria_nombre": cat.nombre,
                    "categoria_clave":  cat.clave,
                    "tipo":             cat.tipo,
                    "total_ingresos":   0,
                    "total_egresos":    0,
                    "resultado_neto":   0,
                }
            if mov.concepto.tipo == 'INGRESO':
                por_categoria[key]['total_ingresos'] += float(mov.monto)
            else:
                por_categoria[key]['total_egresos'] += float(mov.monto)

        for k in por_categoria:
            por_categoria[k]['resultado_neto'] = (
                por_categoria[k]['total_ingresos'] - por_categoria[k]['total_egresos']
            )

        # ── Desglose por Rubro Contable ────────────────────────────────────
        por_rubro = {}
        for mov in movimientos:
            rubro = mov.concepto.rubro_contable
            key = rubro.id
            if key not in por_rubro:
                por_rubro[key] = {
                    "rubro_id":     rubro.id,
                    "rubro_nombre": rubro.nombre,
                    "rubro_tipo":   rubro.tipo,
                    "total_ingresos": 0,
                    "total_egresos":  0,
                    "resultado_neto": 0,
                }
            if mov.concepto.tipo == 'INGRESO':
                por_rubro[key]['total_ingresos'] += float(mov.monto)
            else:
                por_rubro[key]['total_egresos'] += float(mov.monto)

        for k in por_rubro:
            por_rubro[k]['resultado_neto'] = (
                por_rubro[k]['total_ingresos'] - por_rubro[k]['total_egresos']
            )

        # ── Saldo de arrastre al inicio del mes ───────────────────────────
        primer_reporte = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__year=anio,
            fecha_contable__month=mes,
        ).order_by('fecha_contable').first()

        saldo_arrastre_inicio = float(primer_reporte.saldo_arrastre_inicio) if primer_reporte else 0

        data = {
            "sucursal_id":          int(sucursal_id),
            "periodo":              f"{anio}/{mes:02d}",
            "saldo_arrastre_inicio": saldo_arrastre_inicio,
            "total_ingresos":       float(total_ingresos),
            "total_egresos":        float(total_egresos),
            "resultado_neto":       float(resultado_neto),
            "saldo_proyectado_fin":  saldo_arrastre_inicio + float(resultado_neto),
            "por_categoria":        list(por_categoria.values()),
            "por_rubro":            list(por_rubro.values()),
        }

        return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} calculado en tiempo real.")
