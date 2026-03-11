param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$BadgeToken = "OP-2026-BADGE-00042",
    [string]$Company = "Peintures du Maroc SARL",
    [string]$WorkOrder = "MFG-WO-2026-00001",
    [string]$QrData = "MP-RES-ALK-G70|LOTE-TEST-RES-001",
    [string]$BatchNo = "LOTE-CHAOS-PT-001",
    [string]$ItemCode = "PT-PIN-BLC-MAT-20L",
    [switch]$IncludeWriteOps,
    [string]$LotesUsadosJson = "",
    [string]$ConsumosExtraJson = "{}",
    [switch]$IncludeQualityWriteOps,
    [string]$QualityDecision = "Rejected",
    [double]$QualityQty = 1.0
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

            $parsed = $null
            try {
                $parsed = $bodyText | ConvertFrom-Json
            }
            catch {
                $parsed = $null
            }

            if ($null -ne $parsed -and $null -ne $parsed.message -and $null -ne $parsed.message.error_code) {
                throw "HTTP $([int]$resp.StatusCode) - $($parsed.message.error_code): $($parsed.message.message_fr)"
            }

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
$qualityBase = "$BaseUrl/api/method/gcma_kiosco.api.calidad"

Write-Host "Iniciando smoke suite GCMA Kiosco..." -ForegroundColor Cyan

try {
    $login = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.login_operario" -Body @{ qr_token = $BadgeToken } -Session $session
    $loginOk = $login.message.success -eq $true
    $loginNote = if ($null -ne $login.message.message_fr -and $login.message.message_fr -ne "") { $login.message.message_fr } else { "sin mensaje" }
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $loginOk -Note $loginNote
}
catch {
    Add-Result -Results $results -Step "EP1 login_operario" -Ok $false -Note $_.Exception.Message
}

try {
    $sessionRes = Invoke-KioscoRequest -Method GET -Url "$kioscoBase.get_operario_session" -Session $session
    $ok = $sessionRes.message.success -eq $true
    $sessionNote = if ($ok) { "sesion activa" } else { $sessionRes.message.error_code }
    Add-Result -Results $results -Step "EP1b get_operario_session" -Ok $ok -Note $sessionNote
}
catch {
    Add-Result -Results $results -Step "EP1b get_operario_session" -Ok $false -Note $_.Exception.Message
}

try {
    $ep2Url = "$kioscoBase.get_tareas?company=$([uri]::EscapeDataString($Company))"
    $ep2 = Invoke-KioscoRequest -Method GET -Url $ep2Url -Session $session
    $ok = $null -ne $ep2.message
    $total = if ($ok) { $ep2.message.total } else { "N/A" }
    Add-Result -Results $results -Step "EP2 get_tareas" -Ok $ok -Note "total=$total"
}
catch {
    Add-Result -Results $results -Step "EP2 get_tareas" -Ok $false -Note $_.Exception.Message
}

try {
    $ep3 = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.validar_material" -Body @{ work_order = $WorkOrder; qr_data = $QrData } -Session $session
    $ok = $null -ne $ep3.message
    $note = if ($ep3.message.valido -eq $true) { "valido=true" } else { "valido=false ($($ep3.message.error_code))" }
    Add-Result -Results $results -Step "EP3 validar_material" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP3 validar_material" -Ok $false -Note $_.Exception.Message
}

try {
    $ep5Url = "$kioscoBase.info_lote?batch_no=$([uri]::EscapeDataString($BatchNo))&item_code=$([uri]::EscapeDataString($ItemCode))"
    $ep5 = Invoke-KioscoRequest -Method GET -Url $ep5Url -Session $session
    $ok = $ep5.message.success -eq $true
    $note = if ($ok) { "total_qty=$($ep5.message.total_qty)" } else { $ep5.message.error_code }
    Add-Result -Results $results -Step "EP5 info_lote" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP5 info_lote" -Ok $false -Note $_.Exception.Message
}

try {
    $ep6 = Invoke-KioscoRequest -Method GET -Url "$qualityBase.get_lotes_cuarentena" -Session $session
    $ok = $ep6.message.success -eq $true
    $note = if ($ok) { "total=$($ep6.message.total)" } else { $ep6.message.error_code }
    Add-Result -Results $results -Step "EP6 get_lotes_cuarentena" -Ok $ok -Note $note
}
catch {
    Add-Result -Results $results -Step "EP6 get_lotes_cuarentena" -Ok $false -Note $_.Exception.Message
}

if ($IncludeWriteOps) {
    if ([string]::IsNullOrWhiteSpace($LotesUsadosJson)) {
        Add-Result -Results $results -Step "EP4 reportar_consumo" -Ok $false -Note "LotesUsadosJson obligatorio cuando IncludeWriteOps=true"
    }
    else {
        try {
            $ep4 = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.reportar_consumo" -Body @{
                work_order = $WorkOrder
                lotes_usados = $LotesUsadosJson
                consumos_extra = $ConsumosExtraJson
            } -Session $session
            $ok = $ep4.message.success -eq $true
            $note = if ($ok) { "transfer=$($ep4.message.stock_entry_transfer)" } else { $ep4.message.error_code }
            Add-Result -Results $results -Step "EP4 reportar_consumo" -Ok $ok -Note $note
        }
        catch {
            Add-Result -Results $results -Step "EP4 reportar_consumo" -Ok $false -Note $_.Exception.Message
        }
    }
}

if ($IncludeQualityWriteOps) {
    try {
        $ep7 = Invoke-KioscoRequest -Method POST -Url "$qualityBase.aprobar_calidad" -Body @{
            item_code = $ItemCode
            batch_no = $BatchNo
            qty = $QualityQty
            parametros = '{"pH":7.2,"aspect":"Conforme"}'
            resultado = $QualityDecision
            remarks = "Smoke suite sprint 2"
        } -Session $session

        $ok = $ep7.message.success -eq $true
        $note = if ($ok) { "qi=$($ep7.message.quality_inspection)" } else { $ep7.message.error_code }
        Add-Result -Results $results -Step "EP7 aprobar_calidad" -Ok $ok -Note $note
    }
    catch {
        Add-Result -Results $results -Step "EP7 aprobar_calidad" -Ok $false -Note $_.Exception.Message
    }
}

$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count

Write-Host ""
Write-Host "Resumen smoke suite" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0
