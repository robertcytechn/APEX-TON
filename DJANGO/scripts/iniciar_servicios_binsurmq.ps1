param(
    [string]$BrokerUrl = '',
    [string]$ResultBackend = '',
    [string]$PythonPath = '',
    [switch]$SinConsolaControl
)

$ErrorActionPreference = 'Stop'

# 1) Para que sirve: resolver rutas base de proyecto y entorno virtual.
# 2) Como funciona: usa PSScriptRoot para ubicar DJANGO y repo padre.
# 3) Que hace: evita dependencias con cwd manual del operador.
# 4) Como editarla: ajusta solo si mueves la carpeta DJANGO fuera del repo.
$RutaDjango = Split-Path -Parent $PSScriptRoot
$RutaRepo = Split-Path -Parent $RutaDjango
$RutaVenvScripts = Join-Path $RutaRepo '.venv/Scripts'
$RutaPythonVenv = Join-Path $RutaVenvScripts 'python.exe'
$RutaPython = ''
$RutaPythonReal = ''
$RutaScriptsPython = ''
$OrigenBroker = ''
$RutaEnvDjango = Join-Path $RutaDjango '.env'
$RutaRuntime = Join-Path $RutaDjango 'runtime'
$RutaLogs = Join-Path $RutaRuntime 'logs'

if (-not (Test-Path $RutaLogs)) {
    New-Item -Path $RutaLogs -ItemType Directory -Force | Out-Null
}

$SelloEjecucion = Get-Date -Format 'yyyyMMdd_HHmmss'
$RutaLogArranque = Join-Path $RutaLogs "arranque_binsurmq_$SelloEjecucion.log"

function Escribir-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Mensaje,
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Nivel = 'INFO'
    )

    $Linea = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Nivel, $Mensaje
    Write-Host $Linea
    Add-Content -Path $RutaLogArranque -Value $Linea -Encoding UTF8
}

function Iniciar-ProcesoServicio {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Nombre,
        [Parameter(Mandatory = $true)]
        [string]$Comando
    )

    $SelloProceso = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $RutaStdOut = Join-Path $RutaLogs "$Nombre.$SelloProceso.stdout.log"
    $RutaStdErr = Join-Path $RutaLogs "$Nombre.$SelloProceso.stderr.log"

    $Proceso = Start-Process `
        -FilePath 'powershell.exe' `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $Comando) `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $RutaStdOut `
        -RedirectStandardError $RutaStdErr

    return [PSCustomObject]@{
        Proceso = $Proceso
        RutaStdOut = $RutaStdOut
        RutaStdErr = $RutaStdErr
    }
}

function Obtener-ResumenEstadoServicio {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Nombre,
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Proceso,
        [Parameter(Mandatory = $true)]
        [string]$RutaStdOut,
        [Parameter(Mandatory = $true)]
        [string]$RutaStdErr
    )

    $EnLinea = $false
    try {
        $EnLinea = -not $Proceso.HasExited
    }
    catch {
        $EnLinea = $false
    }

    return [PSCustomObject]@{
        Nombre = $Nombre
        Estado = if ($EnLinea) { 'EN_LINEA' } else { 'NO_INICIADO' }
        Pid = $Proceso.Id
        RutaStdOut = $RutaStdOut
        RutaStdErr = $RutaStdErr
    }
}

function Es-ProcesoActivo {
    param(
        [Parameter(Mandatory = $false)]
        [int]$IdProceso = 0
    )

    if ($IdProceso -le 0) {
        return $false
    }

    return [bool](Get-Process -Id $IdProceso -ErrorAction SilentlyContinue)
}

