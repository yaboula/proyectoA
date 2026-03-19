param(
    [string]$BaseUrl         = "http://localhost:8080",
    [string]$BadgeComercial  = "COM-2026-BADGE-00099",
    [string]$BadgeChofer     = "CHOFER-2026-BADGE-00088",
    [string]$ClienteId       = "Droguerie Atlas Test",
    [string]$SalesOrder      = "",
    [string]$ItemCodeFefo    = "PT-TEST-B3-ITEM-A",
    [string]$BatchFefo       = "B3-FEFO-NEAR-001",
    [string]$AdminUser       = "Administrator",
    [string]$AdminPwd        = "admin",
    [switch]$IncludeWriteOps
)

$ErrorActionPreference = "Continue"

$cookieCom    = "$env:TEMP\b3_cookie_com.txt"
$cookieChofer = "$env:TEMP\b3_cookie_chofer.txt"
$cookieAdmin  = "$env:TEMP\b3_cookie_admin.txt"
$results = New-Object "System.Collections.Generic.List[object]"

function Add-Result {
    param([string]$Sprint, [string]$Step, [bool]$Ok, [string]$Note)
    $status = if ($Ok) { "PASS" } else { "FAIL" }
    $results.Add([pscustomobject]@{ Sprint=$Sprint; Step=$Step; Status=$status; Note=$Note }) | Out-Null
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1,-10} {2,-42} {3}" -f $status, $Sprint, $Step, $Note) -ForegroundColor $color
}

function Coalesce {
    param($a, $b, $c)
    if ($null -ne $a -and "$a" -ne "") { return $a }
    if ($null -ne $b -and "$b" -ne "") { return $b }
    return $c
}

function Get-Prop {
    param($obj, [string]$prop, $default)
    if ($null -eq $obj) { return $default }
    try { $v = $obj.$prop; if ($null -eq $v) { $default } else { $v } } catch { $default }
}

function Invoke-B3Get {
    param([string]$Url, [string]$CookieFile)
    $raw = curl.exe -s --max-time 15 -b $CookieFile $Url 2>&1
    if ($LASTEXITCODE -ne 0) { throw "curl GET failed ($LASTEXITCODE): $raw" }
    $parsed = $raw | ConvertFrom-Json
    return $parsed
}

function Invoke-B3Post {
    param([string]$Url, [hashtable]$Body, [string]$CookieFile)
    $formArgs = @()
    foreach ($k in $Body.Keys) { $formArgs += @("-d", "$k=$([uri]::EscapeDataString($Body[$k]))") }
    $raw = curl.exe -s --max-time 15 -b $CookieFile -c $CookieFile -X POST $formArgs $Url 2>&1
    if ($LASTEXITCODE -ne 0) { throw "curl POST failed ($LASTEXITCODE): $raw" }
    $parsed = $raw | ConvertFrom-Json
    return $parsed
}

function Invoke-B3Login {
    param([string]$Url, [hashtable]$Body, [string]$CookieFile)
    $formArgs = @()
    foreach ($k in $Body.Keys) { $formArgs += @("-d", "$k=$([uri]::EscapeDataString($Body[$k]))") }
    $raw = curl.exe -s --max-time 15 -c $CookieFile -X POST $formArgs $Url 2>&1
    if ($LASTEXITCODE -ne 0) { throw "curl LOGIN failed ($LASTEXITCODE): $raw" }
    return ($raw | ConvertFrom-Json)
}

$KIOSCO_NS = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$C         = "$BaseUrl/api/method/gcma_kiosco.api.comercial"
$L         = "$BaseUrl/api/method/gcma_kiosco.api.logistica"
$G         = "$BaseUrl/api/method/gcma_kiosco.api.gerencial"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  GCMA Bloque 3 -- Smoke Test (S07-S12) v0.9.3" -ForegroundColor Cyan
Write-Host "  BaseUrl  : $BaseUrl" -ForegroundColor Cyan
Write-Host "  Cliente  : $ClienteId" -ForegroundColor Cyan
Write-Host "  WriteOps : $IncludeWriteOps" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# ---- SETUP: Login ------------------------------------------------
Write-Host "-- SETUP: Login --" -ForegroundColor DarkGray

