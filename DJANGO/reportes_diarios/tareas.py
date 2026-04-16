"""
Tareas asíncronas de Celery para el módulo reportes_diarios.
La tarea principal es el cierre automático del día contable al alcanzar la hora_cierre
configurada en ConfiguracionGlobal.
"""
import logging
import os
import shutil
import subprocess
from datetime import datetime
from celery import shared_task
from django.core.mail import get_connection
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
def _resolver_destinatarios_correos_ejecutivos(sucursal):
    from reportes_diarios.configuracion_correos_ejecutivos import (
        CLAVE_CONFIG_DESTINATARIOS_CORREOS,
        INCLUIR_CORREO_SUCURSAL_EN_ENVIO,
    )
    from reportes_diarios.servicios_resumenes_correo import (
        normalizar_destinatarios,
        obtener_destinatarios_globales_configurados,
    )

    destinatarios = obtener_destinatarios_globales_configurados(CLAVE_CONFIG_DESTINATARIOS_CORREOS)
    if INCLUIR_CORREO_SUCURSAL_EN_ENVIO and getattr(sucursal, 'correo', None):
        destinatarios.append(sucursal.correo)

    return normalizar_destinatarios(destinatarios)


# 1) Para qué sirve: enviar automáticamente el resumen diario ejecutivo por cada sucursal activa.
# 2) Cómo funciona: construye paquete por sucursal, toma destinatarios globales y envía con una conexión SMTP compartida.
# 3) Qué hace: materializa el envío diario sin requerir ejecución manual del comando.
# 4) Cómo editarla: ajusta filtros de sucursal o payload de tarea manteniendo esta rutina idempotente.
@shared_task(bind=True, name='reportes_diarios.enviar_resumen_diario_ejecutivo', max_retries=2)
def enviar_resumen_diario_ejecutivo(self, fecha_contable_iso=None):
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

    sucursales = obtener_sucursales_objetivo()
    if not sucursales:
        logger.info('[CORREO DIARIO] No hay sucursales activas para procesar.')
        return {
            'fecha_contable': str(fecha_contable),
            'sucursales_procesadas': 0,
            'mensajes_enviados': 0,
            'sucursales_omitidas': 0,
            'errores': [],
        }

    conexion = get_connection(fail_silently=False)
    mensajes_enviados = 0
    sucursales_omitidas = 0
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
        'sucursales_procesadas': len(sucursales),
        'mensajes_enviados': mensajes_enviados,
        'sucursales_omitidas': sucursales_omitidas,
        'errores': errores,
    }
    logger.info(f"[CORREO DIARIO] Finalizado: {resumen}")
    return resumen


# 1) Para qué sirve: enviar automáticamente el cierre mensual ejecutivo por sucursal.
# 2) Cómo funciona: determina periodo objetivo (mes anterior por defecto), construye paquetes y envía por SMTP.
# 3) Qué hace: automatiza el correo de cierre del 1er día de cada mes.
# 4) Cómo editarla: permite forzar periodo con anio/mes al ejecutar la tarea manualmente.
@shared_task(bind=True, name='reportes_diarios.enviar_cierre_mensual_ejecutivo', max_retries=2)
def enviar_cierre_mensual_ejecutivo(self, anio=None, mes=None):
    from reportes_diarios.servicios_resumenes_correo import (
        construir_paquete_correo_cierre_mensual_ejecutivo,
        enviar_paquete_correo,
        obtener_periodo_mes_anterior,
        obtener_sucursales_objetivo,
    )

    if anio is None or mes is None:
        anio, mes = obtener_periodo_mes_anterior()

    sucursales = obtener_sucursales_objetivo()
    if not sucursales:
        logger.info('[CORREO MENSUAL] No hay sucursales activas para procesar.')
        return {
            'periodo': f"{int(anio)}-{int(mes):02d}",
            'sucursales_procesadas': 0,
            'mensajes_enviados': 0,
            'sucursales_omitidas': 0,
            'errores': [],
        }

    conexion = get_connection(fail_silently=False)
    mensajes_enviados = 0
    sucursales_omitidas = 0
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
        'sucursales_procesadas': len(sucursales),
        'mensajes_enviados': mensajes_enviados,
        'sucursales_omitidas': sucursales_omitidas,
        'errores': errores,
    }
    logger.info(f"[CORREO MENSUAL] Finalizado: {resumen}")
    return resumen


