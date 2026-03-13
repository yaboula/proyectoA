param(
    [string]$BackendContainer = "frappe_docker-backend-1",
    [string]$BenchSite = "frontend"
)

$ErrorActionPreference = "Stop"

Write-Host "Preparando sandbox de recepcion para Playwright..." -ForegroundColor Cyan

$output = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.bootstrap_recepcion_sandbox 2>&1 | Out-String

Write-Host $output.Trim()