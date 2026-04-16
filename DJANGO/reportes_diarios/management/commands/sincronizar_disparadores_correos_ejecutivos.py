import json
from datetime import time as time_cls

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from configuraciones_globales.models import ConfiguracionGlobal

from reportes_diarios.configuracion_correos_ejecutivos import (
    CLAVE_CONFIG_HORARIO_CIERRE,
    CRON_DIARIO_DIA_MES,
    CRON_DIARIO_DIA_SEMANA,
    CRON_DIARIO_HORA,
    CRON_DIARIO_MES,
    CRON_DIARIO_MINUTO,
    CRON_MENSUAL_DIA_MES,
    CRON_MENSUAL_DIA_SEMANA,
    CRON_MENSUAL_HORA,
    CRON_MENSUAL_MES,
    CRON_MENSUAL_MINUTO,
    CRON_RESPALDO_BD_DIA_MES,
    CRON_RESPALDO_BD_DIA_SEMANA,
    CRON_RESPALDO_BD_HORA,
    CRON_RESPALDO_BD_MES,
    CRON_RESPALDO_BD_MINUTO,
    CRON_SINCRONIZAR_HORARIO_DIA_MES,
    CRON_SINCRONIZAR_HORARIO_DIA_SEMANA,
    CRON_SINCRONIZAR_HORARIO_HORA,
    CRON_SINCRONIZAR_HORARIO_MES,
    CRON_SINCRONIZAR_HORARIO_MINUTO,
    HABILITAR_DISPARADOR_DIARIO,
    HABILITAR_DISPARADOR_MENSUAL,
    HABILITAR_DISPARADOR_RESPALDO_BD,
    HABILITAR_DISPARADOR_SINCRONIZAR_HORARIO_DIARIO,
    NOMBRE_PERIODIC_TASK_DIARIO,
    NOMBRE_PERIODIC_TASK_MENSUAL,
    NOMBRE_PERIODIC_TASK_RESPALDO_BD,
    NOMBRE_PERIODIC_TASK_SINCRONIZAR_HORARIO_DIARIO,
    NOMBRE_TAREA_CORREO_DIARIO,
    NOMBRE_TAREA_CORREO_MENSUAL,
    NOMBRE_TAREA_RESPALDO_BD,
    NOMBRE_TAREA_SINCRONIZAR_HORARIO_DIARIO,
    ZONA_HORARIA_CRON,
)


# 1) Para que sirve: crear/obtener un crontab reutilizable en django_celery_beat.
# 2) Como funciona: usa get_or_create con campos cron y zona horaria.
# 3) Que hace: evita duplicar schedules al sincronizar multiples veces.
# 4) Como editarla: agrega parametros extra aqui si tu scheduler lo requiere.
def _obtener_crontab(minuto, hora, dia_semana, dia_mes, mes, zona_horaria):
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=str(minuto),
        hour=str(hora),
        day_of_week=str(dia_semana),
        day_of_month=str(dia_mes),
        month_of_year=str(mes),
        timezone=str(zona_horaria),
    )
    return crontab


# 1) Para que sirve: crear o actualizar un PeriodicTask de forma idempotente.
# 2) Como funciona: update_or_create por nombre con tarea, cron, estado y descripcion.
# 3) Que hace: deja los disparadores listos sin intervencion manual en admin.
# 4) Como editarla: anade queue/options en defaults si segmentas workers en el futuro.
def _sincronizar_periodic_task(nombre, tarea, crontab, habilitado, descripcion, args=None):
    defaults = {
        'task': str(tarea),
        'crontab': crontab,
        'enabled': bool(habilitado),
        'description': str(descripcion),
        'args': json.dumps(args or []),
    }
    periodic_task, creado = PeriodicTask.objects.update_or_create(name=str(nombre), defaults=defaults)
    return periodic_task, creado


# 1) Para que sirve: convertir el valor de HORARIO_CIERRE a hora/minuto de cron.
# 2) Como funciona: soporta datetime.time y texto HH:MM o HH:MM:SS.
# 3) Que hace: permite programar el envio diario segun configuracion global en BD.
# 4) Como editarla: agrega formatos extra solo si se estandarizan oficialmente.
def _extraer_hora_minuto_desde_valor(valor):
    if isinstance(valor, time_cls):
        return int(valor.hour), int(valor.minute)

    texto = str(valor or '').strip()
    if not texto:
        return None

    partes = texto.split(':')
    if len(partes) < 2:
        return None

    try:
        hora = int(partes[0])
        minuto = int(partes[1])
    except (TypeError, ValueError):
        return None

    if hora < 0 or hora > 23:
        return None
    if minuto < 0 or minuto > 59:
        return None

    return hora, minuto