function Obtener-DescendientesProceso {
    param(
        [Parameter(Mandatory = $true)]
        [int]$IdProcesoRaiz
    )

    if ($IdProcesoRaiz -le 0) {
        return @()
    }

    $ProcesosSistema = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Select-Object ProcessId, ParentProcessId
    $MapaHijos = @{}

    foreach ($ProcesoSistema in $ProcesosSistema) {
        $IdPadre = [int]$ProcesoSistema.ParentProcessId
        $IdHijo = [int]$ProcesoSistema.ProcessId

        if (-not $MapaHijos.ContainsKey($IdPadre)) {
            $MapaHijos[$IdPadre] = New-Object 'System.Collections.Generic.List[int]'
        }

        $null = $MapaHijos[$IdPadre].Add($IdHijo)
    }

    $Pendientes = New-Object 'System.Collections.Generic.Queue[int]'
    $Visitados = New-Object 'System.Collections.Generic.HashSet[int]'
    $Descendientes = New-Object 'System.Collections.Generic.List[int]'

    $Pendientes.Enqueue($IdProcesoRaiz)
    $null = $Visitados.Add($IdProcesoRaiz)

    while ($Pendientes.Count -gt 0) {
        $IdActual = $Pendientes.Dequeue()

        if (-not $MapaHijos.ContainsKey($IdActual)) {
            continue
        }

        foreach ($IdHijo in $MapaHijos[$IdActual]) {
            $IdHijoNormalizado = [int]$IdHijo
            if ($Visitados.Add($IdHijoNormalizado)) {
                $null = $Descendientes.Add($IdHijoNormalizado)
                $Pendientes.Enqueue($IdHijoNormalizado)
            }
        }
    }

    return @($Descendientes.ToArray())
}

function Detener-ArbolProceso {
    param(
        [Parameter(Mandatory = $true)]
        [int]$IdProcesoRaiz,
        [Parameter(Mandatory = $false)]
        [string]$Etiqueta = 'Proceso'
    )

    if ($IdProcesoRaiz -le 0) {
        return $false
    }

    $IdsDescendientes = Obtener-DescendientesProceso -IdProcesoRaiz $IdProcesoRaiz
    $IdsAEliminar = @()

    if ($IdsDescendientes.Count -gt 0) {
        $IdsAEliminar += ($IdsDescendientes | Sort-Object -Descending)
    }
    $IdsAEliminar += $IdProcesoRaiz

    foreach ($IdActual in $IdsAEliminar) {
        $IdActualNormalizado = [int]$IdActual
        if (-not (Es-ProcesoActivo -IdProceso $IdActualNormalizado)) {
            continue
        }
        Stop-Process -Id $IdActualNormalizado -Force -ErrorAction SilentlyContinue
    }

    $IdsPendientes = @()
    foreach ($IdActual in $IdsAEliminar) {
        $IdActualNormalizado = [int]$IdActual
        if (Es-ProcesoActivo -IdProceso $IdActualNormalizado) {
            $IdsPendientes += $IdActualNormalizado
        }
    }

    if ($IdsPendientes.Count -gt 0) {
        Escribir-Log "$Etiqueta mantiene procesos vivos tras detener arbol: $($IdsPendientes -join ', ')." 'WARN'
        return $false
    }

    return $true
}

function Obtener-PatronesServicio {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    switch ($Servicio.NombreProceso) {
        'waitress' {
            return @('waitress-serve --port=8000 backend.wsgi:application')
        }
        'celery_worker' {
            return @('-A backend worker -l info')
        }
        'celery_beat' {
            return @('-A backend beat -l info')
        }
        default {
            return @()
        }
    }
}

function Obtener-ProcesosHuerfanosServicio {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    $Patrones = Obtener-PatronesServicio -Servicio $Servicio
    if ($Patrones.Count -eq 0) {
        return @()
    }

    $ProcesosSistema = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Select-Object ProcessId, Name, CommandLine
    $Coincidencias = @()

    foreach ($ProcesoSistema in $ProcesosSistema) {
        $LineaComando = [string]$ProcesoSistema.CommandLine
        if ([string]::IsNullOrWhiteSpace($LineaComando)) {
            continue
        }

        foreach ($Patron in $Patrones) {
            if ($LineaComando -like "*$Patron*") {
                $Coincidencias += $ProcesoSistema
                break
            }
        }
    }

    return @($Coincidencias | Sort-Object ProcessId -Unique)
}