# 1) Para que sirve: refrescar diariamente el horario de envio diario leyendo HORARIO_CIERRE en BD.
# 2) Como funciona: reusa el comando de sincronizacion de disparadores con update idempotente.
# 3) Que hace: evita que el envio diario quede con una hora vieja despues de cambiar configuracion global.
# 4) Como editarla: agrega parametros al call_command si necesitas variantes por entorno.
@shared_task(bind=True, name='reportes_diarios.sincronizar_horario_correo_diario', max_retries=1)
def sincronizar_horario_correo_diario(self):
    try:
        call_command('sincronizar_disparadores_correos_ejecutivos')
        mensaje = 'Sincronizacion de horario diario completada desde HORARIO_CIERRE.'
        logger.info(f"[SYNC HORARIO CORREO] {mensaje}")
        return {'status': 'ok', 'mensaje': mensaje}
    except Exception as exc:
        texto_error = f'Sincronizacion de horario diario fallida: {exc}'
        logger.error(f"[SYNC HORARIO CORREO] {texto_error}")
        raise


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
        Path('C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe'),
    ]
    for ruta_candidata in rutas_candidatas:
        if ruta_candidata.exists():
            return str(ruta_candidata)

    return None


# 1) Para que sirve: limpiar respaldos viejos para controlar crecimiento de disco.
# 2) Como funciona: elimina archivos .sql con antiguedad mayor a retencion_dias.
# 3) Que hace: conserva solo ventana reciente de backups completos.
# 4) Como editarla: cambia patron o metrica de antiguedad si se comprime a zip.
def _limpiar_respaldos_antiguos(carpeta_respaldos, retencion_dias):
    if int(retencion_dias) <= 0:
        return 0

    ahora = timezone.localtime(timezone.now())
    eliminados = 0

    for archivo in carpeta_respaldos.glob('backup_*.sql'):
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
        RETENCION_DIAS_RESPALDO_BD,
        RUTA_RESPALDOS_BD_RELATIVA,
    )

    configuracion_db = settings.DATABASES.get('default', {})
    engine = str(configuracion_db.get('ENGINE') or '')
    if 'mysql' not in engine:
        mensaje = f'Backup omitido: engine no soportado para esta tarea ({engine}).'
        logger.warning(f"[BACKUP BD] {mensaje}")
        return {'status': 'omitido', 'mensaje': mensaje}

    ruta_mysqldump = _resolver_ruta_mysqldump()
    if not ruta_mysqldump:
        raise RuntimeError('No se encontro mysqldump. Define MYSQLDUMP_PATH en entorno del servidor.')

    carpeta_respaldos = Path(settings.BASE_DIR) / str(RUTA_RESPALDOS_BD_RELATIVA)
    carpeta_respaldos.mkdir(parents=True, exist_ok=True)

    marca_tiempo = timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')
    nombre_bd = str(configuracion_db.get('NAME') or 'base_datos')
    nombre_archivo = f'backup_{nombre_bd}_{marca_tiempo}.sql'
    ruta_archivo = carpeta_respaldos / nombre_archivo

    host = str(configuracion_db.get('HOST') or '127.0.0.1')
    puerto = str(configuracion_db.get('PORT') or '3306')
    usuario = str(configuracion_db.get('USER') or '')
    password = str(configuracion_db.get('PASSWORD') or '')

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
        with ruta_archivo.open('wb') as flujo_salida:
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

    eliminados = _limpiar_respaldos_antiguos(carpeta_respaldos, RETENCION_DIAS_RESPALDO_BD)
    tamanio_bytes = ruta_archivo.stat().st_size if ruta_archivo.exists() else 0

    resumen = {
        'status': 'ok',
        'archivo': str(ruta_archivo),
        'bytes': int(tamanio_bytes),
        'respaldos_eliminados': int(eliminados),
    }
    logger.info(f"[BACKUP BD] Respaldo generado: {resumen}")
    return resumen
