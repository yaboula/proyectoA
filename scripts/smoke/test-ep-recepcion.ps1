param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$BadgeToken = "OP-2026-BADGE-00042",
    [string]$Company = "Peintures du Maroc SARL",
    [switch]$PrepareSandbox,
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

    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Method Get -Uri $Url -WebSession $Session -UseBasicParsing
        }
        else {
            $response = Invoke-WebRequest -Method Post -Uri $Url -Body $Body -WebSession $Session -ContentType "application/x-www-form-urlencoded" -UseBasicParsing
        }
    }
    catch {
        $resp = $_.Exception.Response
        if ($null -ne $resp) {
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $bodyText = $reader.ReadToEnd()
            $reader.Close()
            throw "HTTP $([int]$resp.StatusCode) - $bodyText"
        }
        throw $_
    }

    if (-not $response.Content) {
        return $null
    }

    return ($response.Content | ConvertFrom-Json)
}

function Add-Result {
    param(
        [System.Collections.Generic.List[object]]$Results,
        [string]$Step,
        [bool]$Ok,
        [string]$Note
    )

    $status = if ($Ok) { "PASS" } else { "FAIL" }
    $Results.Add([pscustomobject]@{
        Step   = $Step
        Status = $status
        Note   = $Note
    }) | Out-Null

    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} - {2}" -f $status, $Step, $Note) -ForegroundColor $color
}

function Invoke-FormPostRaw {
    param(
        [string]$Url,
        [string]$Body,
        [Microsoft.PowerShell.Commands.WebRequestSession]$Session
    )

    try {
        $response = Invoke-WebRequest -Method Post -Uri $Url -Body $Body -WebSession $Session -ContentType "application/x-www-form-urlencoded" -UseBasicParsing
    }
    catch {
        $resp = $_.Exception.Response
        if ($null -ne $resp) {
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $bodyText = $reader.ReadToEnd()
            $reader.Close()
            throw "HTTP $([int]$resp.StatusCode) - $bodyText"
        }
        throw $_
    }

    if (-not $response.Content) {
        return $null
    }

    return ($response.Content | ConvertFrom-Json)
}

$results = New-Object 'System.Collections.Generic.List[object]'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$receptionBase = "$BaseUrl/api/method/gcma_kiosco.api.recepcion"
$kioscoBase = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"

Write-Host "Iniciando smoke recepcion GCMA..." -ForegroundColor Cyan

if ($PrepareSandbox) {
    try {
        $bootstrapOutput = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.bootstrap_recepcion_sandbox 2>&1 | Out-String
        Add-Result -Results $results -Step "Sandbox bootstrap" -Ok $true -Note ($bootstrapOutput.Trim())
    }
    catch {
        Add-Result -Results $results -Step "Sandbox bootstrap" -Ok $false -Note $_.Exception.Message
    }
}

try {
    $login = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.login_operario" -Body @{ qr_token = $BadgeToken } -Session $session
    $loginOk = $login.message.success -eq $true
    $loginNote = if ($null -ne $login.message.message_fr -and $login.message.message_fr -ne '') { $login.message.message_fr } else { 'login' }
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $loginOk -Note $loginNote
}
catch {
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $false -Note $_.Exception.Message
}

$order = $null
$item = $null
try {
    $listUrl = "$receptionBase.get_compras_pendientes?company=$([uri]::EscapeDataString($Company))"
    $epRec1 = Invoke-KioscoRequest -Method GET -Url $listUrl -Session $session
    $ok = $epRec1.message.success -eq $true -and ($epRec1.message.total -gt 0)
    if ($ok) {
        $order = $epRec1.message.ordenes[0]
        $item = $order.items[0]
    }
    $note = if ($ok) { "po=$($order.po_name) item=$($item.item_code)" } else { "sin ordenes abiertas" }
    Add-Result -Results $results -Step "EP_REC_1 get_compras_pendientes" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP_REC_1 get_compras_pendientes" -Ok $false -Note $_.Exception.Message
}

if ($null -ne $order -and $null -ne $item) {
    try {
        $qty = [Math]::Min([double]$item.qty_pending, 1.0)
        $expiryDate = $null
        if ($item.has_expiry_date -eq 1) {
            $expiryDate = (Get-Date).AddDays(365).ToString('yyyy-MM-dd')
        }

        $receiptPayload = @(
            @{
                item_code = $item.item_code
                qty = $qty
                supplier_batch = ("FOURN-{0:yyyyMMddHHmmss}" -f (Get-Date))
                expiry_date = $expiryDate
            }
        ) | ConvertTo-Json -Compress

        $rawBody = 'po_name=' + [uri]::EscapeDataString($order.po_name) + '&items_recibidos=' + [uri]::EscapeDataString($receiptPayload)
        $epRec2 = Invoke-FormPostRaw -Url "$receptionBase.registrar_recepcion" -Body $rawBody -Session $session

        $ok = $epRec2.message.success -eq $true -and -not [string]::IsNullOrWhiteSpace($epRec2.message.purchase_receipt)
        $lotes = @($epRec2.message.lotes_generados).Count
        $note = if ($ok) { "pr=$($epRec2.message.purchase_receipt) lotes=$lotes" } else { "sin purchase receipt" }
        Add-Result -Results $results -Step "EP_REC_2 registrar_recepcion" -Ok $ok -Note $note
    }
    catch {
        Add-Result -Results $results -Step "EP_REC_2 registrar_recepcion" -Ok $false -Note $_.Exception.Message
    }

    try {
        $reloadUrl = "$receptionBase.get_compras_pendientes?company=$([uri]::EscapeDataString($Company))"
        $epRec1Reload = Invoke-KioscoRequest -Method GET -Url $reloadUrl -Session $session
        $reloadedOrder = @($epRec1Reload.message.ordenes | Where-Object { $_.po_name -eq $order.po_name }) | Select-Object -First 1
        $reloadedItem = $null
        if ($null -ne $reloadedOrder) {
            $reloadedItem = @($reloadedOrder.items | Where-Object { $_.item_code -eq $item.item_code }) | Select-Object -First 1
        }

        $ok = $epRec1Reload.message.success -eq $true -and $null -ne $reloadedOrder -and $null -ne $reloadedItem -and ([double]$reloadedItem.qty_pending -lt [double]$item.qty_pending)
        $note = if ($ok) {
            "po=$($reloadedOrder.po_name) item=$($reloadedItem.item_code) qty_pending=$($reloadedItem.qty_pending)"
        }
        else {
            "reload sin reliquat esperado"
        }
        Add-Result -Results $results -Step "EP_REC_1 reload apres reception" -Ok $ok -Note $note
    }
    catch {
        Add-Result -Results $results -Step "EP_REC_1 reload apres reception" -Ok $false -Note $_.Exception.Message
    }
}
else {
    Add-Result -Results $results -Step "EP_REC_2 registrar_recepcion" -Ok $false -Note "Precondicion no satisfecha: sin orden o item pendiente"
    Add-Result -Results $results -Step "EP_REC_1 reload apres reception" -Ok $false -Note "Precondicion no satisfecha: sin orden o item pendiente"
}

$failed = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count
$passed = ($results | Where-Object { $_.Status -eq 'PASS' }).Count

Write-Host ""
Write-Host "Resumen smoke recepcion" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0