function Detener-ProcesosHuerfanosServicio {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    $ProcesosHuerfanos = Obtener-ProcesosHuerfanosServicio -Servicio $Servicio
    if ($ProcesosHuerfanos.Count -eq 0) {
        return 0
    }

    $Detenciones = 0
    foreach ($ProcesoHuerfano in ($ProcesosHuerfanos | Sort-Object ProcessId -Descending)) {
        $IdHuerfano = [int]$ProcesoHuerfano.ProcessId
        if (-not (Es-ProcesoActivo -IdProceso $IdHuerfano)) {
            continue
        }

        $ResultadoDetencion = Detener-ArbolProceso -IdProcesoRaiz $IdHuerfano -Etiqueta "$($Servicio.Nombre) huerfano"
        if ($ResultadoDetencion) {
            $Detenciones += 1
        }
    }

    return $Detenciones
}

function Obtener-PidServicioActivo {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    $PidServicio = 0
    try {
        $PidServicio = [int]$Servicio.Estado.Proceso.Id
    }
    catch {
        $PidServicio = 0
    }

    if (Es-ProcesoActivo -IdProceso $PidServicio) {
        return $PidServicio
    }

    return 0
}

function Guardar-ArchivoPidServicios {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RutaPid,
        [Parameter(Mandatory = $true)]
        [string]$BrokerUrl,
        [Parameter(Mandatory = $true)]
        [string]$ResultBackend,
        [Parameter(Mandatory = $true)]
        [string]$RutaLogArranque,
        [Parameter(Mandatory = $true)]
        [hashtable]$ServiciosControl
    )

    $ServicioWaitress = $ServiciosControl['waitress']
    $ServicioWorker = $ServiciosControl['worker']
    $ServicioBeat = $ServiciosControl['beat']

    $PidWaitress = Obtener-PidServicioActivo -Servicio $ServicioWaitress
    $PidWorker = Obtener-PidServicioActivo -Servicio $ServicioWorker
    $PidBeat = Obtener-PidServicioActivo -Servicio $ServicioBeat

    @(
        "WAITRESS_PID=$PidWaitress",
        "WORKER_PID=$PidWorker",
        "BEAT_PID=$PidBeat",
        "BROKER_URL=$BrokerUrl",
        "RESULT_BACKEND=$ResultBackend",
        "ARRANQUE_LOG=$RutaLogArranque",
        "WAITRESS_STDOUT=$($ServicioWaitress.Estado.RutaStdOut)",
        "WAITRESS_STDERR=$($ServicioWaitress.Estado.RutaStdErr)",
        "WORKER_STDOUT=$($ServicioWorker.Estado.RutaStdOut)",
        "WORKER_STDERR=$($ServicioWorker.Estado.RutaStdErr)",
        "BEAT_STDOUT=$($ServicioBeat.Estado.RutaStdOut)",
        "BEAT_STDERR=$($ServicioBeat.Estado.RutaStdErr)"
    ) | Set-Content -Path $RutaPid -Encoding UTF8
}

function Detener-ServicioControl {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    $PidServicio = Obtener-PidServicioActivo -Servicio $Servicio
    if ($PidServicio -eq 0) {
        $DetencionesHuerfanas = Detener-ProcesosHuerfanosServicio -Servicio $Servicio
        if ($DetencionesHuerfanas -gt 0) {
            Escribir-Log "$($Servicio.Nombre) no tenia PID padre activo, pero se detuvieron $DetencionesHuerfanas procesos huerfanos asociados."
            return
        }

        Escribir-Log "$($Servicio.Nombre) ya estaba detenido." 'WARN'
        return
    }

    $DetenidoArbol = Detener-ArbolProceso -IdProcesoRaiz $PidServicio -Etiqueta $Servicio.Nombre
    $DetencionesHuerfanas = Detener-ProcesosHuerfanosServicio -Servicio $Servicio

    if (-not $DetenidoArbol) {
        Escribir-Log "No fue posible detener $($Servicio.Nombre) (PID=$PidServicio)." 'WARN'
        return
    }

    if ($DetencionesHuerfanas -gt 0) {
        Escribir-Log "$($Servicio.Nombre): limpieza adicional de procesos huerfanos completada ($DetencionesHuerfanas)."
    }

    $ProcesosPendientes = Obtener-ProcesosHuerfanosServicio -Servicio $Servicio
    if ($ProcesosPendientes.Count -gt 0) {
        $IdsPendientes = ($ProcesosPendientes | ForEach-Object { [int]$_.ProcessId }) -join ', '
        Escribir-Log "$($Servicio.Nombre) mantiene procesos asociados activos: $IdsPendientes" 'WARN'
        return
    }

    Escribir-Log "$($Servicio.Nombre) detenido correctamente (PID=$PidServicio)."
}

