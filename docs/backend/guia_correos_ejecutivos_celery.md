# Guia rapida: correos ejecutivos con Celery

Esta guia explica como operar los envios automaticos diario y mensual usando:
- Destinatarios globales en base de datos.
- Disparadores en django_celery_beat.
- Archivo de configuracion editable para horarios.

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
- CRON_DIARIO_* (hora/minuto y patron cron)
- CRON_MENSUAL_* (por defecto dia 1 de cada mes)
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

### Redis

Ejemplo local con Docker:

```powershell
docker run -d --name redis-apex -p 6379:6379 redis
```

### Worker Celery

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/celery.exe -A backend worker -l info
```

### Beat Celery

```powershell
cd c:/Users/rober/OneDrive/Escritorio/APEX-TON/DJANGO
c:/Users/rober/OneDrive/Escritorio/APEX-TON/.venv/Scripts/celery.exe -A backend beat -l info
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

Estas tareas leen destinatarios desde ConfiguracionGlobal.DESTINATARIOS_CORREOS en cada ejecucion.
