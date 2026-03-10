$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath = Join-Path $repoRoot 'kiosco-pwa'

function Stop-ListenersForPort {
    param(
        [int]$Port,
        [string]$Reason
    )

    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $listeners) {
        return
    }

    $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    Write-Warning "$Reason Puerto $Port ocupado por PID(s): $($pids -join ', '). Se reiniciara el proceso."

    foreach ($processId in $pids) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        }
        catch {
            Write-Warning "No se pudo detener PID $processId en puerto ${Port}: $($_.Exception.Message)"
        }
    }

    Start-Sleep -Seconds 2

    $stillListening = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($stillListening) {
        $stillPids = $stillListening | Select-Object -ExpandProperty OwningProcess -Unique
        Write-Error "No se pudo liberar el puerto $Port. Sigue ocupado por PID(s): $($stillPids -join ', ')."
    }
}

if (-not (Test-Path $appPath)) {
    Write-Error "No se encontro kiosco-pwa en $appPath"
}

Stop-ListenersForPort -Port 5173 -Reason 'Kiosco dev:'
Stop-ListenersForPort -Port 5175 -Reason 'Vite duplicado detectado:'

Push-Location $appPath
try {
    npm run dev:kiosco
}
finally {
    Pop-Location
}