function Reiniciar-ServicioControl {
    param(
        [Parameter(Mandatory = $true)]
        [PSCustomObject]$Servicio
    )

    Detener-ServicioControl -Servicio $Servicio
    $Servicio.Estado = Iniciar-ProcesoServicio -Nombre $Servicio.NombreProceso -Comando $Servicio.Comando
    Escribir-Log "$($Servicio.Nombre) reiniciado con PID=$($Servicio.Estado.Proceso.Id)."
}

function Mostrar-ResumenServiciosControl {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ServiciosControl
    )

    Write-Host ''
    Write-Host '================ RESUMEN SERVICIOS BINSURMQ ================'

    $TotalActivos = 0
    foreach ($ClaveServicio in @('waitress', 'worker', 'beat')) {
        $Servicio = $ServiciosControl[$ClaveServicio]
        $PidServicio = Obtener-PidServicioActivo -Servicio $Servicio
        $EstadoServicio = if ($PidServicio -gt 0) { 'EN_LINEA' } else { 'DETENIDO' }
        if ($PidServicio -gt 0) {
            $TotalActivos += 1
        }

        Write-Host ("{0,-14} {1,-10} PID={2}" -f $Servicio.Nombre, $EstadoServicio, $PidServicio)
        Write-Host ("  STDOUT: {0}" -f $Servicio.Estado.RutaStdOut)
        Write-Host ("  STDERR: {0}" -f $Servicio.Estado.RutaStdErr)
    }

    $EstadoGeneral = if ($TotalActivos -eq 3) {
        'ONLINE'
    }
    elseif ($TotalActivos -eq 0) {
        'OFFLINE'
    }
    else {
        'PARCIAL'
    }

    Write-Host ("Estado general: {0}" -f $EstadoGeneral)
    Write-Host '============================================================='

    return $EstadoGeneral
}

function Abrir-ConsolaControlServicios {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ServiciosControl,
        [Parameter(Mandatory = $true)]
        [string]$RutaPid,
        [Parameter(Mandatory = $true)]
        [string]$BrokerUrl,
        [Parameter(Mandatory = $true)]
        [string]$ResultBackend,
        [Parameter(Mandatory = $true)]
        [string]$RutaLogArranque
    )

    Escribir-Log 'Consola de control activa. Esta ventana permanece abierta para administrar servicios.'

    while ($true) {
        $EstadoGeneral = Mostrar-ResumenServiciosControl -ServiciosControl $ServiciosControl

        Write-Host ''
        Write-Host 'Opciones disponibles:'
        Write-Host '  1) Actualizar estado'
        Write-Host '  2) Reiniciar Waitress'
        Write-Host '  3) Reiniciar Celery Worker'
        Write-Host '  4) Reiniciar Celery Beat'
        Write-Host '  5) Reiniciar todos'
        Write-Host '  6) Detener todos y salir'
        Write-Host '  7) Salir y dejar servicios en segundo plano'

        $Opcion = [string](Read-Host 'Selecciona una opcion [1-7]')
        $Opcion = $Opcion.Trim()

        switch ($Opcion) {
            '1' {
                Escribir-Log "Actualizacion manual de estado solicitada. Estado general: $EstadoGeneral"
            }
            '2' {
                Reiniciar-ServicioControl -Servicio $ServiciosControl['waitress']
                Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl
            }
            '3' {
                Reiniciar-ServicioControl -Servicio $ServiciosControl['worker']
                Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl
            }
            '4' {
                Reiniciar-ServicioControl -Servicio $ServiciosControl['beat']
                Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl
            }
            '5' {
                Reiniciar-ServicioControl -Servicio $ServiciosControl['waitress']
                Reiniciar-ServicioControl -Servicio $ServiciosControl['worker']
                Reiniciar-ServicioControl -Servicio $ServiciosControl['beat']
                Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl
                Escribir-Log 'Reinicio general completado.'
            }
            '6' {
                Detener-ServicioControl -Servicio $ServiciosControl['beat']
                Detener-ServicioControl -Servicio $ServiciosControl['worker']
                Detener-ServicioControl -Servicio $ServiciosControl['waitress']
                Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl
                Escribir-Log 'Servicios detenidos por solicitud del operador. Cerrando consola de control.'
                break
            }
            '7' {
                Escribir-Log 'Consola cerrada por operador. Los servicios continuan en segundo plano.'
                break
            }
            default {
                Escribir-Log 'Opcion no valida. Usa un valor entre 1 y 7.' 'WARN'
            }
        }
    }
}

