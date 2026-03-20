"""
Tareas asíncronas de Celery para el módulo reportes_diarios.
La tarea principal es el cierre automático del día contable al alcanzar la hora_cierre
configurada en ConfiguracionGlobal.
"""
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
import calendar

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='reportes_diarios.cerrar_dia_contable', max_retries=3)
def cerrar_dia_contable(self):
    """
    Tarea programada de Celery Beat que se ejecuta a la hora_cierre del sistema.

    Para cada sucursal activa:
    1. Obtiene el ReporteDiario del día contable actual (T-1) si existe y está ABIERTO.
    2. Calcula totales de ingresos, egresos y resultado neto.
    3. Toma snapshot del tipo de cambio vigente.
    4. Calcula saldo_arrastre_fin.
    5. Cambia estado a CERRADO (usa select_for_update para evitar condiciones de carrera).
    6. Si es el último día del mes, genera el LibroEstadoResultados del mes.

    Los bloqueos de transacción garantizan consistencia incluso si la tarea se ejecuta
    concurrentemente en múltiples workers.
    """
    from reportes_diarios.models import ReporteDiario, MovimientoDiario
    from sucursales.models import Sucursal
    from configuraciones_globales.models import ConfiguracionGlobal

    fecha_contable = timezone.localdate() - timezone.timedelta(days=1)
    logger.info(f"[CIERRE AUTOMÁTICO] Iniciando cierre del día contable: {fecha_contable}")

    # Leer tipo de cambio actual como snapshot
    tc_usd = 0
    tc_eur = 0
    try:
        cfg_usd = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_USD').first()
        cfg_eur = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_EUR').first()
        if cfg_usd and cfg_usd.valor_tipado:
            tc_usd = cfg_usd.valor_tipado
        if cfg_eur and cfg_eur.valor_tipado:
            tc_eur = cfg_eur.valor_tipado
    except Exception as exc:
        logger.warning(f"[CIERRE AUTOMÁTICO] No se pudo leer el tipo de cambio: {exc}")

    sucursales = Sucursal.objects.filter(estado=Sucursal.Estado.ACTIVO)
    reportes_cerrados = 0
    errores = []

    for sucursal in sucursales:
        try:
            with transaction.atomic():
                # Buscar reporte del día; si no existe, no hay movimientos ese día, se omite.
                reporte = ReporteDiario.todos.select_for_update().filter(
                    sucursal=sucursal,
                    fecha_contable=fecha_contable,
                    estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
                    eliminado_en__isnull=True,
                ).first()

                if not reporte:
                    logger.info(f"[CIERRE AUTOMÁTICO] {sucursal.nombre}: sin reporte abierto para {fecha_contable}. Se omite.")
                    continue

                # Calcular totales con bloqueo
                movimientos = reporte.movimientos.filter(eliminado_en__isnull=True)
                ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
                egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
                neto = ingresos - egresos

                reporte.total_ingresos          = ingresos
                reporte.total_egresos           = egresos
                reporte.resultado_neto          = neto
                reporte.saldo_arrastre_fin      = reporte.saldo_arrastre_inicio + neto
                reporte.tipo_cambio_usd_snapshot = tc_usd
                reporte.tipo_cambio_eur_snapshot = tc_eur
                reporte.estado_reporte          = ReporteDiario.EstadoReporte.CERRADO
                reporte.cerrado_en              = timezone.now()
                reporte.save()

                reportes_cerrados += 1
                logger.info(f"[CIERRE AUTOMÁTICO] {sucursal.nombre}: reporte {fecha_contable} cerrado. Neto: ${neto:,.2f}")

                # ── Verificar si es fin de mes para cerrar LibroEstadoResultados ──
                ultimo_dia_del_mes = calendar.monthrange(fecha_contable.year, fecha_contable.month)[1]
                if fecha_contable.day == ultimo_dia_del_mes:
                    _cerrar_mes_automatico(sucursal, fecha_contable.year, fecha_contable.month, tc_usd, tc_eur)

        except Exception as exc:
            error_msg = f"[CIERRE AUTOMÁTICO] Error cerrando {sucursal.nombre}: {exc}"
            logger.error(error_msg)
            errores.append(error_msg)

    resumen = {
        "fecha_contable":     str(fecha_contable),
        "sucursales_procesadas": sucursales.count(),
        "reportes_cerrados":  reportes_cerrados,
        "errores":            errores,
    }
    logger.info(f"[CIERRE AUTOMÁTICO] Finalizado: {resumen}")
    return resumen


def _cerrar_mes_automatico(sucursal, anio, mes, tc_usd, tc_eur):
    """
    Genera o actualiza el LibroEstadoResultados del mes al detectar el último día.
    Solo se ejecuta si el libro aún está ABIERTO.
    """
    from libro_estado_resultados.models import LibroEstadoResultados
    from reportes_diarios.models import MovimientoDiario

    try:
        with transaction.atomic():
            libro, _ = LibroEstadoResultados.objects.select_for_update().get_or_create(
                sucursal=sucursal, anio=anio, mes=mes,
                defaults={'estado_mes': LibroEstadoResultados.EstadoMes.ABIERTO}
            )

            if libro.estado_mes == LibroEstadoResultados.EstadoMes.CERRADO:
                logger.info(f"[CIERRE MES] {sucursal.nombre} {anio}/{mes:02d}: ya está cerrado.")
                return

            movimientos = MovimientoDiario.objects.filter(
                reporte__sucursal=sucursal,
                reporte__fecha_contable__year=anio,
                reporte__fecha_contable__month=mes,
                eliminado_en__isnull=True,
            ).select_related('concepto__rubro_contable')

            ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
            egresos  = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
            neto = ingresos - egresos

            # Desglose JSON por rubro
            desglose = {}
            for mov in movimientos:
                rubro = mov.concepto.rubro_contable.nombre
                if rubro not in desglose:
                    desglose[rubro] = {"ingresos": 0, "egresos": 0, "neto": 0}
                if mov.concepto.tipo == 'INGRESO':
                    desglose[rubro]['ingresos'] += float(mov.monto)
                else:
                    desglose[rubro]['egresos'] += float(mov.monto)
            for k in desglose:
                desglose[k]['neto'] = desglose[k]['ingresos'] - desglose[k]['egresos']

            libro.total_ingresos          = ingresos
            libro.total_egresos           = egresos
            libro.resultado_neto          = neto
            libro.saldo_arrastre_fin      = libro.saldo_arrastre_inicio + neto
            libro.desglose_por_rubro      = desglose
            libro.tipo_cambio_usd_snapshot = tc_usd
            libro.tipo_cambio_eur_snapshot = tc_eur
            libro.estado_mes              = LibroEstadoResultados.EstadoMes.CERRADO
            libro.cerrado_en              = timezone.now()
            libro.save()

            logger.info(f"[CIERRE MES] {sucursal.nombre} {anio}/{mes:02d}: LibroEstadoResultados cerrado. Neto: ${neto:,.2f}")

    except Exception as exc:
        logger.error(f"[CIERRE MES] Error al cerrar libro {sucursal.nombre} {anio}/{mes:02d}: {exc}")
