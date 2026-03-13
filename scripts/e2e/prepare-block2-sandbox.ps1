param(
    [string]$BackendContainer = "frappe_docker-backend-1",
    [string]$BenchSite = "frontend"
)

$ErrorActionPreference = "Stop"

function Invoke-BenchBootstrap {
    param(
        [string]$Method
    )

    $output = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute $Method 2>&1 | Out-String
    Write-Host $output.Trim()
}

Write-Host "Preparando sandbox completo de Bloque 2..." -ForegroundColor Cyan
Invoke-BenchBootstrap -Method gcma_kiosco.api.recepcion.bootstrap_recepcion_sandbox
Invoke-BenchBootstrap -Method gcma_kiosco.api.recepcion.bootstrap_cuarentena_transfer_sandbox
Invoke-BenchBootstrap -Method gcma_kiosco.api.recepcion.bootstrap_inventario_ciego_sandbox