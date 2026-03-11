param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$BadgeToken = "OP-2026-BADGE-00042",
    [string]$BatchNo = "LOTE-CHAOS-PT-001",
    [string]$ValidItemCode = "PT-PIN-BLC-MAT-20L",
    [string]$InvalidItemCode = "MP-RES-ALK-G70"
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

        if (-not $response.Content) {
            return $null
        }

        return ($response.Content | ConvertFrom-Json)
    }
    catch {
        throw $_
    }
}

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Get-HttpErrorPayload {
    param(
        [System.Exception]$Exception
    )

    $resp = $Exception.Response
    if ($null -eq $resp) {
        return $null
    }

    $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
    $bodyText = $reader.ReadToEnd()
    $reader.Close()

    $payload = $null
    try {
        $payload = $bodyText | ConvertFrom-Json
    }
    catch {
        $payload = $null
    }

    return [pscustomobject]@{
        StatusCode = [int]$resp.StatusCode
        Body       = $bodyText
        Parsed     = $payload
    }
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$kioscoBase = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$results = @()

Write-Host "Iniciando tests EP5 info_lote..." -ForegroundColor Cyan

# Arrange: login
$login = Invoke-KioscoRequest -Method POST -Url "$kioscoBase.login_operario" -Body @{ qr_token = $BadgeToken } -Session $session
Assert-True -Condition ($login.message.success -eq $true) -Message "Precondicion login fallida"

# Test 1: caso positivo
try {
    $url = "$kioscoBase.info_lote?batch_no=$([uri]::EscapeDataString($BatchNo))&item_code=$([uri]::EscapeDataString($ValidItemCode))"
    $res = Invoke-KioscoRequest -Method GET -Url $url -Session $session

    Assert-True -Condition ($res.message.success -eq $true) -Message "EP5 positivo: success=false"
    Assert-True -Condition ($null -ne $res.message.total_qty) -Message "EP5 positivo: total_qty ausente"
    Assert-True -Condition ($null -ne $res.message.stock_por_almacen) -Message "EP5 positivo: stock_por_almacen ausente"

    $results += [pscustomobject]@{ Test = "EP5 positivo"; Status = "PASS"; Note = "total_qty=$($res.message.total_qty)" }
    Write-Host "[PASS] EP5 positivo" -ForegroundColor Green
}
catch {
    $results += [pscustomobject]@{ Test = "EP5 positivo"; Status = "FAIL"; Note = $_.Exception.Message }
    Write-Host "[FAIL] EP5 positivo - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: contrato de error con item_code invalido
try {
    $url = "$kioscoBase.info_lote?batch_no=$([uri]::EscapeDataString($BatchNo))&item_code=$([uri]::EscapeDataString($InvalidItemCode))"
    $res = Invoke-KioscoRequest -Method GET -Url $url -Session $session

    # Some runtimes may return HTTP 200 with success=false for business validation errors.
    Assert-True -Condition ($res.message.success -eq $false) -Message "EP5 error-contract: success=true inesperado"
    Assert-True -Condition ($res.message.error_code -eq "BATCH_ITEM_MISMATCH") -Message "EP5 error-contract: error_code inesperado"

    $results += [pscustomobject]@{ Test = "EP5 contrato error"; Status = "PASS"; Note = "error_code=$($res.message.error_code) (HTTP 200)" }
    Write-Host "[PASS] EP5 contrato error" -ForegroundColor Green
}
catch {
    $httpError = Get-HttpErrorPayload -Exception $_.Exception
    if ($null -ne $httpError -and $httpError.StatusCode -eq 422) {
        $errorCode = if ($null -ne $httpError.Parsed -and $null -ne $httpError.Parsed.message) { $httpError.Parsed.message.error_code } else { "N/A" }
        $results += [pscustomobject]@{ Test = "EP5 contrato error"; Status = "PASS"; Note = "HTTP 422 esperado; error_code=$errorCode" }
        Write-Host "[PASS] EP5 contrato error" -ForegroundColor Green
    }
    else {
        $note = if ($null -ne $httpError) { "HTTP $($httpError.StatusCode) - $($httpError.Body)" } else { $_.Exception.Message }
        $results += [pscustomobject]@{ Test = "EP5 contrato error"; Status = "FAIL"; Note = $note }
        Write-Host "[FAIL] EP5 contrato error - $note" -ForegroundColor Red
    }
}

$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count

Write-Host ""
Write-Host "Resumen tests EP5" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0