# 1) Para que sirve: obtener horario cierre real desde tabla configuraciones_globales.
# 2) Como funciona: busca la clave HORARIO_CIERRE y convierte su valor a hora/minuto.
# 3) Que hace: habilita programacion diaria dinamica segun configuracion de negocio.
# 4) Como editarla: cambia la clave consultada en configuracion_correos_ejecutivos.py.
def _obtener_hora_minuto_horario_cierre():
    configuracion = ConfiguracionGlobal.objects.filter(clave=CLAVE_CONFIG_HORARIO_CIERRE).first()
    if not configuracion:
        return None, 'No se encontro HORARIO_CIERRE en configuraciones_globales.'

    valor_convertido = _extraer_hora_minuto_desde_valor(configuracion.valor_tipado)
    if valor_convertido:
        return valor_convertido, f'HORARIO_CIERRE={configuracion.valor}'

    valor_crudo = _extraer_hora_minuto_desde_valor(configuracion.valor)
    if valor_crudo:
        return valor_crudo, f'HORARIO_CIERRE={configuracion.valor}'

    return None, f'No se pudo interpretar HORARIO_CIERRE={configuracion.valor}'


class Command(BaseCommand):
    help = (
        'Sincroniza disparadores de Celery Beat para correos ejecutivos diario y mensual '
        'usando la configuracion de reportes_diarios/configuracion_correos_ejecutivos.py.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--deshabilitar-diario',
            action='store_true',
            help='Fuerza deshabilitar el disparador diario en esta ejecucion.',
        )
        parser.add_argument(
            '--deshabilitar-mensual',
            action='store_true',
            help='Fuerza deshabilitar el disparador mensual en esta ejecucion.',
        )
        parser.add_argument(
            '--deshabilitar-respaldo-bd',
            action='store_true',
            help='Fuerza deshabilitar el disparador de backup diario de base de datos.',
        )
        parser.add_argument(
            '--deshabilitar-sincronizacion-horario',
            action='store_true',
            help='Fuerza deshabilitar la tarea diaria que refresca horario desde HORARIO_CIERRE.',
        )
        parser.add_argument(
            '--ignorar-horario-cierre',
            action='store_true',
            help='No usar HORARIO_CIERRE y mantener el horario diario fijo del archivo de configuracion.',
        )

    # 1) Para que sirve: dejar configurados en BD los disparadores de correos ejecutivos.
    # 2) Como funciona: lee archivo de configuracion y hace upsert de dos PeriodicTask.
    # 3) Que hace: materializa la programacion de Celery Beat de forma repetible.
    # 4) Como editarla: si agregas mas disparadores, replica el mismo patron de sincronia.
    def handle(self, *args, **options):
        habilitar_diario = bool(HABILITAR_DISPARADOR_DIARIO) and not bool(options.get('deshabilitar_diario'))
        habilitar_mensual = bool(HABILITAR_DISPARADOR_MENSUAL) and not bool(options.get('deshabilitar_mensual'))
        habilitar_respaldo_bd = bool(HABILITAR_DISPARADOR_RESPALDO_BD) and not bool(options.get('deshabilitar_respaldo_bd'))
        habilitar_sincronizacion_horario = bool(HABILITAR_DISPARADOR_SINCRONIZAR_HORARIO_DIARIO) and not bool(options.get('deshabilitar_sincronizacion_horario'))

        hora_diario = str(CRON_DIARIO_HORA).zfill(2)
        minuto_diario = str(CRON_DIARIO_MINUTO).zfill(2)
        origen_horario_diario = 'fallback del archivo de configuracion'

        if not bool(options.get('ignorar_horario_cierre')):
            horario_desde_bd, detalle = _obtener_hora_minuto_horario_cierre()
            if horario_desde_bd:
                hora_diario = str(horario_desde_bd[0]).zfill(2)
                minuto_diario = str(horario_desde_bd[1]).zfill(2)
                origen_horario_diario = detalle
            else:
                origen_horario_diario = f'{detalle} | Se usa fallback {hora_diario}:{minuto_diario}'

        crontab_diario = _obtener_crontab(
            minuto=minuto_diario,
            hora=hora_diario,
            dia_semana=CRON_DIARIO_DIA_SEMANA,
            dia_mes=CRON_DIARIO_DIA_MES,
            mes=CRON_DIARIO_MES,
            zona_horaria=ZONA_HORARIA_CRON,
        )
        periodic_diario, creado_diario = _sincronizar_periodic_task(
            nombre=NOMBRE_PERIODIC_TASK_DIARIO,
            tarea=NOMBRE_TAREA_CORREO_DIARIO,
            crontab=crontab_diario,
            habilitado=habilitar_diario,
            descripcion='Envio automatico de resumen diario ejecutivo por casino.',
        )

        crontab_mensual = _obtener_crontab(
            minuto=CRON_MENSUAL_MINUTO,
            hora=CRON_MENSUAL_HORA,
            dia_semana=CRON_MENSUAL_DIA_SEMANA,
            dia_mes=CRON_MENSUAL_DIA_MES,
            mes=CRON_MENSUAL_MES,
            zona_horaria=ZONA_HORARIA_CRON,
        )
        periodic_mensual, creado_mensual = _sincronizar_periodic_task(
            nombre=NOMBRE_PERIODIC_TASK_MENSUAL,
            tarea=NOMBRE_TAREA_CORREO_MENSUAL,
            crontab=crontab_mensual,
            habilitado=habilitar_mensual,
            descripcion='Envio automatico de cierre mensual ejecutivo por casino.',
        )

        crontab_sincronizar_horario = _obtener_crontab(
            minuto=CRON_SINCRONIZAR_HORARIO_MINUTO,
            hora=CRON_SINCRONIZAR_HORARIO_HORA,
            dia_semana=CRON_SINCRONIZAR_HORARIO_DIA_SEMANA,
            dia_mes=CRON_SINCRONIZAR_HORARIO_DIA_MES,
            mes=CRON_SINCRONIZAR_HORARIO_MES,
            zona_horaria=ZONA_HORARIA_CRON,
        )
        periodic_sincronizar_horario, creado_sincronizar_horario = _sincronizar_periodic_task(
            nombre=NOMBRE_PERIODIC_TASK_SINCRONIZAR_HORARIO_DIARIO,
            tarea=NOMBRE_TAREA_SINCRONIZAR_HORARIO_DIARIO,
            crontab=crontab_sincronizar_horario,
            habilitado=habilitar_sincronizacion_horario,
            descripcion='Sincroniza cada dia el horario del correo diario usando HORARIO_CIERRE de configuraciones globales.',
        )

        crontab_respaldo_bd = _obtener_crontab(
            minuto=CRON_RESPALDO_BD_MINUTO,
            hora=CRON_RESPALDO_BD_HORA,
            dia_semana=CRON_RESPALDO_BD_DIA_SEMANA,
            dia_mes=CRON_RESPALDO_BD_DIA_MES,
            mes=CRON_RESPALDO_BD_MES,
            zona_horaria=ZONA_HORARIA_CRON,
        )
        periodic_respaldo_bd, creado_respaldo_bd = _sincronizar_periodic_task(
            nombre=NOMBRE_PERIODIC_TASK_RESPALDO_BD,
            tarea=NOMBRE_TAREA_RESPALDO_BD,
            crontab=crontab_respaldo_bd,
            habilitado=habilitar_respaldo_bd,
            descripcion='Genera respaldo completo diario de base de datos.',
        )

        self.stdout.write(self.style.SUCCESS('Disparadores de correos ejecutivos sincronizados.'))
        self.stdout.write(
            f"- Diario: {'creado' if creado_diario else 'actualizado'} | enabled={periodic_diario.enabled} | {hora_diario}:{minuto_diario}"
        )
        self.stdout.write(f"  Origen horario diario: {origen_horario_diario}")
        self.stdout.write(
            f"- Mensual: {'creado' if creado_mensual else 'actualizado'} | enabled={periodic_mensual.enabled} | dia {CRON_MENSUAL_DIA_MES} {CRON_MENSUAL_HORA}:{CRON_MENSUAL_MINUTO}"
        )
        self.stdout.write(
            f"- Sync horario diario: {'creado' if creado_sincronizar_horario else 'actualizado'} | enabled={periodic_sincronizar_horario.enabled} | {CRON_SINCRONIZAR_HORARIO_HORA}:{CRON_SINCRONIZAR_HORARIO_MINUTO}"
        )
        self.stdout.write(
            f"- Backup BD diario: {'creado' if creado_respaldo_bd else 'actualizado'} | enabled={periodic_respaldo_bd.enabled} | {CRON_RESPALDO_BD_HORA}:{CRON_RESPALDO_BD_MINUTO}"
        )
