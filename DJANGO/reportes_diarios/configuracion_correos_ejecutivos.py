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

# 1) Para que sirve: tomar el horario real de envio diario desde configuracion global.
# 2) Como funciona: al sincronizar disparadores se lee esta clave y se actualiza el cron diario.
# 3) Que hace: evita dejar fija la hora de envio cuando negocio cambie HORARIO_CIERRE.
# 4) Como editarla: usa otra clave solo si cambias la convencion en BD.
CLAVE_CONFIG_HORARIO_CIERRE = 'HORARIO_CIERRE'

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
NOMBRE_TAREA_SINCRONIZAR_HORARIO_DIARIO = 'reportes_diarios.sincronizar_horario_correo_diario'
NOMBRE_TAREA_RESPALDO_BD = 'reportes_diarios.ejecutar_backup_bd'

# 1) Para que sirve: activar o desactivar cada disparador sin eliminar el registro.
# 2) Como funciona: el comando de sincronizacion marca enabled en PeriodicTask.
# 3) Que hace: facilita pausar envios por mantenimiento.
# 4) Como editarla: cambia a False y vuelve a sincronizar disparadores.
HABILITAR_DISPARADOR_DIARIO = True
HABILITAR_DISPARADOR_MENSUAL = True
HABILITAR_DISPARADOR_SINCRONIZAR_HORARIO_DIARIO = True
HABILITAR_DISPARADOR_RESPALDO_BD = True

# 1) Para que sirve: definir horario del resumen diario ejecutivo.
# 2) Como funciona: cron minuto/hora/dia_semana/dia_mes/mes.
# 3) Que hace: ejecuta una tarea diaria en la hora indicada.
# 4) Como editarla: este valor es fallback cuando HORARIO_CIERRE no esta definido.
CRON_DIARIO_MINUTO = '10'
CRON_DIARIO_HORA = '08'
CRON_DIARIO_DIA_SEMANA = '*'
CRON_DIARIO_DIA_MES = '*'
CRON_DIARIO_MES = '*'

# 1) Para que sirve: definir horario del cierre mensual ejecutivo.
# 2) Como funciona: por defecto corre el dia 1 de cada mes a las 08:00.
# 3) Que hace: envia resumen del mes anterior por cada sucursal.
# 4) Como editarla: ajusta dia/hora segun operacion y vuelve a sincronizar.
CRON_MENSUAL_MINUTO = '00'
CRON_MENSUAL_HORA = '08'
CRON_MENSUAL_DIA_SEMANA = '*'
CRON_MENSUAL_DIA_MES = '1'
CRON_MENSUAL_MES = '*'

# 1) Para que sirve: programar una revision diaria de HORARIO_CIERRE para actualizar el cron diario.
# 2) Como funciona: corre una vez al dia y vuelve a ejecutar la sincronizacion de disparadores.
# 3) Que hace: asegura que cambios en configuracion global impacten el envio diario.
# 4) Como editarla: cambia la hora de revision sin tocar la logica del task.
CRON_SINCRONIZAR_HORARIO_MINUTO = '05'
CRON_SINCRONIZAR_HORARIO_HORA = '00'
CRON_SINCRONIZAR_HORARIO_DIA_SEMANA = '*'
CRON_SINCRONIZAR_HORARIO_DIA_MES = '*'
CRON_SINCRONIZAR_HORARIO_MES = '*'

# 1) Para que sirve: programar el respaldo completo de base de datos cada dia.
# 2) Como funciona: se ejecuta a las 23:59 por limitacion de cron sin segundos.
# 3) Que hace: genera respaldo SQL completo en carpeta configurable.
# 4) Como editarla: ajusta hora/minuto segun estrategia operativa del servidor.
CRON_RESPALDO_BD_MINUTO = '59'
CRON_RESPALDO_BD_HORA = '23'
CRON_RESPALDO_BD_DIA_SEMANA = '*'
CRON_RESPALDO_BD_DIA_MES = '*'
CRON_RESPALDO_BD_MES = '*'

