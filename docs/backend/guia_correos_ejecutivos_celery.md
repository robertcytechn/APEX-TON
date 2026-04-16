# Guia rapida: correos ejecutivos con Celery y RabbitMQ

Esta guia explica como operar los envios automaticos diario y mensual usando:
- Destinatarios globales en base de datos.
- Disparadores en django_celery_beat.
- Archivo de configuracion editable para horarios y backups.
- Broker RabbitMQ para tareas programadas en Windows Server.

## 1) Configurar destinatarios globales en base de datos

En la tabla de configuraciones globales crea o actualiza el registro:
- clave: DESTINATARIOS_CORREOS
- tipo_valor: STRING
- valor: correos separados por coma

Ejemplo de valor:

```text
robert.cy93@gmail.com,marcelaf@gbentretenimiento.com,direccion@empresa.com
```

Notas:
- Tambien se aceptan separadores por punto y coma o saltos de linea.
- Si la lista queda vacia, la sucursal se omite en el envio automatico.

## 2) Ajustar horarios sin tocar logica

Edita el archivo:
- DJANGO/reportes_diarios/configuracion_correos_ejecutivos.py

Parametros clave:
- HABILITAR_DISPARADOR_DIARIO
- HABILITAR_DISPARADOR_MENSUAL
- CLAVE_CONFIG_HORARIO_CIERRE (por defecto HORARIO_CIERRE)
- CRON_DIARIO_* (fallback si HORARIO_CIERRE no esta definido o no es valido)
- CRON_MENSUAL_* (por defecto dia 1 de cada mes a las 08:00)
- CRON_RESPALDO_BD_* (por defecto 23:59 diario)
- INCLUIR_CORREO_SUCURSAL_EN_ENVIO (opcional)

Despues de cualquier cambio en este archivo, sincroniza disparadores.

## 3) Sincronizar disparadores en django_celery_beat

Desde la carpeta DJANGO ejecuta:

```powershell
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py sincronizar_disparadores_correos_ejecutivos
```

Opciones utiles:

```powershell
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py sincronizar_disparadores_correos_ejecutivos --deshabilitar-diario
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py sincronizar_disparadores_correos_ejecutivos --deshabilitar-mensual
```

## 4) Levantar procesos necesarios

### RabbitMQ

Ejemplo local/servidor con Docker:

```powershell
docker run -d --name rabbit-apex -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Variables recomendadas en servidor:

```powershell
$env:CELERY_BROKER_URL = 'amqp://guest:guest@127.0.0.1:5672//'
$env:CELERY_RESULT_BACKEND = 'rpc://'
$env:MYSQLDUMP_PATH = 'C:/xampp/mysql/bin/mysqldump.exe'
```

### Worker Celery

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/celery.exe -A backend worker -l info --pool=solo
```

### Beat Celery

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/celery.exe -A backend beat -l info
```

### Waitress en servidor

Regla operativa de despliegue:

```powershell
waitress-serve --port=8000 backend.wsgi:application
```

## 5) Pruebas manuales recomendadas

### Generar/enviar manual diario

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py preparar_resumenes_ejecutivos --tipo diario --solo-generar
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py preparar_resumenes_ejecutivos --tipo diario
```

### Generar/enviar manual mensual

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py preparar_resumenes_ejecutivos --tipo mensual --solo-generar
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/python.exe manage.py preparar_resumenes_ejecutivos --tipo mensual
```

## 6) Tareas Celery involucradas

- reportes_diarios.enviar_resumen_diario_ejecutivo
- reportes_diarios.enviar_cierre_mensual_ejecutivo
- reportes_diarios.sincronizar_horario_correo_diario
- reportes_diarios.ejecutar_backup_bd

Estas tareas leen destinatarios desde ConfiguracionGlobal.DESTINATARIOS_CORREOS en cada ejecucion.

## 7) Programacion aplicada

- Envio diario: usa HORARIO_CIERRE desde ConfiguracionGlobal (resincroniza cada dia).
- Envio mensual: dia 1 a las 08:00.
- Backup completo BD: diario a las 23:59.

Nota: cron de django_celery_beat no maneja segundos, por eso el respaldo se define a las 23:59.

## 8) Script unico para servidor Windows

Para iniciar todo con un solo comando:

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
powershell -ExecutionPolicy Bypass -File ./scripts/iniciar_servicios_binsurmq.ps1
```

El script:
- Sincroniza disparadores en beat (incluye HORARIO_CIERRE y backup diario).
- Levanta waitress con el comando exacto solicitado.
- Levanta celery worker y celery beat en ventanas separadas.
- Guarda PIDs en DJANGO/runtime/servicios_binsurmq.pid.txt.
