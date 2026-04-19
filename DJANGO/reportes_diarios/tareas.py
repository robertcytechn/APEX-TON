"""
Tareas asíncronas de Celery para el módulo reportes_diarios.
La tarea principal es el cierre automático del día contable al alcanzar la hora_cierre
configurada en ConfiguracionGlobal.
"""
import logging
import os
import json
import gzip
import shutil
import subprocess
import tempfile
import traceback
import zipfile
from datetime import datetime
from celery import shared_task
from django.core.mail import EmailMessage, get_connection
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
import calendar
from pathlib import Path

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


# 1) Para qué sirve: resolver la lista final de destinatarios para correos ejecutivos.
# 2) Cómo funciona: toma destinatarios globales desde ConfiguracionGlobal y opcionalmente agrega correo de sucursal.
# 3) Qué hace: unifica la fuente de destinatarios para tareas diarias y mensuales.
# 4) Cómo editarla: cambia la clave/flag en configuracion_correos_ejecutivos.py sin tocar lógica de tareas.
def _normalizar_destinatarios_local(destinatarios):
    if not destinatarios:
        return []

    vistos = set()
    resultado = []

    for destinatario in destinatarios:
        correo = str(destinatario or '').strip()
        if not correo or '@' not in correo:
            continue

        llave = correo.lower()
        if llave in vistos:
            continue

        vistos.add(llave)
        resultado.append(correo)

    return resultado


# 1) Para qué sirve: leer destinatarios desde ConfiguracionGlobal sin dependencias pesadas.
# 2) Cómo funciona: parsea listas o texto separado por coma/punto y coma/salto de línea.
# 3) Qué hace: permite resolver correos para tareas operativas aunque falten librerías de reportes.
# 4) Cómo editarla: cambia clave por defecto si negocio redefine la configuración de correos.
def _obtener_destinatarios_globales_configurados_local(clave_configuracion='DESTINATARIOS_CORREOS'):
    from configuraciones_globales.models import ConfiguracionGlobal

    configuracion = ConfiguracionGlobal.objects.filter(clave=clave_configuracion).first()
    if not configuracion:
        return []

    valor_configurado = configuracion.valor_tipado
    if valor_configurado in (None, ''):
        return []

    if isinstance(valor_configurado, (list, tuple, set)):
        candidatos = [str(item or '').strip() for item in valor_configurado]
        return _normalizar_destinatarios_local(candidatos)

    texto = str(valor_configurado)
    separador_unificado = texto.replace('\n', ',').replace(';', ',')
    candidatos = [segmento.strip() for segmento in separador_unificado.split(',')]
    return _normalizar_destinatarios_local(candidatos)


def _resolver_destinatarios_correos_ejecutivos(sucursal):
    from reportes_diarios.configuracion_correos_ejecutivos import (
        CLAVE_CONFIG_DESTINATARIOS_CORREOS,
        INCLUIR_CORREO_SUCURSAL_EN_ENVIO,
    )

    destinatarios = _obtener_destinatarios_globales_configurados_local(CLAVE_CONFIG_DESTINATARIOS_CORREOS)
    if INCLUIR_CORREO_SUCURSAL_EN_ENVIO and getattr(sucursal, 'correo', None):
        destinatarios.append(sucursal.correo)

    return _normalizar_destinatarios_local(destinatarios)