# 1) Para que sirve: nombres internos de los PeriodicTask en django_celery_beat.
# 2) Como funciona: el comando sincroniza/actualiza por estos identificadores.
# 3) Que hace: mantiene registros estables y editables en BD.
# 4) Como editarla: evita cambiarla salvo migracion controlada de nombres.
NOMBRE_PERIODIC_TASK_DIARIO = 'correo_ejecutivo_diario_por_casino'
NOMBRE_PERIODIC_TASK_MENSUAL = 'correo_ejecutivo_cierre_mensual_por_casino'
NOMBRE_PERIODIC_TASK_SINCRONIZAR_HORARIO_DIARIO = 'sincronizar_horario_cierre_desde_config_global'
NOMBRE_PERIODIC_TASK_RESPALDO_BD = 'backup_bd_completo_diario'

# 1) Para que sirve: definir parametros del respaldo de base de datos.
# 2) Como funciona: tarea de backup usa esta ruta relativa y retencion en dias.
# 3) Que hace: centraliza configuracion para no tocar la tarea ni el script.
# 4) Como editarla: cambia carpeta/retencion segun capacidad de disco del servidor.
RUTA_RESPALDOS_BD_RELATIVA = 'media/backups_bd'

# 1) Para que sirve: ruta de bitacora tecnica del respaldo de BD.
# 2) Como funciona: cada ejecucion agrega eventos y errores por etapa en un log diario.
# 3) Que hace: evita fallos silenciosos y facilita diagnostico operativo.
# 4) Como editarla: apunta a otra carpeta dentro de media si cambias politica de monitoreo.
RUTA_LOGS_RESPALDO_BD_RELATIVA = 'media/logs/backups_bd'

# 1) Para que sirve: ruta secundaria para bitacora de respaldo cuando media no tiene permisos de escritura.
# 2) Como funciona: la tarea intenta esta carpeta si falla la ruta principal.
# 3) Que hace: evita que la tarea falle antes de iniciar por errores de permisos de carpeta.
# 4) Como editarla: usa una ruta local del servidor donde Celery Worker tenga permiso garantizado.
RUTA_LOGS_RESPALDO_BD_FALLBACK_RELATIVA = 'runtime/logs/backups_bd'

RETENCION_DIAS_RESPALDO_BD = 30

# 1) Para que sirve: definir destinatarios exclusivos del correo de backup.
# 2) Como funciona: se consulta esta clave en configuracion global y, si no existe, usa DESTINATARIOS_CORREOS.
# 3) Que hace: permite enviar respaldo a un correo personal sin afectar otros flujos.
# 4) Como editarla: cambia la clave solo si homologas convencion en base de datos.
CLAVE_CONFIG_DESTINATARIOS_RESPALDO_BD = 'DESTINATARIO_BACKUP'

# 1) Para que sirve: definir formato de compresion del respaldo antes de adjuntar por correo.
# 2) Como funciona: acepta 'gz' o 'zip'.
# 3) Que hace: reduce el peso del archivo para no exceder limites de adjuntos.
# 4) Como editarla: usa 'gz' por mejor compresion para SQL de texto.
FORMATO_COMPRESION_RESPALDO_BD = 'gz'

# 1) Para que sirve: limitar tamano del adjunto de respaldo en correo.
# 2) Como funciona: si el comprimido supera este valor se envia correo sin adjunto.
# 3) Que hace: evita rechazos por limite de 25 MB en proveedores de correo.
# 4) Como editarla: ajusta solo si cambian politicas del buzón destino.
LIMITE_ADJUNTO_CORREO_RESPALDO_BD_BYTES = 25 * 1024 * 1024

# 1) Para que sirve: estandarizar asuntos del correo de estado del backup.
# 2) Como funciona: la tarea usa asunto distinto para exito y fallo.
# 3) Que hace: facilita identificar alertas operativas en bandeja.
# 4) Como editarla: ajusta textos sin cambiar logica de ejecucion.
ASUNTO_CORREO_RESPALDO_BD_EXITO = 'BinsurMX | Respaldo BD exitoso'
ASUNTO_CORREO_RESPALDO_BD_FALLO = 'BinsurMX | Alerta respaldo BD fallido'

# Zona horaria para los cron de django_celery_beat.
ZONA_HORARIA_CRON = 'America/Mexico_City'