try {
    $lc = Invoke-B3Login -Url "$KIOSCO_NS.login_operario" -Body @{ qr_token=$BadgeComercial } -CookieFile $cookieCom
    $ok = ($lc.message.success -eq $true)
    $msg = Coalesce (Get-Prop $lc.message "message_fr" $null) (Get-Prop $lc.message "error_code" $null) "sin msg"
    Add-Result "SETUP" "login_comercial" $ok $msg
} catch { Add-Result "SETUP" "login_comercial" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $lcho = Invoke-B3Login -Url "$KIOSCO_NS.login_operario" -Body @{ qr_token=$BadgeChofer } -CookieFile $cookieChofer
    $ok = ($lcho.message.success -eq $true)
    $msg = Coalesce (Get-Prop $lcho.message "message_fr" $null) (Get-Prop $lcho.message "error_code" $null) "sin msg"
    Add-Result "SETUP" "login_chofer" $ok $msg
} catch { Add-Result "SETUP" "login_chofer" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $ladm = Invoke-B3Login -Url "$BaseUrl/api/method/login" -Body @{ usr=$AdminUser; pwd=$AdminPwd } -CookieFile $cookieAdmin
    $okAdm = ($ladm.message -eq "Logged In")
    Add-Result "SETUP" "login_admin" $okAdm "user=$AdminUser"
} catch { Add-Result "SETUP" "login_admin" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

# ---- S07: Rutas + Catalogo ---------------------------------------
Write-Host ""
Write-Host "-- S07: Rutas + Catalogo --" -ForegroundColor DarkGray

try {
    $ruta = Invoke-B3Get -Url "$C.get_ruta_dia" -CookieFile $cookieCom
    $ok = ($null -ne $ruta.message)  # PASS si el endpoint responde (rutas puede estar vacia)
    $arr = Get-Prop $ruta.message "rutas" $null
    $total = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S07" "get_ruta_dia" $ok "rutas_hoy=$total (seed pendiente)"
} catch { Add-Result "S07" "get_ruta_dia" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $cat = Invoke-B3Get -Url "$C.get_catalogo_stock?limit=10" -CookieFile $cookieCom
    $ok = ($null -ne $cat.message)
    $arr = Get-Prop $cat.message "items" $null
    $cnt = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S07" "get_catalogo_stock" $ok "items=$cnt"
} catch { Add-Result "S07" "get_catalogo_stock" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $catS = Invoke-B3Get -Url "$C.get_catalogo_stock?search=test&limit=5" -CookieFile $cookieCom
    $ok = ($null -ne $catS.message)
    Add-Result "S07" "get_catalogo_stock+search" $ok "search=test ok"
} catch { Add-Result "S07" "get_catalogo_stock+search" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

if ($IncludeWriteOps) {
    try {
        $chk = Invoke-B3Post -Url "$C.post_checkin" -Body @{ id_cliente=$ClienteId; gps_lat_capturada="33.5731"; gps_lng_capturada="-7.5898" } -CookieFile $cookieCom
        $ok = ($null -ne $chk.message -and (Get-Prop $chk.message "status" $null) -ne "error")
        $note = Coalesce (Get-Prop $chk.message "status" $null) (Get-Prop $chk.message "error_code" $null) "ok"
        Add-Result "S07" "post_checkin" $ok $note
    } catch { Add-Result "S07" "post_checkin" $false $_.Exception.Message }
}

# ---- S08: Estado cuenta + Cobro ----------------------------------
Write-Host ""
Write-Host "-- S08: Cobranzas y Pedidos --" -ForegroundColor DarkGray

$cEnc = [uri]::EscapeDataString($ClienteId)

try {
    $cuenta = Invoke-B3Get -Url "$C.get_estado_cuenta?id_cliente=$cEnc" -CookieFile $cookieCom
    $ok = ($null -ne $cuenta.message)
    $bloq  = Coalesce (Get-Prop $cuenta.message "bloqueado_para_venta" $null) "N/A"
    $saldo = Coalesce (Get-Prop $cuenta.message "saldo_vencido" $null) "0"
    Add-Result "S08" "get_estado_cuenta" $ok "bloqueado=$bloq saldo=$saldo"
} catch { Add-Result "S08" "get_estado_cuenta" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

if ($IncludeWriteOps) {
    try {
        $ref = "SMOKE-$(Get-Date -Format 'HHmmss')"
        $cobro = Invoke-B3Post -Url "$C.post_cobro" -Body @{ id_cliente=$ClienteId; monto="500"; modo_pago="Espece"; referencia=$ref } -CookieFile $cookieCom
        $ok = ($null -ne $cobro.message -and (Get-Prop $cobro.message "status" $null) -ne "error")
        $note = Coalesce (Get-Prop $cobro.message "payment_entry" $null) (Get-Prop $cobro.message "status" $null) (Get-Prop $cobro.message "error_code" $null)
        if (-not $note) { $note = "ok" }
        Add-Result "S08" "post_cobro" $ok $note
    } catch { Add-Result "S08" "post_cobro" $false $_.Exception.Message }

    try {
        $pj = '[{"id_cliente":"' + $ClienteId + '","items":[{"item_code":"PT-TEST-B3-ITEM-A","qty":1,"rate":150}]}]'
        $sync = Invoke-B3Post -Url "$C.sync_pedidos_offline" -Body @{ pedidos=$pj } -CookieFile $cookieCom
        $ok = ($null -ne $sync.message)
        $note = Coalesce (Get-Prop $sync.message "created" $null) (Get-Prop $sync.message "status" $null) "ok"
        Add-Result "S08" "sync_pedidos_offline" $ok $note
    } catch { Add-Result "S08" "sync_pedidos_offline" $false $_.Exception.Message }
}

# ---- S09: Picking FEFO -------------------------------------------
Write-Host ""
Write-Host "-- S09: Picking FEFO --" -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($SalesOrder)) {
    try {
        $soUrl = "$BaseUrl/api/resource/Sales%20Order?filters=%5B%5B%22docstatus%22%2C%22%3D%22%2C1%5D%5D&fields=%5B%22name%22%5D&limit=1"
        $soList = Invoke-B3Get -Url $soUrl -CookieFile $cookieCom
        if ($null -ne $soList.data -and $soList.data.Count -gt 0) {
            $SalesOrder = $soList.data[0].name
            Write-Host "  Auto-detected SO: $SalesOrder" -ForegroundColor DarkGray
        }
    } catch { }
}

if (-not [string]::IsNullOrWhiteSpace($SalesOrder)) {
    $soEnc = [uri]::EscapeDataString($SalesOrder)
    try {
        $pick = Invoke-B3Get -Url "$L.get_pick_list?sales_order=$soEnc" -CookieFile $cookieCom
        $ok = ($null -ne $pick.message)
        $arr = Get-Prop $pick.message "items" $null
        $cnt = if ($null -ne $arr) { $arr.Count } else { "0" }
        Add-Result "S09" "get_pick_list" $ok "items=$cnt SO=$SalesOrder"
    } catch { Add-Result "S09" "get_pick_list" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

    try {
        $scan = Invoke-B3Post -Url "$L.validar_scan_fefo" -Body @{ sales_order=$SalesOrder; item_code=$ItemCodeFefo; batch_scanned=$BatchFefo; qty_ya_escaneada="0" } -CookieFile $cookieCom
        $ok = ($null -ne $scan.message)
        $valido = Coalesce (Get-Prop $scan.message "valido" $null) (Get-Prop $scan.message "status" $null) "N/A"
        Add-Result "S09" "validar_scan_fefo" $ok "valido=$valido"
    } catch { Add-Result "S09" "validar_scan_fefo" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }
} else {
    Add-Result "S09" "get_pick_list"     $false "Sin SO: pasar -SalesOrder SAL-ORD-2026-XXXXX"
    Add-Result "S09" "validar_scan_fefo" $false "Skipped (sin SO)"
}

# ---- S10: Chofer POD ---------------------------------------------
Write-Host ""
Write-Host "-- S10: Chofer POD --" -ForegroundColor DarkGray

try {
    $entregas = Invoke-B3Get -Url "$L.get_entregas_pendientes_chofer?limit=10" -CookieFile $cookieChofer
    $ok = ($null -ne $entregas.message)
    $arr = Get-Prop $entregas.message "entregas" $null
    $total = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S10" "get_entregas_pendientes_chofer" $ok "total=$total (seed pendiente)"
} catch { Add-Result "S10" "get_entregas_pendientes_chofer" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

# ---- S11: Portal B2B + Loyalty -----------------------------------
Write-Host ""
Write-Host "-- S11: Portal B2B + Loyalty --" -ForegroundColor DarkGray

try {
    $dash = Invoke-B3Get -Url "$C.get_portal_dashboard?id_cliente=$cEnc" -CookieFile $cookieCom
    $ok = ($null -ne $dash.message)
    $bloq30 = Coalesce (Get-Prop $dash.message "bloqueado_30_dias" $null) "N/A"
    Add-Result "S11" "get_portal_dashboard" $ok "bloqueado_30d=$bloq30"
} catch { Add-Result "S11" "get_portal_dashboard" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $estado = Invoke-B3Get -Url "$C.get_portal_estado_cuenta?id_cliente=$cEnc" -CookieFile $cookieCom
    $ok = ($null -ne $estado.message)
    $arr = Get-Prop $estado.message "facturas" $null
    $fct = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S11" "get_portal_estado_cuenta" $ok "facturas=$fct"
} catch { Add-Result "S11" "get_portal_estado_cuenta" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $loyalty = Invoke-B3Get -Url "$C.get_loyalty_points?id_cliente=$cEnc" -CookieFile $cookieCom
    $ok = ($null -ne $loyalty.message)
    $saldoObj = Get-Prop $loyalty.message "saldo" $null
    $pts = if ($null -ne $saldoObj) { Get-Prop $saldoObj "saldo_puntos" "0" } else { "N/A" }
    Add-Result "S11" "get_loyalty_points" $ok "saldo=$pts pts"
} catch { Add-Result "S11" "get_loyalty_points" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

if ($IncludeWriteOps) {
    try {
        $ij = '[{"item_code":"PT-TEST-B3-ITEM-A","qty":1}]'
        $pedido = Invoke-B3Post -Url "$C.crear_pedido_portal" -Body @{ id_cliente=$ClienteId; items=$ij } -CookieFile $cookieCom
        $ok = ($null -ne $pedido.message -and (Get-Prop $pedido.message "status" $null) -ne "error")
        $note = Coalesce (Get-Prop $pedido.message "sales_order" $null) (Get-Prop $pedido.message "error_code" $null) "ok"
        Add-Result "S11" "crear_pedido_portal" $ok $note
    } catch { Add-Result "S11" "crear_pedido_portal" $false $_.Exception.Message }

    try {
        $redimir = Invoke-B3Post -Url "$C.redimir_puntos" -Body @{ id_cliente=$ClienteId; puntos="10" } -CookieFile $cookieCom
        $ok = ($null -ne $redimir.message -and (Get-Prop $redimir.message "status" $null) -ne "error")
        $desc = Coalesce (Get-Prop $redimir.message "descuento_aplicado_mad" $null) "N/A"
        Add-Result "S11" "redimir_puntos" $ok "descuento=$desc MAD"
    } catch { Add-Result "S11" "redimir_puntos" $false $_.Exception.Message }
}

# ---- S12: Panel Gerencial 360 (requiere login admin) ----------------
Write-Host ""
Write-Host "-- S12: Panel Gerencial 360 (admin session) --" -ForegroundColor DarkGray
$fechaHoy = (Get-Date -Format "yyyy-MM-dd")

try {
    $panel = Invoke-B3Get -Url "$G.get_panel_gerencial_360?fecha=$fechaHoy" -CookieFile $cookieAdmin
    $ok = ($null -ne $panel.message)
    $hitRate = Coalesce (Get-Prop $panel.message "hit_rate_hoy" $null) (Get-Prop $panel.message "visitas_hoy" $null) "0"
    Add-Result "S12" "get_panel_gerencial_360" $ok "hit_rate=$hitRate"
} catch { Add-Result "S12" "get_panel_gerencial_360" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $mapa = Invoke-B3Get -Url "$G.get_cobertura_mapa?fecha=$fechaHoy" -CookieFile $cookieAdmin
    $ok = ($null -ne $mapa.message)
    $arr = Get-Prop $mapa.message "checkins" $null
    $pts = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S12" "get_cobertura_mapa" $ok "checkins=$pts"
} catch { Add-Result "S12" "get_cobertura_mapa" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $fotos = Invoke-B3Get -Url "$G.get_reporte_fotos_competencia?limit=5" -CookieFile $cookieAdmin
    $ok = ($null -ne $fotos.message)
    $arr = Get-Prop $fotos.message "fotos" $null
    $total = if ($null -ne $arr) { $arr.Count } else { "0" }
    Add-Result "S12" "get_reporte_fotos_competencia" $ok "fotos=$total"
} catch { Add-Result "S12" "get_reporte_fotos_competencia" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

try {
    $csv = Invoke-B3Get -Url "$G.export_scorecard_csv?fecha=$fechaHoy" -CookieFile $cookieAdmin
    $ok = ($null -ne $csv.message)
    $csvB64 = Get-Prop $csv.message "csv_b64" $null
    $note = if ($null -ne $csvB64 -and "$csvB64" -ne "") { "csv_ok (base64)" } else { Coalesce (Get-Prop $csv.message "error_code" $null) "N/A" }
    Add-Result "S12" "export_scorecard_csv" $ok $note
} catch { Add-Result "S12" "export_scorecard_csv" $false "$($_.Exception.Message.Substring(0,[Math]::Min(80,$_.Exception.Message.Length)))" }

# ---- RESUMEN ----------------------------------------------------
$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  RESULTADO BLOQUE 3" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
$results | Format-Table -AutoSize -Property Sprint, Step, Status, Note
$resColor = if ($failed -gt 0) { "Red" } else { "Green" }
Write-Host ("  PASS={0}  FAIL={1}  TOTAL={2}" -f $passed, $failed, $results.Count) -ForegroundColor $resColor
Write-Host ""

if ($failed -gt 0) {
    Write-Host "DIAGNOSTICO:" -ForegroundColor Yellow
    Write-Host "  SETUP admin FAIL  -> Verificar credenciales -AdminUser/-AdminPwd" -ForegroundColor Yellow
    Write-Host "  S08 post_cobro    -> Puede necesitar Sales Person o Payment Account configurado" -ForegroundColor Yellow
    Write-Host "  S11 loyalty FAIL  -> Loyalty Program no configurado en ERPNext" -ForegroundColor Yellow
    Write-Host "  S12 FAIL          -> Verificar que login_admin sea PASS" -ForegroundColor Yellow
}

Remove-Item $cookieCom    -ErrorAction SilentlyContinue
Remove-Item $cookieChofer -ErrorAction SilentlyContinue
Remove-Item $cookieAdmin  -ErrorAction SilentlyContinue

exit ([int]($failed -gt 0))