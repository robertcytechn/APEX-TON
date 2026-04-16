"""
Configuracion editable para disparadores de correos ejecutivos.

Este archivo concentra parametros operativos para no tocar la logica de tareas.
Despues de modificar horarios o flags, ejecuta el comando:
  manage.py sincronizar_disparadores_correos_ejecutivos
"""

# 1) Para que sirve: clave global en DB desde donde se leen destinatarios separados por coma.
# 2) Como funciona: se consulta en ConfiguracionGlobal.clave.
# 3) Que hace: evita hardcodear correos dentro del codigo.
# 4) Como editarla: cambia solo si decides usar otra variable global.
CLAVE_CONFIG_DESTINATARIOS_CORREOS = 'DESTINATARIOS_CORREOS'

# 1) Para que sirve: controlar si tambien se agrega correo de cada sucursal al envio.
# 2) Como funciona: cuando es True concatena sucursal.correo a los destinatarios globales.
# 3) Que hace: permite un modo hibrido de distribucion por sucursal.
# 4) Como editarla: ponlo en False para enviar unicamente a la lista global.
INCLUIR_CORREO_SUCURSAL_EN_ENVIO = False

# 1) Para que sirve: nombre canonico de tareas Celery para sincronizacion de beat.
# 2) Como funciona: PeriodicTask.task debe coincidir exactamente con shared_task(name=...).
# 3) Que hace: evita divergencias de nombre entre codigo y scheduler.
# 4) Como editarla: solo si renombras explicitamente las tareas en reportes_diarios.tareas.
NOMBRE_TAREA_CORREO_DIARIO = 'reportes_diarios.enviar_resumen_diario_ejecutivo'
NOMBRE_TAREA_CORREO_MENSUAL = 'reportes_diarios.enviar_cierre_mensual_ejecutivo'

# 1) Para que sirve: activar o desactivar cada disparador sin eliminar el registro.
# 2) Como funciona: el comando de sincronizacion marca enabled en PeriodicTask.
# 3) Que hace: facilita pausar envios por mantenimiento.
# 4) Como editarla: cambia a False y vuelve a sincronizar disparadores.
HABILITAR_DISPARADOR_DIARIO = True
HABILITAR_DISPARADOR_MENSUAL = True

# 1) Para que sirve: definir horario del resumen diario ejecutivo.
# 2) Como funciona: cron minuto/hora/dia_semana/dia_mes/mes.
# 3) Que hace: ejecuta una tarea diaria en la hora indicada.
# 4) Como editarla: cambia valores y luego sincroniza disparadores.
CRON_DIARIO_MINUTO = '10'
CRON_DIARIO_HORA = '08'
CRON_DIARIO_DIA_SEMANA = '*'
CRON_DIARIO_DIA_MES = '*'
CRON_DIARIO_MES = '*'

# 1) Para que sirve: definir horario del cierre mensual ejecutivo.
# 2) Como funciona: por defecto corre el dia 1 de cada mes a las 08:15.
# 3) Que hace: envia resumen del mes anterior por cada sucursal.
# 4) Como editarla: ajusta dia/hora segun operacion y vuelve a sincronizar.
CRON_MENSUAL_MINUTO = '15'
CRON_MENSUAL_HORA = '08'
CRON_MENSUAL_DIA_SEMANA = '*'
CRON_MENSUAL_DIA_MES = '1'
CRON_MENSUAL_MES = '*'

# 1) Para que sirve: nombres internos de los PeriodicTask en django_celery_beat.
# 2) Como funciona: el comando sincroniza/actualiza por estos identificadores.
# 3) Que hace: mantiene registros estables y editables en BD.
# 4) Como editarla: evita cambiarla salvo migracion controlada de nombres.
NOMBRE_PERIODIC_TASK_DIARIO = 'correo_ejecutivo_diario_por_casino'
NOMBRE_PERIODIC_TASK_MENSUAL = 'correo_ejecutivo_cierre_mensual_por_casino'

# Zona horaria para los cron de django_celery_beat.
ZONA_HORARIA_CRON = 'America/Mexico_City'