function Obtener-VariableEntornoArchivo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RutaArchivo,
        [Parameter(Mandatory = $true)]
        [string]$NombreVariable
    )

    if (-not (Test-Path $RutaArchivo)) {
        return ''
    }

    foreach ($Linea in (Get-Content -Path $RutaArchivo -Encoding UTF8)) {
        $LineaLimpia = [string]$Linea
        if ([string]::IsNullOrWhiteSpace($LineaLimpia)) {
            continue
        }

        $LineaLimpia = $LineaLimpia.Trim()
        if ($LineaLimpia.StartsWith('#')) {
            continue
        }

        $IndiceIgual = $LineaLimpia.IndexOf('=')
        if ($IndiceIgual -lt 1) {
            continue
        }

        $Clave = $LineaLimpia.Substring(0, $IndiceIgual).Trim()
        if ($Clave -ne $NombreVariable) {
            continue
        }

        $Valor = $LineaLimpia.Substring($IndiceIgual + 1).Trim()
        if (
            ($Valor.StartsWith('"') -and $Valor.EndsWith('"')) -or
            ($Valor.StartsWith("'") -and $Valor.EndsWith("'"))
        ) {
            $Valor = $Valor.Substring(1, $Valor.Length - 2)
        }

        return $Valor
    }

    return ''
}

