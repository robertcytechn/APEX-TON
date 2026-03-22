from django.db.models import Sum
from datetime import date
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from configuraciones_globales.models import RubroContable
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
            - dia         (opcional, filtra un día específico dentro del mes)

    GET /api/estado-resultados/?sucursal_id=1&mes=3&anio=2026
    GET /api/estado-resultados/?sucursal_id=1&mes=3&anio=2026&dia=19
    """

    @staticmethod
    def _construir_rubros_base():
        rubros = (
            RubroContable.objects.filter(eliminado_en__isnull=True)
            .order_by('padre', 'nombre')
            .values('id', 'nombre', 'tipo', 'padre')
        )
        return {
            rubro['id']: {
                "rubro_id": rubro['id'],
                "rubro_nombre": rubro['nombre'],
                "rubro_tipo": rubro['tipo'],
                "rubro_padre": rubro['padre'],
                "total_ingresos": 0.0,
                "total_egresos": 0.0,
                "resultado_neto": 0.0,
            }
            for rubro in rubros
        }

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
            dia_param = request.query_params.get('dia')
            dia = int(dia_param) if dia_param not in (None, '') else None
        except ValueError:
            return respuesta_estandar(
                mensaje="Los parámetros 'mes', 'anio' y 'dia' deben ser números enteros.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        if mes < 1 or mes > 12:
            return respuesta_estandar(
                mensaje="El parámetro 'mes' debe estar en el rango 1-12.",
                estado="error", codigo=status.HTTP_400_BAD_REQUEST
            )

        fecha_especifica = None
        if dia is not None:
            try:
                fecha_especifica = date(anio, mes, dia)
            except ValueError:
                return respuesta_estandar(
                    mensaje="La combinación de 'anio', 'mes' y 'dia' no representa una fecha válida.",
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

            if libro and fecha_especifica is None:
                rubros_base = self._construir_rubros_base()
                desglose_snapshot = libro.desglose_por_rubro or []

                for rubro in desglose_snapshot:
                    rubro_id = rubro.get('rubro_id')
                    if rubro_id in rubros_base:
                        rubros_base[rubro_id]['total_ingresos'] = float(rubro.get('total_ingresos') or 0)
                        rubros_base[rubro_id]['total_egresos'] = float(rubro.get('total_egresos') or 0)
                        rubros_base[rubro_id]['resultado_neto'] = float(rubro.get('resultado_neto') or 0)
                        continue

                    rubros_base[rubro_id] = {
                        "rubro_id": rubro_id,
                        "rubro_nombre": rubro.get('rubro_nombre') or 'SIN RUBRO CONTABLE',
                        "rubro_tipo": rubro.get('rubro_tipo') or 'NO_CONTABLE',
                        "rubro_padre": rubro.get('rubro_padre'),
                        "total_ingresos": float(rubro.get('total_ingresos') or 0),
                        "total_egresos": float(rubro.get('total_egresos') or 0),
                        "resultado_neto": float(rubro.get('resultado_neto') or 0),
                    }

                rubros_lista = list(rubros_base.values())
                rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))

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
                    "por_rubro":            rubros_lista,
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

        if fecha_especifica is not None:
            movimientos = movimientos.filter(reporte__fecha_contable=fecha_especifica)

        rubros_base = self._construir_rubros_base()

        def construir_respuesta_sin_movimientos(mensaje):
            rubros_lista = list(rubros_base.values())
            rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))
            return respuesta_estandar(
                data={
                    "fuente": "tiempo_real",
                    "sucursal_id": int(sucursal_id),
                    "periodo": f"{anio}/{mes:02d}",
                    "fecha": fecha_especifica.isoformat() if fecha_especifica else None,
                    "total_ingresos": 0,
                    "total_egresos": 0,
                    "resultado_neto": 0,
                    "por_categoria": [],
                    "por_rubro": rubros_lista,
                },
                mensaje=mensaje,
            )

        if not movimientos.exists():
            if fecha_especifica is not None:
                return construir_respuesta_sin_movimientos(f"Sin movimientos registrados para {fecha_especifica.isoformat()}.")
            return construir_respuesta_sin_movimientos(f"Sin movimientos registrados para {anio}/{mes:02d}.")

        total_ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or 0
        total_egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or 0
        resultado_neto = total_ingresos - total_egresos

        # Desglose por Categoría Operativa
        por_categoria = {}
        por_rubro = dict(rubros_base)
        for mov in movimientos:
            cat   = mov.concepto.categoria
            rubro = mov.concepto.rubro_contable
            rubro_id = rubro.id if rubro else 'SIN_RUBRO_CONTABLE'
            rubro_nombre = rubro.nombre if rubro else 'SIN RUBRO CONTABLE'
            rubro_tipo = rubro.tipo if rubro else 'NO_CONTABLE'

            if cat.id not in por_categoria:
                por_categoria[cat.id] = {"categoria_id": cat.id, "categoria_nombre": cat.nombre, "categoria_clave": cat.clave, "tipo": cat.tipo, "total_ingresos": 0, "total_egresos": 0, "resultado_neto": 0}
            if rubro_id not in por_rubro:
                por_rubro[rubro_id] = {
                    "rubro_id": rubro_id,
                    "rubro_nombre": rubro_nombre,
                    "rubro_tipo": rubro_tipo,
                    "rubro_padre": None,
                    "total_ingresos": 0.0,
                    "total_egresos": 0.0,
                    "resultado_neto": 0.0,
                }

            campo = 'total_ingresos' if mov.concepto.tipo == 'INGRESO' else 'total_egresos'
            por_categoria[cat.id][campo] += float(mov.monto)
            por_rubro[rubro_id][campo] += float(mov.monto)

        for d in list(por_categoria.values()) + list(por_rubro.values()):
            d['resultado_neto'] = d['total_ingresos'] - d['total_egresos']

        reportes_mes = ReporteDiario.objects.filter(
            sucursal_id=sucursal_id,
            fecha_contable__year=anio,
            fecha_contable__month=mes,
        )

        if fecha_especifica is not None:
            reportes_mes = reportes_mes.filter(fecha_contable=fecha_especifica)

        primer_reporte = reportes_mes.order_by('fecha_contable').first()
        saldo_inicio = float(primer_reporte.saldo_arrastre_inicio) if primer_reporte else 0

        rubros_lista = list(por_rubro.values())
        rubros_lista.sort(key=lambda rubro: ((rubro.get('rubro_padre') or ''), rubro.get('rubro_nombre') or ''))

        data = {
            "fuente":               "tiempo_real",
            "sucursal_id":          int(sucursal_id),
            "periodo":              f"{anio}/{mes:02d}",
            "fecha":               fecha_especifica.isoformat() if fecha_especifica else None,
            "saldo_arrastre_inicio": saldo_inicio,
            "total_ingresos":       float(total_ingresos),
            "total_egresos":        float(total_egresos),
            "resultado_neto":       float(resultado_neto),
            "saldo_proyectado_fin":  saldo_inicio + float(resultado_neto),
            "por_categoria":        list(por_categoria.values()),
            "por_rubro":            rubros_lista,
        }

        if fecha_especifica is not None:
            return respuesta_estandar(data=data, mensaje=f"Estado de resultados {fecha_especifica.isoformat()} calculado en tiempo real.")
        return respuesta_estandar(data=data, mensaje=f"Estado de resultados {anio}/{mes:02d} calculado en tiempo real.")

