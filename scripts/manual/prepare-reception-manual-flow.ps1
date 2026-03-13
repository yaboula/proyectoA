param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$BadgeToken = "OP-2026-BADGE-00042",
    [string]$Company = "Peintures du Maroc SARL",
    [string]$BackendContainer = "frappe_docker-backend-1",
    [string]$BenchSite = "frontend"
)

$ErrorActionPreference = "Stop"

function Invoke-KioscoRequest {
    param(
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [string]$Url,
        [hashtable]$Body,
        [Microsoft.PowerShell.Commands.WebRequestSession]$Session
    )

    if ($Method -eq "GET") {
        $response = Invoke-WebRequest -Method Get -Uri $Url -WebSession $Session -UseBasicParsing
    }
    else {
        $response = Invoke-WebRequest -Method Post -Uri $Url -Body $Body -WebSession $Session -ContentType "application/x-www-form-urlencoded" -UseBasicParsing
    }

    if (-not $response.Content) {
        return $null
    }

    return ($response.Content | ConvertFrom-Json)
}

Write-Host "Preparando punto de inicio para flujo manual de recepcion..." -ForegroundColor Cyan

$bootstrapOutput = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.bootstrap_recepcion_sandbox 2>&1 | Out-String
Write-Host $bootstrapOutput.Trim()

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$kioscoBase = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$receptionBase = "$BaseUrl/api/method/gcma_kiosco.api.recepcion"

$login = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.login_operario" -Body @{ qr_token = $BadgeToken } -Session $session
if ($login.message.success -ne $true) {
    throw "No se pudo iniciar sesion con el badge indicado."
}

$listUrl = "$receptionBase.get_compras_pendientes?company=$([uri]::EscapeDataString($Company))"
$pending = Invoke-KioscoRequest -Method GET -Url $listUrl -Session $session

if ($pending.message.success -ne $true -or $pending.message.total -lt 1) {
    throw "No hay Purchase Orders abiertas para iniciar el flujo manual."
}

$order = $pending.message.ordenes[0]
$item = $order.items[0]

Write-Host "" 
Write-Host "Flujo manual listo" -ForegroundColor Green
Write-Host ("PO sugerida: " + $order.po_name)
Write-Host ("Proveedor: " + $order.supplier_name)
Write-Host ("Linea sugerida: " + $item.item_code + " - " + $item.item_name)
Write-Host ("Qty pendiente actual: " + $item.qty_pending + " " + $item.uom)
Write-Host "" 
Write-Host "Siguiente paso en la app:" -ForegroundColor Cyan
Write-Host "1) Abrir /recepcion"
Write-Host "2) Elegir la PO sugerida"
Write-Host "3) Receptionner una cantidad parcial (ejemplo: 1)"
Write-Host "4) Confirmar que baja el reliquat en pantalla"
