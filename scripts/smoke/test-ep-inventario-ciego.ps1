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

$results = New-Object 'System.Collections.Generic.List[object]'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$kioscoBase = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$receptionBase = "$BaseUrl/api/method/gcma_kiosco.api.recepcion"
$warehouse = "Materia Prima Aprobada - PDM"
$conteo = @(
    @{ item_code = "MP-RES-ALK-G70"; batch_no = "LOTE-CIEGO-2026-0001"; qty_fisica = 10 },
    @{ item_code = "MP-RES-ALK-G70"; batch_no = "LOTE-CIEGO-2026-0002"; qty_fisica = 12 },
    @{ item_code = "MP-RES-ALK-G70"; batch_no = "LOTE-CIEGO-2026-0003"; qty_fisica = 13 },
    @{ item_code = "MP-RES-ALK-G70"; batch_no = "LOTE-CIEGO-2026-0004"; qty_fisica = 14 },
    @{ item_code = "MP-RES-ALK-G70"; batch_no = "LOTE-CIEGO-2026-0005"; qty_fisica = 15 }
)

Write-Host "Iniciando smoke inventario ciego GCMA..." -ForegroundColor Cyan

if ($PrepareSandbox) {
    try {
        $bootstrapOutput = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.bootstrap_inventario_ciego_sandbox 2>&1 | Out-String
        $bootstrapOk = -not ($bootstrapOutput -match 'Traceback' -or $bootstrapOutput -match 'AttributeError' -or $bootstrapOutput -match 'NameError')
        Add-Result -Results $results -Step "Sandbox bootstrap" -Ok $bootstrapOk -Note ($bootstrapOutput.Trim())
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

try {
    $epRec5 = Invoke-KioscoRequest -Method POST -Url "$receptionBase.subir_conteo_fisico" -Body @{
        warehouse = $warehouse
        conteo = ($conteo | ConvertTo-Json -Compress)
    } -Session $session

    $ok = $epRec5.message.success -eq $true -and -not [string]::IsNullOrWhiteSpace($epRec5.message.reconciliation_doc)
    $note = if ($ok) { "doc=$($epRec5.message.reconciliation_doc) lines=$($epRec5.message.items_count)" } else { "sin documento" }
    Add-Result -Results $results -Step "EP_REC_5 subir_conteo_fisico" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP_REC_5 subir_conteo_fisico" -Ok $false -Note $_.Exception.Message
}

try {
    $inspectOutput = docker exec -w /home/frappe/frappe-bench $BackendContainer bench --site $BenchSite execute gcma_kiosco.api.recepcion.inspect_latest_blind_inventory_reconciliation 2>&1 | Out-String
    $inspectOk = -not ($inspectOutput -match 'Traceback' -or $inspectOutput -match 'AttributeError' -or $inspectOutput -match 'NameError')
    if (-not $inspectOk) {
        throw $inspectOutput.Trim()
    }

    $inspection = $inspectOutput.Trim() | ConvertFrom-Json
    $ok = $inspection.docstatus -eq 0 -and $inspection.items_count -eq 1 -and $inspection.warehouse -eq $warehouse
    $note = if ($ok) { "doc=$($inspection.name) items=$($inspection.items_count) draft=$($inspection.docstatus)" } else { "inspeccion inconsistente" }
    Add-Result -Results $results -Step "DB Stock Reconciliation draft" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "DB Stock Reconciliation draft" -Ok $false -Note $_.Exception.Message
}

$failed = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count
$passed = ($results | Where-Object { $_.Status -eq 'PASS' }).Count

Write-Host ""
Write-Host "Resumen smoke inventario ciego" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0
