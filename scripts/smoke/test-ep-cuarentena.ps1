param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$BadgeToken = "OP-2026-BADGE-00042",
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

function New-KioscoSession {
    param(
        [string]$LoginUrl,
        [string]$QrToken
    )

    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $login = Invoke-KioscoRequest -Method POST -Url $LoginUrl -Body @{ qr_token = $QrToken } -Session $session
    if ($login.message.success -ne $true) {
        throw "LOGIN_FAILED"
    }

    return $session
}

$results = New-Object 'System.Collections.Generic.List[object]'
$kioscoBase = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$receptionBase = "$BaseUrl/api/method/gcma_kiosco.api.recepcion"
$itemCode = "MP-RES-ALK-G70"
$batchNo = "LOTE-QA-RECEP-0001"
$sourceWarehouse = "Cuarentena MP - PDM"
$targetWarehouse = "Materia Prima Aprobada - PDM"

Write-Host "Iniciando smoke cuarentena GCMA..." -ForegroundColor Cyan

if ($PrepareSandbox) {
    try {
        $bootstrapOutput = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.bootstrap_cuarentena_transfer_sandbox 2>&1 | Out-String
        $bootstrapOk = -not ($bootstrapOutput -match 'Traceback' -or $bootstrapOutput -match 'AttributeError' -or $bootstrapOutput -match 'NameError')
        Add-Result -Results $results -Step "Sandbox bootstrap" -Ok $bootstrapOk -Note ($bootstrapOutput.Trim())
    }
    catch {
        Add-Result -Results $results -Step "Sandbox bootstrap" -Ok $false -Note $_.Exception.Message
    }
}

try {
    $session = New-KioscoSession -LoginUrl "$kioscoBase.login_operario" -QrToken $BadgeToken
    $login = Invoke-KioscoRequest -Method GET -Url "$kioscoBase.get_operario_session" -Session $session
    $loginOk = $login.message.success -eq $true
    $loginNote = if ($null -ne $login.message.message_fr -and $login.message.message_fr -ne '') { $login.message.message_fr } else { 'login' }
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $loginOk -Note $loginNote
}
catch {
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $false -Note $_.Exception.Message
}

try {
    $ep5 = Invoke-KioscoRequest -Method GET -Url "$kioscoBase.info_lote?batch_no=$([uri]::EscapeDataString($batchNo))" -Session $session
    $quarantineRow = @($ep5.message.stock_por_almacen | Where-Object { $_.warehouse -eq $sourceWarehouse }) | Select-Object -First 1
    $availableQty = if ($null -ne $quarantineRow) { [double]$quarantineRow.qty } else { 0.0 }
    $ok = $ep5.message.success -eq $true -and $availableQty -gt 0
    $note = if ($ok) { "lot=$batchNo disponible=$availableQty" } else { "stock en quarantaine indisponible" }
    Add-Result -Results $results -Step "EP5 info_lote cuarentena" -Ok $ok -Note $note
}
catch {
    $availableQty = 0.0
    Add-Result -Results $results -Step "EP5 info_lote cuarentena" -Ok $false -Note $_.Exception.Message
}

if ($availableQty -gt 0) {
    try {
        $sessionTransfer = New-KioscoSession -LoginUrl "$kioscoBase.login_operario" -QrToken $BadgeToken
        $qtyToMove = [Math]::Min($availableQty, 5.0)
        $epRec3 = Invoke-KioscoRequest -Method POST -Url "$receptionBase.trasladar_lote_aprobado" -Body @{
            item_code = $itemCode
            batch_no = $batchNo
            qty_to_move = $qtyToMove
            source_warehouse = $sourceWarehouse
            target_warehouse = $targetWarehouse
        } -Session $sessionTransfer

        $ok = $epRec3.message.success -eq $true -and -not [string]::IsNullOrWhiteSpace($epRec3.message.stock_entry)
        $note = if ($ok) { "ste=$($epRec3.message.stock_entry) qty=$qtyToMove" } else { "sin stock entry" }
        Add-Result -Results $results -Step "EP_REC_3 traslado feliz" -Ok $ok -Note $note
    }
    catch {
        Add-Result -Results $results -Step "EP_REC_3 traslado feliz" -Ok $false -Note $_.Exception.Message
    }
}
else {
    Add-Result -Results $results -Step "EP_REC_3 traslado feliz" -Ok $false -Note "Precondicion no satisfecha: lote sin stock en cuarentena"
}

try {
    $sessionNegative = New-KioscoSession -LoginUrl "$kioscoBase.login_operario" -QrToken $BadgeToken
    $null = Invoke-KioscoRequest -Method POST -Url "$receptionBase.trasladar_lote_aprobado" -Body @{
        item_code = $itemCode
        batch_no = $batchNo
        qty_to_move = 1000
        source_warehouse = $sourceWarehouse
        target_warehouse = $targetWarehouse
    } -Session $sessionNegative

    Add-Result -Results $results -Step "EP_REC_3 stock insuficiente" -Ok $false -Note "La API no bloqueo el sobreconsumo"
}
catch {
    $message = $_.Exception.Message
    $ok = $message -match 'INSUFFICIENT_STOCK' -or $message -match 'Stock insuffisant' -or $message -match 'HTTP 422'
    Add-Result -Results $results -Step "EP_REC_3 stock insuficiente" -Ok $ok -Note $message
}

try {
    $sessionPrint = New-KioscoSession -LoginUrl "$kioscoBase.login_operario" -QrToken $BadgeToken
    $epRec4 = Invoke-KioscoRequest -Method GET -Url "$receptionBase.get_lote_para_impresion?batch_no=$([uri]::EscapeDataString($batchNo))" -Session $sessionPrint
    $ok = $epRec4.message.success -eq $true -and -not [string]::IsNullOrWhiteSpace($epRec4.message.etiqueta.batch_no)
    $note = if ($ok) { "batch=$($epRec4.message.etiqueta.batch_no) item=$($epRec4.message.etiqueta.item_code)" } else { "sin etiqueta" }
    Add-Result -Results $results -Step "EP_REC_4 get_lote_para_impresion" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP_REC_4 get_lote_para_impresion" -Ok $false -Note $_.Exception.Message
}

$failed = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count
$passed = ($results | Where-Object { $_.Status -eq 'PASS' }).Count

Write-Host ""
Write-Host "Resumen smoke cuarentena" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0