try {
    # 1) Para que sirve: resolver Python en servidor sin depender de entorno virtual.
    # 2) Como funciona: prioridad PythonPath -> PYTHON_BIN -> python de sistema -> venv (fallback).
    # 3) Que hace: permite operar en servidores donde no existe .venv.
    # 4) Como editarla: pasa -PythonPath para forzar ejecutable especifico.
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $PythonPath = $env:PYTHON_BIN
    }

    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $PythonPath = 'python'
        }
        elseif (Test-Path $RutaPythonVenv) {
            $PythonPath = $RutaPythonVenv
        }
    }

    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        throw "No se encontro Python disponible (ni sistema ni entorno virtual). Configura Python en PATH o usa -PythonPath."
    }

    $RutaPython = $PythonPath

    try {
        $RutaPythonReal = (& $RutaPython -c "import sys; print(sys.executable)" 2>&1 | Select-Object -First 1).Trim()
    }
    catch {
        throw "No se pudo ejecutar Python con '$RutaPython'. Detalle: $($_.Exception.Message)"
    }

    if ([string]::IsNullOrWhiteSpace($RutaPythonReal)) {
        throw "No se pudo resolver la ruta real de Python desde '$RutaPython'."
    }

    $RutaScriptsPython = Join-Path (Split-Path -Parent $RutaPythonReal) 'Scripts'
    if (Test-Path $RutaScriptsPython) {
        $env:Path = "$RutaScriptsPython;$env:Path"
    }

    if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
        $BrokerUrl = $env:CELERY_BROKER_URL
        if (-not [string]::IsNullOrWhiteSpace($BrokerUrl)) {
            $OrigenBroker = 'variable de entorno CELERY_BROKER_URL'
        }
    }
    else {
        $OrigenBroker = 'parametro -BrokerUrl'
    }
    if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
        $BrokerUrl = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_URL'
        if (-not [string]::IsNullOrWhiteSpace($BrokerUrl)) {
            $OrigenBroker = 'archivo .env (CELERY_BROKER_URL)'
        }
    }

    if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
        $BrokerScheme = $env:CELERY_BROKER_SCHEME
        if ([string]::IsNullOrWhiteSpace($BrokerScheme)) {
            $BrokerScheme = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_SCHEME'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerScheme)) {
            $BrokerScheme = 'amqp'
        }

        $BrokerHost = $env:CELERY_BROKER_HOST
        if ([string]::IsNullOrWhiteSpace($BrokerHost)) {
            $BrokerHost = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_HOST'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerHost)) {
            $BrokerHost = '127.0.0.1'
        }

        $BrokerPort = $env:CELERY_BROKER_PORT
        if ([string]::IsNullOrWhiteSpace($BrokerPort)) {
            $BrokerPort = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_PORT'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerPort)) {
            $BrokerPort = '5672'
        }

        $BrokerUser = $env:CELERY_BROKER_USER
        if ([string]::IsNullOrWhiteSpace($BrokerUser)) {
            $BrokerUser = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_USER'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerUser)) {
            $BrokerUser = 'guest'
        }

        $BrokerPassword = $env:CELERY_BROKER_PASSWORD
        if ([string]::IsNullOrWhiteSpace($BrokerPassword)) {
            $BrokerPassword = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_PASSWORD'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerPassword)) {
            $BrokerPassword = 'guest'
        }

        $BrokerVhost = $env:CELERY_BROKER_VHOST
        if ([string]::IsNullOrWhiteSpace($BrokerVhost)) {
            $BrokerVhost = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_BROKER_VHOST'
        }
        if ([string]::IsNullOrWhiteSpace($BrokerVhost)) {
            $BrokerVhost = '/'
        }

        $BrokerVhost = $BrokerVhost.Trim()
        if ($BrokerVhost -eq '/') {
            $BrokerVhostNormalizado = '//'
        }
        elseif ($BrokerVhost.StartsWith('/')) {
            $BrokerVhostNormalizado = $BrokerVhost
        }
        else {
            $BrokerVhostNormalizado = "/$BrokerVhost"
        }

        $BrokerUserEscapado = [Uri]::EscapeDataString($BrokerUser)
        $BrokerPasswordEscapado = [Uri]::EscapeDataString($BrokerPassword)
        $BrokerUrl = "${BrokerScheme}://${BrokerUserEscapado}:${BrokerPasswordEscapado}@${BrokerHost}:${BrokerPort}${BrokerVhostNormalizado}"
        $OrigenBroker = 'variables CELERY_BROKER_* (entorno/.env)'
    }

    if ([string]::IsNullOrWhiteSpace($BrokerUrl)) {
        $BrokerUrl = 'amqp://guest:guest@127.0.0.1:5672//'
        $OrigenBroker = 'valor predeterminado local'
    }

    if ([string]::IsNullOrWhiteSpace($ResultBackend)) {
        $ResultBackend = $env:CELERY_RESULT_BACKEND
    }
    if ([string]::IsNullOrWhiteSpace($ResultBackend)) {
        $ResultBackend = Obtener-VariableEntornoArchivo -RutaArchivo $RutaEnvDjango -NombreVariable 'CELERY_RESULT_BACKEND'
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

    Escribir-Log "Inicio de arranque de servicios BinsurMQ."
    Escribir-Log "Log de arranque: $RutaLogArranque"
    Escribir-Log "Archivo .env detectado: $RutaEnvDjango"
    Escribir-Log "Python resuelto: $RutaPythonReal"
    Escribir-Log "Broker URL activo: $BrokerUrl"
    Escribir-Log "Origen broker: $OrigenBroker"
    Escribir-Log "Result backend activo: $ResultBackend"

    Push-Location $RutaDjango
    try {
        Escribir-Log "[1/3] Sincronizando disparadores (HORARIO_CIERRE + mensual + backup)..."
        (& $RutaPython manage.py sincronizar_disparadores_correos_ejecutivos 2>&1 | Out-String).Trim().Split([Environment]::NewLine) | ForEach-Object {
            if (-not [string]::IsNullOrWhiteSpace($_)) {
                Escribir-Log $_
            }
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo al sincronizar disparadores de Celery Beat."
        }

        Escribir-Log "[2/3] Iniciando procesos: waitress, celery worker, celery beat..."

        $BrokerUrlEscapado = $BrokerUrl.Replace("'", "''")
        $ResultBackendEscapado = $ResultBackend.Replace("'", "''")
        $PathEscapado = $env:Path.Replace("'", "''")
        $RutaDjangoEscapada = $RutaDjango.Replace("'", "''")
        $RutaPythonEscapada = $RutaPython.Replace("'", "''")

        $ComandoBaseEntorno = "`$env:CELERY_BROKER_URL='$BrokerUrlEscapado'; `$env:CELERY_RESULT_BACKEND='$ResultBackendEscapado'; `$env:Path='$PathEscapado'; Set-Location '$RutaDjangoEscapada';"
        $ComandoCeleryBase = "& '$RutaPythonEscapada' -m celery -A backend.celery:app"

        # Regla solicitada: iniciar exactamente este comando para servidor.
        $ComandoWaitress = "$ComandoBaseEntorno waitress-serve --port=8000 backend.wsgi:application"
        $ComandoWorker = "$ComandoBaseEntorno $ComandoCeleryBase worker -l info --pool=solo --include=reportes_diarios.tareas,reportes_diarios.tasks"
        $ComandoBeat = "$ComandoBaseEntorno $ComandoCeleryBase beat -l info"

        $EstadoWaitress = Iniciar-ProcesoServicio -Nombre 'waitress' -Comando $ComandoWaitress
        $EstadoWorker = Iniciar-ProcesoServicio -Nombre 'celery_worker' -Comando $ComandoWorker
        $EstadoBeat = Iniciar-ProcesoServicio -Nombre 'celery_beat' -Comando $ComandoBeat

        $ServiciosControl = [ordered]@{
            waitress = [PSCustomObject]@{
                Nombre = 'Waitress'
                NombreProceso = 'waitress'
                Comando = $ComandoWaitress
                Estado = $EstadoWaitress
            }
            worker = [PSCustomObject]@{
                Nombre = 'Celery Worker'
                NombreProceso = 'celery_worker'
                Comando = $ComandoWorker
                Estado = $EstadoWorker
            }
            beat = [PSCustomObject]@{
                Nombre = 'Celery Beat'
                NombreProceso = 'celery_beat'
                Comando = $ComandoBeat
                Estado = $EstadoBeat
            }
        }

        Escribir-Log "Procesos secundarios iniciados en segundo plano con ventanas ocultas."

        $RutaPid = Join-Path $RutaRuntime 'servicios_binsurmq.pid.txt'
        if (-not (Test-Path $RutaRuntime)) {
            New-Item -Path $RutaRuntime -ItemType Directory -Force | Out-Null
        }

        Guardar-ArchivoPidServicios -RutaPid $RutaPid -BrokerUrl $BrokerUrl -ResultBackend $ResultBackend -RutaLogArranque $RutaLogArranque -ServiciosControl $ServiciosControl

        $EstadoGeneralArranque = Mostrar-ResumenServiciosControl -ServiciosControl $ServiciosControl
        Escribir-Log "Estado general del arranque: $EstadoGeneralArranque"

        $PidWaitress = Obtener-PidServicioActivo -Servicio $ServiciosControl['waitress']
        $PidWorker = Obtener-PidServicioActivo -Servicio $ServiciosControl['worker']
        $PidBeat = Obtener-PidServicioActivo -Servicio $ServiciosControl['beat']

        Escribir-Log "[3/3] Servicios iniciados correctamente."
        Escribir-Log "Waitress PID: $PidWaitress"
        Escribir-Log "Worker PID: $PidWorker"
        Escribir-Log "Beat PID: $PidBeat"
        Escribir-Log "Archivo PID: $RutaPid"
        Escribir-Log "Log worker stderr: $($ServiciosControl['worker'].Estado.RutaStdErr)"
        Escribir-Log "Log beat stderr: $($ServiciosControl['beat'].Estado.RutaStdErr)"

        if ($SinConsolaControl) {
            Escribir-Log 'SinConsolaControl activo: se cierra esta ventana y los servicios quedan en segundo plano.'
        }
        else {
            Abrir-ConsolaControlServicios `
                -ServiciosControl $ServiciosControl `
                -RutaPid $RutaPid `
                -BrokerUrl $BrokerUrl `
                -ResultBackend $ResultBackend `
                -RutaLogArranque $RutaLogArranque
        }
    }
    finally {
        Pop-Location
    }
}
catch {
    Escribir-Log "Error al iniciar servicios: $($_.Exception.Message)" 'ERROR'
    Escribir-Log "Detalle tecnico: $($_.ToString())" 'ERROR'
    Escribir-Log "Revisa el log de arranque: $RutaLogArranque" 'ERROR'
    throw
}
