import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from reportes_diarios.configuracion_correos_ejecutivos import (
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
    HABILITAR_DISPARADOR_DIARIO,
    HABILITAR_DISPARADOR_MENSUAL,
    NOMBRE_PERIODIC_TASK_DIARIO,
    NOMBRE_PERIODIC_TASK_MENSUAL,
    NOMBRE_TAREA_CORREO_DIARIO,
    NOMBRE_TAREA_CORREO_MENSUAL,
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

    # 1) Para que sirve: dejar configurados en BD los disparadores de correos ejecutivos.
    # 2) Como funciona: lee archivo de configuracion y hace upsert de dos PeriodicTask.
    # 3) Que hace: materializa la programacion de Celery Beat de forma repetible.
    # 4) Como editarla: si agregas mas disparadores, replica el mismo patron de sincronia.
    def handle(self, *args, **options):
        habilitar_diario = bool(HABILITAR_DISPARADOR_DIARIO) and not bool(options.get('deshabilitar_diario'))
        habilitar_mensual = bool(HABILITAR_DISPARADOR_MENSUAL) and not bool(options.get('deshabilitar_mensual'))

        crontab_diario = _obtener_crontab(
            minuto=CRON_DIARIO_MINUTO,
            hora=CRON_DIARIO_HORA,
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

        self.stdout.write(self.style.SUCCESS('Disparadores de correos ejecutivos sincronizados.'))
        self.stdout.write(
            f"- Diario: {'creado' if creado_diario else 'actualizado'} | enabled={periodic_diario.enabled} | {CRON_DIARIO_HORA}:{CRON_DIARIO_MINUTO}"
        )
        self.stdout.write(
            f"- Mensual: {'creado' if creado_mensual else 'actualizado'} | enabled={periodic_mensual.enabled} | dia {CRON_MENSUAL_DIA_MES} {CRON_MENSUAL_HORA}:{CRON_MENSUAL_MINUTO}"
        )
