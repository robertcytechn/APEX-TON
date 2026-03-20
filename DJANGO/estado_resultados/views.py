from django.db.models import Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from reportes_diarios.models import ReporteDiario, MovimientoDiario


def respuesta_estandar(data=None, mensaje="Operación exitosa", estado="success", codigo=status.HTTP_200_OK):
    return Response({"status": estado, "message": mensaje, "data": data}, status=codigo)


class EstadoResultadosAPIView(APIView):
    """
    Endpoint de Estado de Resultados con modo dual:

    - Mes CERRADO (LibroEstadoResultados.estado_mes == CERRADO):
      Devuelve directamente el snapshot guardado en `LibroEstadoResultados.desglose_por_rubro`.
      Lectura instantánea, sin costo de agregación. Ideal para consultas del rol Director.

    - Mes en CURSO (no hay libro cerrado):
      Agrega en tiempo real desde MovimientoDiario. Siempre refleja el estado actual.

    Parámetros de query:
      - sucursal_id (obligatorio)
      - mes         (opcional, default: mes actual)
      - anio        (opcional, default: año actual)

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

        # ── Modo 1: Mes CERRADO → devolver snapshot del libro ─────────────────
        try:
            from libro_estado_resultados.models import LibroEstadoResultados
            libro = LibroEstadoResultados.objects.filter(
                sucursal_id=sucursal_id,
                anio=anio,
                mes=mes,
                estado_mes=LibroEstadoResultados.EstadoMes.CERRADO,
                eliminado_en__isnull=True,
            ).first()

            if libro:
                data = {
                    "fuente":               "snapshot_historico",
                    "sucursal_id":          int(sucursal_id),
                    "periodo":              f"{anio}/{mes:02d}",
                    "estado_mes":           libro.estado_mes,
                    "saldo_arrastre_inicio": float(libro.saldo_arrastre_inicio),
                    "total_ingresos":       float(libro.total_ingresos),
                    "total_egresos":        float(libro.total_egresos),
                    "resultado_neto":       float(libro.resultado_neto),
                    "saldo_arrastre_fin":   float(libro.saldo_arrastre_fin),
                    "tipo_cambio_usd":      float(libro.tipo_cambio_usd_snapshot),
                    "tipo_cambio_eur":      float(libro.tipo_cambio_eur_snapshot),
                    "cerrado_en":           libro.cerrado_en.isoformat() if libro.cerrado_en else None,
                    "por_rubro":            libro.desglose_por_rubro,
                    "por_categoria":        [],  # No disponible en snapshot — consultar MovimientoDiario si se necesita
                }
                return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} — datos del cierre histórico.")
        except Exception:
            pass  # Si no hay libro, continuar con modo en tiempo real

        # ── Modo 2: Mes en curso → agregar en tiempo real ──────────────────────
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
                    "fuente":        "tiempo_real",
                    "sucursal_id":   int(sucursal_id),
                    "periodo":       f"{anio}/{mes:02d}",
                    "total_ingresos": 0,
                    "total_egresos":  0,
                    "resultado_neto": 0,
                    "por_categoria":  [],
                    "por_rubro":      [],
                },
                mensaje=f"Sin movimientos registrados para {anio}/{mes:02d}."
            )

        total_ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or 0
        total_egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or 0
        resultado_neto = total_ingresos - total_egresos

        # Desglose por Categoría Operativa
        por_categoria = {}
        por_rubro = {}
        for mov in movimientos:
            cat   = mov.concepto.categoria
            rubro = mov.concepto.rubro_contable

            if cat.id not in por_categoria:
                por_categoria[cat.id] = {"categoria_id": cat.id, "categoria_nombre": cat.nombre, "categoria_clave": cat.clave, "tipo": cat.tipo, "total_ingresos": 0, "total_egresos": 0, "resultado_neto": 0}
            if rubro.id not in por_rubro:
                por_rubro[rubro.id] = {"rubro_id": rubro.id, "rubro_nombre": rubro.nombre, "rubro_tipo": rubro.tipo, "total_ingresos": 0, "total_egresos": 0, "resultado_neto": 0}

            campo = 'total_ingresos' if mov.concepto.tipo == 'INGRESO' else 'total_egresos'
            por_categoria[cat.id][campo] += float(mov.monto)
            por_rubro[rubro.id][campo]   += float(mov.monto)

        for d in list(por_categoria.values()) + list(por_rubro.values()):
            d['resultado_neto'] = d['total_ingresos'] - d['total_egresos']

        primer_reporte = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__year=anio,
            fecha_contable__month=mes,
        ).order_by('fecha_contable').first()
        saldo_inicio = float(primer_reporte.saldo_arrastre_inicio) if primer_reporte else 0

        data = {
            "fuente":               "tiempo_real",
            "sucursal_id":          int(sucursal_id),
            "periodo":              f"{anio}/{mes:02d}",
            "saldo_arrastre_inicio": saldo_inicio,
            "total_ingresos":       float(total_ingresos),
            "total_egresos":        float(total_egresos),
            "resultado_neto":       float(resultado_neto),
            "saldo_proyectado_fin":  saldo_inicio + float(resultado_neto),
            "por_categoria":        list(por_categoria.values()),
            "por_rubro":            list(por_rubro.values()),
        }
        return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} calculado en tiempo real.")

