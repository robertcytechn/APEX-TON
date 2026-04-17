param(
    [string]$BrokerUrl = '',
    [string]$ResultBackend = ''
)

$ErrorActionPreference = 'Stop'

# 1) Para que sirve: resolver rutas base de proyecto y entorno virtual.
# 2) Como funciona: usa PSScriptRoot para ubicar DJANGO y repo padre.
# 3) Que hace: evita dependencias con cwd manual del operador.
# 4) Como editarla: ajusta solo si mueves la carpeta DJANGO fuera del repo.
$RutaDjango = Split-Path -Parent $PSScriptRoot
$RutaRepo = Split-Path -Parent $RutaDjango
$RutaVenvScripts = Join-Path $RutaRepo '.venv/Scripts'
$RutaPython = Join-Path $RutaVenvScripts 'python.exe'

if (-not (Test-Path $RutaPython)) {
    throw "No se encontro python del entorno virtual en: $RutaPython"
}

if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
    $BrokerUrl = $env:CELERY_BROKER_URL
}
if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
    $BrokerUrl = 'amqp://guest:guest@127.0.0.1:5672//'
}

if ([string]::IsNullOrWhiteSpace($ResultBackend)) {
    $ResultBackend = $env:CELERY_RESULT_BACKEND
}
if ([string]::IsNullOrWhiteSpace($ResultBackend)) {
    $ResultBackend = 'rpc://'
}

# 1) Para que sirve: garantizar broker RabbitMQ para worker y beat en este arranque.
# 2) Como funciona: define variables de entorno antes de lanzar procesos.
# 3) Que hace: fuerza operacion con RabbitMQ en Windows Server.
# 4) Como editarla: pasa -BrokerUrl o -ResultBackend al invocar el script.
$env:CELERY_BROKER_URL = $BrokerUrl
$env:CELERY_RESULT_BACKEND = $ResultBackend
$env:Path = "$RutaVenvScripts;$env:Path"

Write-Host "[1/3] Sincronizando disparadores (HORARIO_CIERRE + mensual + backup)..." -ForegroundColor Cyan
Push-Location $RutaDjango
try {
    & $RutaPython manage.py sincronizar_disparadores_correos_ejecutivos
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo al sincronizar disparadores de Celery Beat."
    }

    Write-Host "[2/3] Iniciando procesos: waitress, celery worker, celery beat..." -ForegroundColor Cyan

    $ComandoBaseEntorno = "`$env:CELERY_BROKER_URL='$BrokerUrl'; `$env:CELERY_RESULT_BACKEND='$ResultBackend'; `$env:Path='$RutaVenvScripts;' + `$env:Path; Set-Location '$RutaDjango';"

    # Regla solicitada: iniciar exactamente este comando para servidor.
    $ComandoWaitress = "$ComandoBaseEntorno waitress-serve --port=8000 backend.wsgi:application"
    $ComandoWorker = "$ComandoBaseEntorno celery -A backend worker -l info --pool=solo"
    $ComandoBeat = "$ComandoBaseEntorno celery -A backend beat -l info"

    $ProcesoWaitress = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $ComandoWaitress) -PassThru
    $ProcesoWorker = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $ComandoWorker) -PassThru
    $ProcesoBeat = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $ComandoBeat) -PassThru

    $RutaPid = Join-Path $RutaDjango 'runtime/servicios_binsurmq.pid.txt'
    $CarpetaRuntime = Split-Path -Parent $RutaPid
    if (-not (Test-Path $CarpetaRuntime)) {
        New-Item -Path $CarpetaRuntime -ItemType Directory | Out-Null
    }

    @(
        "WAITRESS_PID=$($ProcesoWaitress.Id)",
        "WORKER_PID=$($ProcesoWorker.Id)",
        "BEAT_PID=$($ProcesoBeat.Id)",
        "BROKER_URL=$BrokerUrl"
    ) | Set-Content -Path $RutaPid -Encoding UTF8

    Write-Host "[3/3] Servicios iniciados correctamente." -ForegroundColor Green
    Write-Host " - Waitress PID: $($ProcesoWaitress.Id)"
    Write-Host " - Worker PID:   $($ProcesoWorker.Id)"
    Write-Host " - Beat PID:     $($ProcesoBeat.Id)"
    Write-Host "Archivo PID: $RutaPid"
}
finally {
    Pop-Location
}
