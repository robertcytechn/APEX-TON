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


# 1) Para qué sirve: automatizar el cierre diario contable para todas las sucursales activas.
# 2) Cómo funciona: recorre sucursales en transacción, calcula neto, snapshot y cambia estado a CERRADO.
# 3) Qué hace: consolida resultados del día T-1 y dispara cierre mensual cuando corresponde.
# 4) Cómo editarla: ajusta secuencia de cálculo o reglas de cierre sin romper atomicidad por sucursal.
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
        cfg_usd = ConfiguracionGlobal.objects.filter(clave='TASA_CAMBIO_DOLARES').first()
        if not cfg_usd:
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


# 1) Para qué sirve: consolidar y cerrar el libro mensual de estado de resultados.
# 2) Cómo funciona: agrega movimientos del mes, genera desglose por rubro y persiste snapshots.
# 3) Qué hace: marca el mes como CERRADO para proteger integridad histórica.
# 4) Cómo editarla: modifica aquí la lógica de desglose o saldos si cambian reglas financieras.
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
            ).select_related('concepto__rubro_contable__padre')

            # Desglose JSON por rubro con estructura detallada para estado de resultados historico.
            desglose = {}
            for mov in movimientos:
                rubro = mov.concepto.rubro_contable
                rubro_id = rubro.id if rubro else 'SIN_RUBRO_CONTABLE'
                rubro_nombre = rubro.nombre if rubro else 'SIN RUBRO CONTABLE'
                rubro_tipo = rubro.tipo if rubro else 'NO_CONTABLE'
                rubro_padre = rubro.padre.nombre if rubro and rubro.padre else 'SIN GRUPO'
                rubro_padre_clave = rubro.padre.clave if rubro and rubro.padre else None
                rubro_padre_considerar = bool(rubro.padre.considerar_en_estado_resultados) if rubro and rubro.padre else True

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

            rubros_ordenados = sorted(
                list(desglose.values()),
                key=lambda rubro_item: ((rubro_item.get('rubro_padre') or ''), (rubro_item.get('rubro_nombre') or '')),
            )

            rubros_considerados = [
                rubro_item for rubro_item in rubros_ordenados
                if bool(rubro_item.get('rubro_padre_considerar_en_estado_resultados', True))
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
            libro.save()

            logger.info(f"[CIERRE MES] {sucursal.nombre} {anio}/{mes:02d}: LibroEstadoResultados cerrado. Neto considerado: ${resultado_neto_considerado:,.2f}")

    except Exception as exc:
        logger.error(f"[CIERRE MES] Error al cerrar libro {sucursal.nombre} {anio}/{mes:02d}: {exc}")
