param(
    [string]$WorkspaceRoot = "D:\proyectoA"
)

$ErrorActionPreference = "Stop"

$results = New-Object 'System.Collections.Generic.List[object]'

function Add-BlockResult {
    param(
        [string]$Step,
        [bool]$Ok,
        [string]$Note
    )

    $status = if ($Ok) { 'PASS' } else { 'FAIL' }
    $results.Add([pscustomobject]@{
        Step = $Step
        Status = $status
        Note = $Note
    }) | Out-Null

    $color = if ($Ok) { 'Green' } else { 'Red' }
    Write-Host ("[{0}] {1} - {2}" -f $status, $Step, $Note) -ForegroundColor $color
}

function Invoke-SmokeStep {
    param(
        [string]$Step,
        [string]$ScriptPath
    )

    try {
        $output = & $ScriptPath -PrepareSandbox 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "ExitCode=$exitCode`n$($output.Trim())"
        }
        Add-BlockResult -Step $Step -Ok $true -Note ($output.Trim())
    }
    catch {
        Add-BlockResult -Step $Step -Ok $false -Note $_.Exception.Message
    }
}

Write-Host "Iniciando smoke completo Bloque 2..." -ForegroundColor Cyan

Push-Location $WorkspaceRoot
try {
    Invoke-SmokeStep -Step "Sprint 4 recepcion" -ScriptPath ".\scripts\smoke\test-ep-recepcion.ps1"
    Invoke-SmokeStep -Step "Sprint 5 cuarentena" -ScriptPath ".\scripts\smoke\test-ep-cuarentena.ps1"
    Invoke-SmokeStep -Step "Sprint 6 inventario ciego" -ScriptPath ".\scripts\smoke\test-ep-inventario-ciego.ps1"
}
finally {
    Pop-Location
}

$failed = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count
$passed = ($results | Where-Object { $_.Status -eq 'PASS' }).Count

Write-Host ""
Write-Host "Resumen smoke Bloque 2" -ForegroundColor Cyan
$results | Format-Table -AutoSize
Write-Host ""
Write-Host ("PASS={0} FAIL={1}" -f $passed, $failed) -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}

exit 0