# 1) Para qué sirve: enviar correo de notificación cuando se cierra un reporte diario.
# 2) Cómo funciona: obtiene el reporte, verifica bandera correo_enviado, construye paquete y envía.
# 3) Qué hace: implementa anti-spam para evitar envíos duplicados del mismo cierre.
# 4) Cómo editarla: personaliza asunto/cuerpo desde servicios_resumenes_correo si cambia formato.
@shared_task(bind=True, name='reportes_diarios.enviar_correo_cierre_reporte', max_retries=2)
def enviar_correo_cierre_reporte(self, reporte_id):
    """
    Envía correo de cierre cuando se termina el día contable.
    
    Previene duplicados verificando la bandera correo_enviado.
    Solo se dispara después de que _cerrar_reporte_diario() haya completado.
    """
    from reportes_diarios.models import ReporteDiario
    from reportes_diarios.servicios_resumenes_correo import (
        construir_paquete_correo_resumen_diario_ejecutivo,
        enviar_paquete_correo,
    )

    try:
        reporte = ReporteDiario.objects.select_for_update().get(pk=reporte_id)
        
        if reporte.correo_enviado:
            logger.info(f"[CIERRE EMAIL] Reporte {reporte.id} ({reporte.fecha_contable}): correo ya fue enviado. Se omite.")
            return {'status': 'omitido', 'razon': 'correo_ya_enviado'}
        
        if reporte.estado_reporte != ReporteDiario.EstadoReporte.CERRADO:
            logger.warning(f"[CIERRE EMAIL] Reporte {reporte.id}: no está CERRADO aún. Se omite.")
            return {'status': 'omitido', 'razon': 'reporte_no_cerrado'}
        
        sucursal = reporte.sucursal
        destinatarios = _resolver_destinatarios_correos_ejecutivos(sucursal)
        
        if not destinatarios:
            logger.warning(f"[CIERRE EMAIL] {sucursal.nombre}: omitido por falta de destinatarios.")
            reporte.correo_enviado = True
            reporte.save(update_fields=['correo_enviado'])
            return {'status': 'omitido', 'razon': 'sin_destinatarios'}
        
        paquete = construir_paquete_correo_resumen_diario_ejecutivo(
            sucursal=sucursal,
            fecha_contable=reporte.fecha_contable,
        )
        
        resultado = enviar_paquete_correo(
            paquete_correo=paquete,
            destinatarios=destinatarios,
        )
        
        reporte.correo_enviado = True
        reporte.save(update_fields=['correo_enviado'])
        
        logger.info(
            f"[CIERRE EMAIL] {sucursal.nombre} ({reporte.fecha_contable}): "
            f"enviado a {', '.join(destinatarios)}"
        )
        
        return {
            'status': 'enviado',
            'reporte_id': reporte.id,
            'sucursal': sucursal.nombre,
            'destinatarios': destinatarios,
            'resultado': resultado,
        }
        
    except ReporteDiario.DoesNotExist:
        logger.error(f"[CIERRE EMAIL] Reporte con ID {reporte_id} no encontrado.")
        return {'status': 'error', 'razon': 'reporte_no_encontrado'}
    except Exception as exc:
        logger.error(f"[CIERRE EMAIL] Error enviando correo para reporte {reporte_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


# 1) Para qué sirve: cerrar automáticamente reportes que han cumplido su período de gracia (5 días).
# 2) Cómo funciona: se ejecuta periódicamente, lee HORARIO_CIERRE, y cierra reportes de días abiertos.
# 3) Qué hace: implementa regla de negocio de cierre con gracia sin requerir cron puntual.
# 4) Cómo editarla: cambia ventana de gracia o lógica de horario si cambian reglas contables.
@shared_task(bind=True, name='reportes_diarios.auto_cerrar_dias_con_gracia', max_retries=2)
def auto_cerrar_dias_con_gracia(self):
    """
    Tarea periódica que cierra automáticamente reportes de días anteriores que
    han cumplido su período de gracia (máximo 5 días de captura).
    
    Regla: Si hoy es lunes, este proceso:
    - Cierra reportes del viernes, sábado, domingo si aún están ABIERTOS y han pasado HORARIO_CIERRE.
    - No toca reportes del lunes.
    
    La ventana de gracia se define como: fecha_actual - 5 días como máximo.
    """
    from reportes_diarios.models import ReporteDiario
    from sucursales.models import Sucursal
    from configuraciones_globales.models import ConfiguracionGlobal
    from datetime import time

    try:
        # 1. Leer HORARIO_CIERRE desde configuración
        config_horario = ConfiguracionGlobal.objects.filter(clave='HORARIO_CIERRE').first()
        if not config_horario:
            logger.warning("[CIERRE AUTOMÁTICO CON GRACIA] No se configuró HORARIO_CIERRE. Se omite ejecución.")
            return {'status': 'omitido', 'razon': 'sin_horario_cierre'}
        
        try:
            hora_cierre = config_horario.valor_tipado
            if isinstance(hora_cierre, str):
                partes = str(hora_cierre).split(':')
                hora = int(partes[0])
                minuto = int(partes[1]) if len(partes) > 1 else 0
                hora_cierre = time(hour=hora, minute=minuto)
            elif not isinstance(hora_cierre, time):
                hora_cierre = time(hour=23, minute=59)  # fallback
        except (ValueError, AttributeError, IndexError):
            logger.warning("[CIERRE AUTOMÁTICO CON GRACIA] HORARIO_CIERRE mal formateado. Fallback a 23:59")
            hora_cierre = time(hour=23, minute=59)
        
        # 2. Verificar si ya pasó la hora de cierre hoy
        ahora = timezone.localtime(timezone.now())
        hora_actual = ahora.time()
        
        if hora_actual < hora_cierre:
            logger.debug(f"[CIERRE AUTOMÁTICO CON GRACIA] Aún no es hora de cerrar ({hora_actual} < {hora_cierre}). Se omite.")
            return {'status': 'omitido', 'razon': 'no_es_hora_cierre'}
        
        # 3. Buscar reportes que deben cerrarse (últimos 5 días, estado ABIERTO)
        desde_hace_5_dias = timezone.localdate() - timezone.timedelta(days=5)
        hoy = timezone.localdate()
        
        reportes_para_cerrar = ReporteDiario.todos.filter(
            fecha_contable__gte=desde_hace_5_dias,
            fecha_contable__lt=hoy,  # Excluye reportes de hoy (solo cierra días pasados)
            estado_reporte=ReporteDiario.EstadoReporte.ABIERTO,
            eliminado_en__isnull=True,
        ).select_related('sucursal')
        
        reportes_cerrados = 0
        errores = []
        
        for reporte in reportes_para_cerrar:
            try:
                with transaction.atomic():
                    # Re-obtener con select_for_update para evitar race conditions
                    reporte_lock = ReporteDiario.todos.select_for_update().get(pk=reporte.pk)
                    
                    if reporte_lock.estado_reporte != ReporteDiario.EstadoReporte.ABIERTO:
                        continue  # Ya fue cerrado por otro proceso
                    
                    # Leer tipo de cambio
                    tc_usd = 0
                    tc_eur = 0
                    try:
                        cfg_usd = ConfiguracionGlobal.objects.filter(clave__in=['TASA_CAMBIO_DOLARES', 'TIPO_CAMBIO_USD']).first()
                        cfg_eur = ConfiguracionGlobal.objects.filter(clave='TIPO_CAMBIO_EUR').first()
                        if cfg_usd and cfg_usd.valor_tipado:
                            tc_usd = cfg_usd.valor_tipado
                        if cfg_eur and cfg_eur.valor_tipado:
                            tc_eur = cfg_eur.valor_tipado
                    except Exception as exc:
                        logger.warning(f"[CIERRE AUTOMÁTICO CON GRACIA] No se pudo leer tipo de cambio: {exc}")
                    
                    # Calcular totales
                    movimientos = reporte_lock.movimientos.filter(eliminado_en__isnull=True)
                    ingresos = movimientos.filter(concepto__tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or 0
                    egresos = movimientos.filter(concepto__tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or 0
                    neto = ingresos - egresos
                    
                    # Actualizar reporte
                    reporte_lock.total_ingresos = ingresos
                    reporte_lock.total_egresos = egresos
                    reporte_lock.resultado_neto = neto
                    reporte_lock.saldo_arrastre_fin = reporte_lock.saldo_arrastre_inicio + neto
                    reporte_lock.tipo_cambio_usd_snapshot = tc_usd
                    reporte_lock.tipo_cambio_eur_snapshot = tc_eur
                    reporte_lock.estado_reporte = ReporteDiario.EstadoReporte.CERRADO
                    reporte_lock.cerrado_en = timezone.now()
                    reporte_lock.correo_enviado = False  # Bandera para enviar email después
                    reporte_lock.save()
                    
                    reportes_cerrados += 1
                    logger.info(
                        f"[CIERRE AUTOMÁTICO CON GRACIA] {reporte_lock.sucursal.nombre} "
                        f"({reporte_lock.fecha_contable}): cerrado automáticamente. Neto: ${neto:,.2f}"
                    )
                    
                    # Dispara tarea de envío de email
                    enviar_correo_cierre_reporte.delay(reporte_lock.id)
                    
                    # Verificar si es fin de mes para cerrar LibroEstadoResultados
                    ultimo_dia_del_mes = calendar.monthrange(reporte_lock.fecha_contable.year, reporte_lock.fecha_contable.month)[1]
                    if reporte_lock.fecha_contable.day == ultimo_dia_del_mes:
                        _cerrar_mes_automatico(
                            reporte_lock.sucursal,
                            reporte_lock.fecha_contable.year,
                            reporte_lock.fecha_contable.month,
                            tc_usd,
                            tc_eur
                        )
                    
            except Exception as exc:
                error_msg = f"[CIERRE AUTOMÁTICO CON GRACIA] Error cerrando {reporte.sucursal.nombre} ({reporte.fecha_contable}): {exc}"
                logger.error(error_msg)
                errores.append(error_msg)
        
        resumen = {
            "fecha_ejecucion": str(ahora),
            "ventana_gracia": f"{desde_hace_5_dias} a {hoy}",
            "horario_cierre": str(hora_cierre),
            "reportes_cerrados": reportes_cerrados,
            "errores": errores,
        }
        
        logger.info(f"[CIERRE AUTOMÁTICO CON GRACIA] Finalizado: {resumen}")
        return resumen
        
    except Exception as exc:
        logger.error(f"[CIERRE AUTOMÁTICO CON GRACIA] Error general: {exc}")
        raise self.retry(exc=exc, countdown=300)


# 1) Para qué sirve: enviar automáticamente el resumen diario ejecutivo por cada sucursal activa.
# 2) Cómo funciona: construye paquete por sucursal, toma destinatarios globales y envía con una conexión SMTP compartida.
# 3) Qué hace: materializa el envío diario sin requerir ejecución manual del comando.
# 4) Cómo editarla: permite filtro por casino con sucursal_id sin romper el envío masivo.
@shared_task(bind=True, name='reportes_diarios.enviar_resumen_diario_ejecutivo', max_retries=2)
def enviar_resumen_diario_ejecutivo(self, fecha_contable_iso=None, sucursal_id=None):
    from datetime import date

    from reportes_diarios.servicios_resumenes_correo import (
        construir_paquete_correo_resumen_diario_ejecutivo,
        enviar_paquete_correo,
        obtener_sucursales_objetivo,
    )

    if fecha_contable_iso:
        fecha_contable = date.fromisoformat(str(fecha_contable_iso))
    else:
        fecha_contable = timezone.localdate() - timezone.timedelta(days=1)

    filtro_sucursal_id = None
    if sucursal_id is not None and str(sucursal_id).strip() != '':
        filtro_sucursal_id = int(sucursal_id)

    sucursales_ids = [filtro_sucursal_id] if filtro_sucursal_id else None
    sucursales = obtener_sucursales_objetivo(sucursal_ids=sucursales_ids)
    if not sucursales:
        logger.info('[CORREO DIARIO] No hay sucursales activas para procesar.')
        return {
            'fecha_contable': str(fecha_contable),
            'sucursal_id_filtro': filtro_sucursal_id,
            'sucursales_procesadas': 0,
            'mensajes_enviados': 0,
            'sucursales_omitidas': 0,
            'adjuntos_generados_total': 0,
            'errores': [],
        }

    conexion = get_connection(fail_silently=False)
    mensajes_enviados = 0
    sucursales_omitidas = 0
    adjuntos_generados_total = 0
    errores = []

    for sucursal in sucursales:
        try:
            destinatarios = _resolver_destinatarios_correos_ejecutivos(sucursal)
            if not destinatarios:
                sucursales_omitidas += 1
                logger.warning(f"[CORREO DIARIO] {sucursal.nombre}: omitido por falta de destinatarios configurados.")
                continue

            paquete = construir_paquete_correo_resumen_diario_ejecutivo(
                sucursal=sucursal,
                fecha_contable=fecha_contable,
            )
            adjuntos_generados_total += len(paquete.get('adjuntos') or [])
            resultado = enviar_paquete_correo(
                paquete_correo=paquete,
                destinatarios=destinatarios,
                conexion=conexion,
            )
            mensajes_enviados += int(resultado.get('enviados') or 0)
            logger.info(f"[CORREO DIARIO] {sucursal.nombre}: enviado a {', '.join(destinatarios)}")
        except Exception as exc:
            texto_error = f"[CORREO DIARIO] Error en {sucursal.nombre}: {exc}"
            logger.error(texto_error)
            errores.append(texto_error)

    resumen = {
        'fecha_contable': str(fecha_contable),
        'sucursal_id_filtro': filtro_sucursal_id,
        'sucursales_procesadas': len(sucursales),
        'mensajes_enviados': mensajes_enviados,
        'sucursales_omitidas': sucursales_omitidas,
        'adjuntos_generados_total': int(adjuntos_generados_total),
        'errores': errores,
    }
    logger.info(f"[CORREO DIARIO] Finalizado: {resumen}")
    return resumen


# 1) Para qué sirve: enviar automáticamente el cierre mensual ejecutivo por sucursal.
# 2) Cómo funciona: determina periodo objetivo (mes anterior por defecto), construye paquetes y envía por SMTP.
# 3) Qué hace: automatiza el correo de cierre del 1er día de cada mes.
# 4) Cómo editarla: permite forzar periodo y filtrar un casino específico desde Centro de Control.
@shared_task(bind=True, name='reportes_diarios.enviar_cierre_mensual_ejecutivo', max_retries=2)
def enviar_cierre_mensual_ejecutivo(self, anio=None, mes=None, sucursal_id=None):
    from reportes_diarios.servicios_resumenes_correo import (
        construir_paquete_correo_cierre_mensual_ejecutivo,
        enviar_paquete_correo,
        obtener_periodo_mes_anterior,
        obtener_sucursales_objetivo,
    )

    if anio is None or mes is None:
        anio, mes = obtener_periodo_mes_anterior()

    filtro_sucursal_id = None
    if sucursal_id is not None and str(sucursal_id).strip() != '':
        filtro_sucursal_id = int(sucursal_id)

    sucursales_ids = [filtro_sucursal_id] if filtro_sucursal_id else None
    sucursales = obtener_sucursales_objetivo(sucursal_ids=sucursales_ids)
    if not sucursales:
        logger.info('[CORREO MENSUAL] No hay sucursales activas para procesar.')
        return {
            'periodo': f"{int(anio)}-{int(mes):02d}",
            'sucursal_id_filtro': filtro_sucursal_id,
            'sucursales_procesadas': 0,
            'mensajes_enviados': 0,
            'sucursales_omitidas': 0,
            'adjuntos_generados_total': 0,
            'errores': [],
        }

    conexion = get_connection(fail_silently=False)
    mensajes_enviados = 0
    sucursales_omitidas = 0
    adjuntos_generados_total = 0
    errores = []

    for sucursal in sucursales:
        try:
            destinatarios = _resolver_destinatarios_correos_ejecutivos(sucursal)
            if not destinatarios:
                sucursales_omitidas += 1
                logger.warning(f"[CORREO MENSUAL] {sucursal.nombre}: omitido por falta de destinatarios configurados.")
                continue

            paquete = construir_paquete_correo_cierre_mensual_ejecutivo(
                sucursal=sucursal,
                anio=int(anio),
                mes=int(mes),
            )
            adjuntos_generados_total += len(paquete.get('adjuntos') or [])
            resultado = enviar_paquete_correo(
                paquete_correo=paquete,
                destinatarios=destinatarios,
                conexion=conexion,
            )
            mensajes_enviados += int(resultado.get('enviados') or 0)
            logger.info(f"[CORREO MENSUAL] {sucursal.nombre}: enviado a {', '.join(destinatarios)}")
        except Exception as exc:
            texto_error = f"[CORREO MENSUAL] Error en {sucursal.nombre}: {exc}"
            logger.error(texto_error)
            errores.append(texto_error)

    resumen = {
        'periodo': f"{int(anio)}-{int(mes):02d}",
        'sucursal_id_filtro': filtro_sucursal_id,
        'sucursales_procesadas': len(sucursales),
        'mensajes_enviados': mensajes_enviados,
        'sucursales_omitidas': sucursales_omitidas,
        'adjuntos_generados_total': int(adjuntos_generados_total),
        'errores': errores,
    }
    logger.info(f"[CORREO MENSUAL] Finalizado: {resumen}")
    return resumen


# 1) Para que sirve: resolver ruta de bitacora diaria del respaldo BD dentro de una carpeta relativa.
# 2) Como funciona: crea carpeta objetivo y devuelve archivo por fecha (backup_bd_YYYYMMDD.log).
# 3) Que hace: centraliza una ruta estable para diagnosticar ejecuciones del respaldo.
# 4) Como editarla: cambia ruta_relativa o la constante RUTA_LOGS_RESPALDO_BD_RELATIVA en configuracion.
def _obtener_ruta_log_respaldo_bd(fecha_referencia=None, ruta_relativa=None):
    from django.conf import settings
    from reportes_diarios.configuracion_correos_ejecutivos import RUTA_LOGS_RESPALDO_BD_RELATIVA

    fecha_log = fecha_referencia or timezone.localtime(timezone.now())
    ruta_relativa_efectiva = str(ruta_relativa or RUTA_LOGS_RESPALDO_BD_RELATIVA or 'media/logs/backups_bd')
    carpeta_logs = Path(settings.BASE_DIR) / ruta_relativa_efectiva
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    return carpeta_logs / f"backup_bd_{fecha_log.strftime('%Y%m%d')}.log"


# 1) Para que sirve: obtener una ruta de bitacora usable aun con restricciones de permisos.
# 2) Como funciona: intenta ruta principal, luego fallback runtime y por ultimo carpeta temporal del sistema.
# 3) Que hace: evita que la tarea falle antes de iniciar por error al crear carpeta de logs.
# 4) Como editarla: ajusta el orden de rutas candidatas segun politicas del servidor.
def _resolver_ruta_log_respaldo_bd_segura(fecha_referencia=None):
    from reportes_diarios.configuracion_correos_ejecutivos import (
        RUTA_LOGS_RESPALDO_BD_FALLBACK_RELATIVA,
        RUTA_LOGS_RESPALDO_BD_RELATIVA,
    )

    fecha_log = fecha_referencia or timezone.localtime(timezone.now())
    rutas_candidatas = [
        str(RUTA_LOGS_RESPALDO_BD_RELATIVA or '').strip(),
        str(RUTA_LOGS_RESPALDO_BD_FALLBACK_RELATIVA or '').strip(),
    ]

    errores_ruta = []
    for ruta_relativa in rutas_candidatas:
        if not ruta_relativa:
            continue

        try:
            return _obtener_ruta_log_respaldo_bd(fecha_referencia=fecha_log, ruta_relativa=ruta_relativa)
        except Exception as exc:
            errores_ruta.append(f"{ruta_relativa}: {exc}")

    try:
        carpeta_temporal = Path(tempfile.gettempdir()) / 'binsurmx' / 'logs' / 'backups_bd'
        carpeta_temporal.mkdir(parents=True, exist_ok=True)
        return carpeta_temporal / f"backup_bd_{fecha_log.strftime('%Y%m%d')}.log"
    except Exception as exc:
        errores_ruta.append(f"tempfile: {exc}")

    logger.error(
        '[BACKUP BD] No fue posible resolver ruta de bitacora local. '
        f'Intentos fallidos: {" | ".join(errores_ruta)}'
    )
    return None


# 1) Para que sirve: serializar contexto tecnico para bitacora legible y consistente.
# 2) Como funciona: intenta JSON y cae a str si algun dato no es serializable.
# 3) Que hace: evita que un contexto complejo rompa escritura de logs.
# 4) Como editarla: agrega normalizacion extra si quieres ocultar campos sensibles.
def _serializar_contexto_bitacora(contexto):
    if not contexto:
        return ''

    try:
        return json.dumps(contexto, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(contexto)


# 1) Para que sirve: persistir eventos tecnicos del respaldo BD aunque el logger global falle.
# 2) Como funciona: escribe en archivo de bitacora con marca de tiempo, contexto y traza opcional.
# 3) Que hace: permite ver etapa exacta y error real cuando el respaldo falla silenciosamente.
# 4) Como editarla: usa otro formato de salida si necesitas integracion con SIEM.
def _registrar_bitacora_respaldo_bd(ruta_log, nivel, evento, contexto=None, excepcion=None):
    nivel_texto = str(nivel or 'INFO').strip().upper()
    evento_texto = str(evento or 'EVENTO').strip()
    marca_tiempo = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
    texto_contexto = _serializar_contexto_bitacora(contexto)

    try:
        if ruta_log is None:
            raise RuntimeError('Ruta de bitacora local no disponible.')

        lineas = [f"{marca_tiempo} | {nivel_texto} | {evento_texto}"]
        if texto_contexto:
            lineas.append(f"Contexto: {texto_contexto}")

        if excepcion is not None:
            lineas.append(f"Excepcion: {type(excepcion).__name__}: {excepcion}")
            traza = ''.join(traceback.format_exception(type(excepcion), excepcion, excepcion.__traceback__))
            if traza:
                lineas.append('Traza:')
                lineas.append(traza.rstrip())

        lineas.append('-' * 120)
        contenido = '\n'.join(lineas) + '\n'

        ruta_destino = Path(ruta_log)
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        with ruta_destino.open('a', encoding='utf-8') as archivo_log:
            archivo_log.write(contenido)

    except Exception as exc_escritura:
        logger.error(f"[BACKUP BD] Error al escribir bitacora local ({evento_texto}): {exc_escritura}")

    texto_logger = f"[BACKUP BD][{str(evento or '').strip()}] {_serializar_contexto_bitacora(contexto) or 'sin_contexto'}"
    if nivel_texto == 'ERROR':
        logger.error(texto_logger)
    elif nivel_texto == 'WARNING':
        logger.warning(texto_logger)
    else:
        logger.info(texto_logger)


# 1) Para que sirve: localizar ejecutable mysqldump disponible en servidor Windows.
# 2) Como funciona: prioriza variable MYSQLDUMP_PATH y despues rutas conocidas.
# 3) Que hace: evita fallos por diferencia de instalacion entre entornos.
# 4) Como editarla: agrega nuevas rutas si cambias distribucion de MySQL.
def _resolver_ruta_mysqldump():
    ruta_preferida = os.getenv('MYSQLDUMP_PATH')
    if ruta_preferida:
        ruta_normalizada = Path(ruta_preferida)
        if ruta_normalizada.exists():
            return str(ruta_normalizada)

    comando_en_path = shutil.which('mysqldump')
    if comando_en_path:
        return str(comando_en_path)

    rutas_candidatas = [
        Path('C:/xampp/mysql/bin/mysqldump.exe'),
        Path('C:/Program Files/MySQL/MySQL Server 8.1/bin/mysqldump.exe'),
        Path('C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'),
        Path('C:/Program Files/MySQL/MySQL Server 8.4/bin/mysqldump.exe'),
        Path('C:/Program Files (x86)/MySQL/MySQL Server 8.1/bin/mysqldump.exe'),
        Path('C:/Program Files (x86)/MySQL/MySQL Server 8.0/bin/mysqldump.exe'),
    ]

    bases_mysql = [
        Path('C:/Program Files/MySQL'),
        Path('C:/Program Files (x86)/MySQL'),
    ]
    for base_mysql in bases_mysql:
        if base_mysql.exists():
            rutas_candidatas.extend(base_mysql.glob('MySQL Server */bin/mysqldump.exe'))

    rutas_vistas = set()
    for ruta_candidata in rutas_candidatas:
        clave_ruta = str(ruta_candidata).lower().strip()
        if not clave_ruta or clave_ruta in rutas_vistas:
            continue

        rutas_vistas.add(clave_ruta)
        if ruta_candidata.exists():
            return str(ruta_candidata)

    return None


# 1) Para que sirve: obtener destinatarios del correo de respaldo con fallback seguro.
# 2) Como funciona: intenta DESTINATARIOS_RESPALDO_BD y cae a DESTINATARIOS_CORREOS.
# 3) Que hace: permite notificar respaldo a correo personal sin romper configuracion existente.
# 4) Como editarla: cambia claves en configuracion_correos_ejecutivos.py.
def _resolver_destinatarios_respaldo_bd():
    from django.conf import settings
    from reportes_diarios.configuracion_correos_ejecutivos import (
        CLAVE_CONFIG_DESTINATARIOS_CORREOS,
        CLAVE_CONFIG_DESTINATARIOS_RESPALDO_BD,
    )

    claves_respaldo = [
        str(CLAVE_CONFIG_DESTINATARIOS_RESPALDO_BD or '').strip(),
        'DESTINATARIOS_RESPALDO_BD',
        'DESTINATARIO_BACKUP',
    ]

    destinatarios = []
    for clave_respaldo in claves_respaldo:
        if not clave_respaldo:
            continue
        destinatarios = _obtener_destinatarios_globales_configurados_local(clave_respaldo)
        if destinatarios:
            break

    if not destinatarios:
        destinatarios = _obtener_destinatarios_globales_configurados_local(CLAVE_CONFIG_DESTINATARIOS_CORREOS)

    if not destinatarios:
        correo_fallback = str(
            getattr(settings, 'EMAIL_HOST_USER', '')
            or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
            or ''
        ).strip()
        if correo_fallback and '@' in correo_fallback:
            destinatarios = [correo_fallback]

    return _normalizar_destinatarios_local(destinatarios)


# 1) Para que sirve: comprimir el .sql de respaldo para reducir peso de adjunto.
# 2) Como funciona: soporta compresion gzip (.gz) o zip (.zip).
# 3) Que hace: genera un archivo comprimido listo para envio por correo.
# 4) Como editarla: cambia formato por default en configuracion, no en esta funcion.
def _comprimir_respaldo_sql(ruta_sql, formato_compresion):
    formato = str(formato_compresion or 'gz').strip().lower()
    if formato not in {'gz', 'zip'}:
        raise ValueError(f'Formato de compresion no soportado: {formato}. Usa gz o zip.')

    if formato == 'gz':
        ruta_comprimida = Path(f'{ruta_sql}.gz')
        with ruta_sql.open('rb') as origen, gzip.open(ruta_comprimida, 'wb', compresslevel=9) as destino:
            shutil.copyfileobj(origen, destino)
        return ruta_comprimida

    ruta_comprimida = Path(f'{ruta_sql}.zip')
    with zipfile.ZipFile(ruta_comprimida, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archivo_zip:
        archivo_zip.write(ruta_sql, arcname=ruta_sql.name)
    return ruta_comprimida


# 1) Para que sirve: enviar notificacion de respaldo usando SMTP configurado en Django.
# 2) Como funciona: construye EmailMessage y adjunta archivo comprimido cuando aplica.
# 3) Que hace: confirma al operador exito o fallo de respaldo diario.
# 4) Como editarla: personaliza remitente/asunto/cuerpo sin tocar flujo principal.
def _enviar_correo_respaldo_bd(destinatarios, asunto, cuerpo, ruta_adjunto=None):
    from django.conf import settings

    remitente = str(
        getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        or getattr(settings, 'EMAIL_HOST_USER', '')
        or 'no-responder@binsur.mx'
    )
    correo = EmailMessage(
        subject=str(asunto),
        body=str(cuerpo),
        from_email=remitente,
        to=list(destinatarios or []),
    )

    if ruta_adjunto and Path(ruta_adjunto).exists():
        correo.attach_file(str(ruta_adjunto))

    enviados = int(correo.send(fail_silently=False) or 0)
    return enviados


# 1) Para que sirve: limpiar respaldos viejos para controlar crecimiento de disco.
# 2) Como funciona: elimina archivos .sql con antiguedad mayor a retencion_dias.
# 3) Que hace: conserva solo ventana reciente de backups completos.
# 4) Como editarla: cambia patron o metrica de antiguedad si se comprime a zip.
def _limpiar_respaldos_antiguos(carpeta_respaldos, retencion_dias):
    if int(retencion_dias) <= 0:
        return 0

    ahora = timezone.localtime(timezone.now())
    eliminados = 0

    patrones = ('backup_*.sql', 'backup_*.sql.gz', 'backup_*.sql.zip')
    archivos_candidatos = set()
    for patron in patrones:
        archivos_candidatos.update(carpeta_respaldos.glob(patron))

    for archivo in archivos_candidatos:
        modificado = timezone.make_aware(datetime.fromtimestamp(archivo.stat().st_mtime), timezone.get_current_timezone())
        antiguedad = (ahora - modificado).days
        if antiguedad > int(retencion_dias):
            archivo.unlink(missing_ok=True)
            eliminados += 1

    return eliminados


# 1) Para que sirve: generar respaldo completo diario de la base de datos MySQL.
# 2) Como funciona: ejecuta mysqldump con credenciales de settings y guarda archivo .sql.
# 3) Que hace: asegura punto de recuperacion diario para contingencias operativas.
# 4) Como editarla: agrega compresion/replicacion externa si se requiere DR avanzado.
@shared_task(bind=True, name='reportes_diarios.ejecutar_backup_bd', max_retries=1)
def ejecutar_backup_bd(self):
    from django.conf import settings
    from reportes_diarios.configuracion_correos_ejecutivos import (
        ASUNTO_CORREO_RESPALDO_BD_EXITO,
        ASUNTO_CORREO_RESPALDO_BD_FALLO,
        FORMATO_COMPRESION_RESPALDO_BD,
        LIMITE_ADJUNTO_CORREO_RESPALDO_BD_BYTES,
        RETENCION_DIAS_RESPALDO_BD,
        RUTA_LOGS_RESPALDO_BD_FALLBACK_RELATIVA,
        RUTA_LOGS_RESPALDO_BD_RELATIVA,
        RUTA_RESPALDOS_BD_RELATIVA,
    )

    fecha_ejecucion = timezone.localtime(timezone.now())
    ruta_log_backup = None
    id_tarea = str(getattr(getattr(self, 'request', None), 'id', '') or '')
    destinatarios = _resolver_destinatarios_respaldo_bd()
    enviados_correo = 0
    etapa_actual = 'inicio'

    try:
        etapa_actual = 'resolver_bitacora_local'
        ruta_log_backup = _resolver_ruta_log_respaldo_bd_segura(fecha_ejecucion)
        if not ruta_log_backup:
            logger.warning(
                '[BACKUP BD] Sin ruta de bitacora local disponible. '
                'Se mantiene trazabilidad en logger del worker.'
            )

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='INICIO_RESPALDO_BD',
            contexto={
                'task_id': id_tarea,
                'fecha_ejecucion': fecha_ejecucion.isoformat(),
                'destinatarios': destinatarios,
                'ruta_bitacora_principal': str(RUTA_LOGS_RESPALDO_BD_RELATIVA),
                'ruta_bitacora_fallback': str(RUTA_LOGS_RESPALDO_BD_FALLBACK_RELATIVA),
                'ruta_bitacora_resuelta': str(ruta_log_backup or ''),
            },
        )

        etapa_actual = 'leer_configuracion_bd'
        configuracion_db = settings.DATABASES.get('default', {})
        engine = str(configuracion_db.get('ENGINE') or '')
        if 'mysql' not in engine:
            raise RuntimeError(f'Engine no soportado para respaldo automatico ({engine}).')

        etapa_actual = 'resolver_mysqldump'
        ruta_mysqldump = _resolver_ruta_mysqldump()
        if not ruta_mysqldump:
            raise RuntimeError('No se encontro mysqldump. Define MYSQLDUMP_PATH en entorno del servidor.')

        carpeta_respaldos = Path(settings.BASE_DIR) / str(RUTA_RESPALDOS_BD_RELATIVA)
        carpeta_respaldos.mkdir(parents=True, exist_ok=True)

        marca_tiempo = fecha_ejecucion.strftime('%Y%m%d_%H%M%S')
        nombre_bd = str(configuracion_db.get('NAME') or 'base_datos')
        nombre_archivo = f'backup_{nombre_bd}_{marca_tiempo}.sql'
        ruta_archivo_sql = carpeta_respaldos / nombre_archivo

        host = str(configuracion_db.get('HOST') or '127.0.0.1')
        puerto = str(configuracion_db.get('PORT') or '3306')
        usuario = str(configuracion_db.get('USER') or '')
        password = str(configuracion_db.get('PASSWORD') or '')

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='CONFIGURACION_RESPALDO_VALIDADA',
            contexto={
                'task_id': id_tarea,
                'engine': engine,
                'host': host,
                'puerto': puerto,
                'usuario': usuario,
                'base_datos': nombre_bd,
                'ruta_mysqldump': ruta_mysqldump,
                'archivo_sql_temporal': str(ruta_archivo_sql),
            },
        )

        comando = [
            ruta_mysqldump,
            f'--host={host}',
            f'--port={puerto}',
            f'--user={usuario}',
            '--single-transaction',
            '--skip-lock-tables',
            '--routines',
            '--triggers',
            nombre_bd,
        ]

        entorno = os.environ.copy()
        if password:
            entorno['MYSQL_PWD'] = password

        try:
            etapa_actual = 'ejecutar_mysqldump'
            _registrar_bitacora_respaldo_bd(
                ruta_log=ruta_log_backup,
                nivel='INFO',
                evento='EJECUTANDO_MYSQLDUMP',
                contexto={
                    'task_id': id_tarea,
                    'comando': comando,
                },
            )

            with ruta_archivo_sql.open('wb') as flujo_salida:
                subprocess.run(
                    comando,
                    env=entorno,
                    stdout=flujo_salida,
                    stderr=subprocess.PIPE,
                    check=True,
                )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b'').decode('utf-8', errors='ignore')
            raise RuntimeError(f'Error en mysqldump: {stderr}') from exc

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='MYSQLDUMP_FINALIZADO',
            contexto={
                'task_id': id_tarea,
                'archivo_sql_temporal': str(ruta_archivo_sql),
                'bytes_sql': int(ruta_archivo_sql.stat().st_size if ruta_archivo_sql.exists() else 0),
            },
        )

        etapa_actual = 'comprimir_respaldo'
        ruta_archivo_comprimido = _comprimir_respaldo_sql(ruta_archivo_sql, FORMATO_COMPRESION_RESPALDO_BD)
        ruta_archivo_sql.unlink(missing_ok=True)

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='RESPALDO_COMPRIMIDO',
            contexto={
                'task_id': id_tarea,
                'archivo_comprimido': str(ruta_archivo_comprimido),
                'bytes_comprimido': int(ruta_archivo_comprimido.stat().st_size if ruta_archivo_comprimido.exists() else 0),
                'formato_compresion': str(FORMATO_COMPRESION_RESPALDO_BD),
            },
        )

        etapa_actual = 'limpieza_retencion'
        eliminados = _limpiar_respaldos_antiguos(carpeta_respaldos, RETENCION_DIAS_RESPALDO_BD)
        tamanio_bytes = ruta_archivo_comprimido.stat().st_size if ruta_archivo_comprimido.exists() else 0
        adjuntar_respaldo = int(tamanio_bytes) <= int(LIMITE_ADJUNTO_CORREO_RESPALDO_BD_BYTES)
        tamano_mb = float(tamanio_bytes) / (1024 * 1024) if tamanio_bytes else 0

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='RESPALDO_LISTO_PARA_NOTIFICAR',
            contexto={
                'task_id': id_tarea,
                'archivo_comprimido': str(ruta_archivo_comprimido),
                'tamano_mb': f'{tamano_mb:.2f}',
                'adjuntar_respaldo': bool(adjuntar_respaldo),
                'respaldos_eliminados': int(eliminados),
            },
        )

        cuerpo_exito = (
            'Respaldo automatico de base de datos ejecutado correctamente.\n\n'
            f'Fecha: {fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'Base de datos: {nombre_bd}\n'
            f'Archivo comprimido: {ruta_archivo_comprimido}\n'
            f'Tamano: {tamano_mb:.2f} MB\n'
            f'Adjunto incluido: {"SI" if adjuntar_respaldo else "NO (supera 25 MB)"}\n'
            f'Respaldos antiguos eliminados: {int(eliminados)}\n'
        )

        if destinatarios:
            etapa_actual = 'enviar_correo_exito'
            fecha_formato = fecha_ejecucion.strftime('%d/%m/%Y')
            asunto_con_fecha = f"{ASUNTO_CORREO_RESPALDO_BD_EXITO} - {fecha_formato}"
            enviados_correo = _enviar_correo_respaldo_bd(
                destinatarios=destinatarios,
                asunto=asunto_con_fecha,
                cuerpo=cuerpo_exito,
                ruta_adjunto=ruta_archivo_comprimido if adjuntar_respaldo else None,
            )
            _registrar_bitacora_respaldo_bd(
                ruta_log=ruta_log_backup,
                nivel='INFO',
                evento='CORREO_RESPALDO_ENVIADO',
                contexto={
                    'task_id': id_tarea,
                    'destinatarios': destinatarios,
                    'mensajes_enviados': int(enviados_correo),
                },
            )
        else:
            _registrar_bitacora_respaldo_bd(
                ruta_log=ruta_log_backup,
                nivel='WARNING',
                evento='RESPALDO_SIN_DESTINATARIOS',
                contexto={
                    'task_id': id_tarea,
                    'archivo_comprimido': str(ruta_archivo_comprimido),
                    'motivo': 'No hay destinatarios configurados ni fallback SMTP disponible.',
                },
            )

        resumen = {
            'status': 'ok',
            'archivo_respaldo': str(ruta_archivo_comprimido),
            'archivo_log': str(ruta_log_backup or ''),
            'bitacora_local_activa': bool(ruta_log_backup),
            'bytes': int(tamanio_bytes),
            'adjunto_enviado': bool(adjuntar_respaldo),
            'correo_enviado': bool(enviados_correo),
            'destinatarios': destinatarios,
            'respaldos_eliminados': int(eliminados),
        }
        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='INFO',
            evento='RESPALDO_FINALIZADO_OK',
            contexto=resumen,
        )
        return resumen

    except Exception as exc:
        texto_error = str(exc)

        _registrar_bitacora_respaldo_bd(
            ruta_log=ruta_log_backup,
            nivel='ERROR',
            evento='RESPALDO_FINALIZADO_CON_ERROR',
            contexto={
                'task_id': id_tarea,
                'etapa_actual': etapa_actual,
                'destinatarios': destinatarios,
            },
            excepcion=exc,
        )

        if destinatarios:
            try:
                etapa_actual = 'enviar_correo_fallo'
                referencia_bitacora = str(ruta_log_backup or 'SIN_BITACORA_LOCAL')
                cuerpo_fallo = (
                    'ALERTA: el respaldo automatico de base de datos fallo.\n\n'
                    f'Fecha: {fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S")}\n'
                    f'Error: {texto_error}\n'
                    f'Bitacora tecnica: {referencia_bitacora}\n'
                    'Accion requerida: revisar logs de Celery Worker y conectividad de BD/SMTP.\n'
                )
                fecha_formato = fecha_ejecucion.strftime('%d/%m/%Y')
                asunto_con_fecha = f"{ASUNTO_CORREO_RESPALDO_BD_FALLO} - {fecha_formato}"
                _enviar_correo_respaldo_bd(
                    destinatarios=destinatarios,
                    asunto=asunto_con_fecha,
                    cuerpo=cuerpo_fallo,
                    ruta_adjunto=None,
                )
                _registrar_bitacora_respaldo_bd(
                    ruta_log=ruta_log_backup,
                    nivel='INFO',
                    evento='CORREO_ALERTA_FALLO_ENVIADO',
                    contexto={
                        'task_id': id_tarea,
                        'destinatarios': destinatarios,
                    },
                )
            except Exception as exc_correo:
                _registrar_bitacora_respaldo_bd(
                    ruta_log=ruta_log_backup,
                    nivel='ERROR',
                    evento='FALLO_CORREO_ALERTA_RESPALDO',
                    contexto={
                        'task_id': id_tarea,
                        'etapa_actual': etapa_actual,
                        'destinatarios': destinatarios,
                    },
                    excepcion=exc_correo,
                )

        raise RuntimeError(
            f'Fallo en respaldo automatico de BD: {texto_error}. '
            f'Revisa bitacora: {str(ruta_log_backup or "SIN_BITACORA_LOCAL")}'
        ) from exc
