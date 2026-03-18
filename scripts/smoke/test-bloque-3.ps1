<#
.SYNOPSIS
    Smoke test automatizado para Bloque 3 — Comercial B2B & Logística (S07-S12).

.DESCRIPTION
    Golpea los 18 endpoints del Bloque 3 con el patron de los smoke tests existentes.
    Usa sesion de cookies (como el frontend PWA) para simular flujos reales.

.PARAMETER BaseUrl
    URL base de Frappe. Default: http://localhost:8080

.PARAMETER BadgeComercial
    Badge QR del comercial. Default: COM-2026-BADGE-00099

.PARAMETER BadgeChofer
    Badge QR del chofer. Default: CHOFER-2026-BADGE-00088

.PARAMETER ClienteId
    portal_customer_id del cliente B2B. Default: CLI-B2B-TEST-001

.PARAMETER SalesOrder
    Nombre del Sales Order para pruebas de picking (puede ser auto si se deja vacío).

.PARAMETER IncludeWriteOps
    Si se activa, ejecuta POST con efectos (cobro, pedido, etc.). Por defecto solo GETs.

.PARAMETER ItemCodeFefo
    Item code para las pruebas de picking FEFO. Default: PT-TEST-B3-ITEM-A

.PARAMETER BatchFefo
    Batch number para scan FEFO. Default: B3-FEFO-NEAR-001

.EXAMPLE
    # Solo lectura (seguro en produccion):
    .\test-bloque-3.ps1

    # Con operaciones de escritura (solo en sandbox):
    .\test-bloque-3.ps1 -IncludeWriteOps -SalesOrder "SAL-ORD-2026-00001"
#>

param(
    [string]$BaseUrl         = "http://localhost:8080",
    [string]$BadgeComercial  = "COM-2026-BADGE-00099",
    [string]$BadgeChofer     = "CHOFER-2026-BADGE-00088",
    [string]$ClienteId       = "CLI-B2B-TEST-001",
    [string]$SalesOrder      = "",
    [string]$ItemCodeFefo    = "PT-TEST-B3-ITEM-A",
    [string]$BatchFefo       = "B3-FEFO-NEAR-001",
    [switch]$IncludeWriteOps
)

$ErrorActionPreference = "Continue"

# ── Helpers ───────────────────────────────────────────────────────────────────
$results = New-Object 'System.Collections.Generic.List[object]'

function Add-Result {
    param([string]$Sprint, [string]$Step, [bool]$Ok, [string]$Note)
    $status = if ($Ok) { "PASS" } else { "FAIL" }
    $results.Add([pscustomobject]@{ Sprint = $Sprint; Step = $Step; Status = $status; Note = $Note }) | Out-Null
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1,-10} {2,-42} {3}" -f $status, $Sprint, $Step, $Note) -ForegroundColor $color
}

function Invoke-B3 {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Body = @{},
        [Microsoft.PowerShell.Commands.WebRequestSession]$Session
    )
    try {
        if ($Method -eq "GET") {
            $r = Invoke-WebRequest -Method Get -Uri $Url -WebSession $Session -UseBasicParsing -TimeoutSec 20
        } else {
            $r = Invoke-WebRequest -Method Post -Uri $Url -Body $Body -WebSession $Session `
                -ContentType "application/x-www-form-urlencoded" -UseBasicParsing -TimeoutSec 20
        }
        return ($r.Content | ConvertFrom-Json)
    } catch {
        $resp = $_.Exception.Response
        if ($null -ne $resp) {
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $body = $reader.ReadToEnd(); $reader.Close()
            try { return ($body | ConvertFrom-Json) } catch { }
        }
        throw $_
    }
}

# Namespaces a intentar (alias maroc_b2b → gcma_kiosco como fallback)
$KIOSCO_NS  = "$BaseUrl/api/method/gcma_kiosco.api.kiosco"
$COMERCIAL  = "$BaseUrl/api/method/maroc_b2b.api.comercial"
$LOGISTICA  = "$BaseUrl/api/method/maroc_b2b.api.logistica"
$GERENCIAL  = "$BaseUrl/api/method/maroc_b2b.api.gerencial"
# Fallbacks
$COMERCIAL_FB = "$BaseUrl/api/method/gcma_kiosco.api.comercial"
$LOGISTICA_FB = "$BaseUrl/api/method/gcma_kiosco.api.logistica"
$GERENCIAL_FB = "$BaseUrl/api/method/gcma_kiosco.api.gerencial"

$sessionCom   = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$sessionChofer = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# ══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  GCMA Bloque 3 — Smoke Test (S07-S12)  v0.9.2" -ForegroundColor Cyan
Write-Host "  BaseUrl: $BaseUrl" -ForegroundColor Cyan
Write-Host "  WriteOps: $IncludeWriteOps" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── SETUP: Login comercial ────────────────────────────────────────────────────
Write-Host "── SETUP: Login ──────────────────────────────────────────" -ForegroundColor DarkGray
try {
    $loginCom = Invoke-B3 -Method POST -Url "$KIOSCO_NS.login_operario" `
        -Body @{ qr_token = $BadgeComercial } -Session $sessionCom
    $okLogin = $loginCom.message.success -eq $true
    Add-Result "SETUP" "login_comercial" $okLogin ($loginCom.message.message_fr ?? $loginCom.message.error_code ?? "sin msg")
} catch {
    Add-Result "SETUP" "login_comercial" $false $_.Exception.Message
}

try {
    $loginChofer = Invoke-B3 -Method POST -Url "$KIOSCO_NS.login_operario" `
        -Body @{ qr_token = $BadgeChofer } -Session $sessionChofer
    $okChofer = $loginChofer.message.success -eq $true
    Add-Result "SETUP" "login_chofer" $okChofer ($loginChofer.message.message_fr ?? $loginChofer.message.error_code ?? "sin msg")
} catch {
    Add-Result "SETUP" "login_chofer" $false $_.Exception.Message
}

# ── S07: Rutas + Catálogo ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "── S07: Rutas Comerciales + Catálogo ─────────────────────" -ForegroundColor DarkGray

try {
    $ruta = Invoke-B3 -Method GET -Url "$COMERCIAL.get_ruta_dia" -Session $sessionCom
    $ok = $null -ne $ruta.message
    $total = $ruta.message.total_clientes ?? $ruta.message.rutas?.Count ?? "N/A"
    Add-Result "S07" "get_ruta_dia" $ok "total_clientes=$total"
} catch {
    try {
        $ruta = Invoke-B3 -Method GET -Url "$COMERCIAL_FB.get_ruta_dia" -Session $sessionCom
        $ok = $null -ne $ruta.message
        Add-Result "S07" "get_ruta_dia [fb]" $ok "fallback namespace ok"
    } catch {
        Add-Result "S07" "get_ruta_dia" $false $_.Exception.Message
    }
}

try {
    $catalogUrl = "$COMERCIAL.get_catalogo_stock?limit=10"
    $cat = Invoke-B3 -Method GET -Url $catalogUrl -Session $sessionCom
    $ok = $null -ne $cat.message
    $items = $cat.message.items?.Count ?? $cat.message.total ?? "N/A"
    Add-Result "S07" "get_catalogo_stock" $ok "items=$items"
} catch {
    try {
        $cat = Invoke-B3 -Method GET -Url "$COMERCIAL_FB.get_catalogo_stock?limit=10" -Session $sessionCom
        $ok = $null -ne $cat.message
        Add-Result "S07" "get_catalogo_stock [fb]" $ok "fallback ok"
    } catch {
        Add-Result "S07" "get_catalogo_stock" $false $_.Exception.Message
    }
}

try {
    $catSearch = Invoke-B3 -Method GET -Url "$COMERCIAL.get_catalogo_stock?search=test&limit=5" -Session $sessionCom
    $ok = $null -ne $catSearch.message
    Add-Result "S07" "get_catalogo_stock (search)" $ok "search=test ok"
} catch {
    Add-Result "S07" "get_catalogo_stock (search)" $false $_.Exception.Message
}

if ($IncludeWriteOps) {
    try {
        $checkin = Invoke-B3 -Method POST -Url "$COMERCIAL.post_checkin" -Body @{
            id_cliente = $ClienteId
            lat        = "33.5731"
            lng        = "-7.5898"
            notas      = "Smoke test B3"
        } -Session $sessionCom
        $ok = $null -ne $checkin.message
        Add-Result "S07" "post_checkin (write)" $ok ($checkin.message.status ?? $checkin.message.error_code ?? "ok")
    } catch {
        Add-Result "S07" "post_checkin (write)" $false $_.Exception.Message
    }
}

# ── S08: Estado cuenta + Cobro + Pedidos ──────────────────────────────────────
Write-Host ""
Write-Host "── S08: Cobranzas y Pedidos ───────────────────────────────" -ForegroundColor DarkGray

try {
    $cuenta = Invoke-B3 -Method GET -Url "$COMERCIAL.get_estado_cuenta?id_cliente=$ClienteId" -Session $sessionCom
    $ok = $null -ne $cuenta.message
    $bloq = $cuenta.message.bloqueado_para_venta ?? "N/A"
    $saldo = $cuenta.message.saldo_vencido ?? "N/A"
    Add-Result "S08" "get_estado_cuenta" $ok "bloqueado=$bloq saldo_vencido=$saldo"
} catch {
    Add-Result "S08" "get_estado_cuenta" $false $_.Exception.Message
}

if ($IncludeWriteOps) {
    try {
        $cobro = Invoke-B3 -Method POST -Url "$COMERCIAL.post_cobro" -Body @{
            id_cliente = $ClienteId
            monto      = "500"
            modo_pago  = "Cash"
            referencia = "SMOKE-TEST-$(Get-Date -Format 'HHmmss')"
        } -Session $sessionCom
        $ok = $null -ne $cobro.message -and $cobro.message.status -ne "error"
        Add-Result "S08" "post_cobro (write)" $ok ($cobro.message.payment_entry ?? $cobro.message.error_code ?? "ok")
    } catch {
        Add-Result "S08" "post_cobro (write)" $false $_.Exception.Message
    }

    try {
        $pedidosJson = '[{"id_cliente":"' + $ClienteId + '","items":[{"item_code":"PT-TEST-B3-ITEM-A","qty":1,"rate":150}]}]'
        $sync = Invoke-B3 -Method POST -Url "$COMERCIAL.sync_pedidos_offline" -Body @{
            pedidos = $pedidosJson
        } -Session $sessionCom
        $ok = $null -ne $sync.message
        Add-Result "S08" "sync_pedidos_offline (write)" $ok ($sync.message.created ?? $sync.message.status ?? "ok")
    } catch {
        Add-Result "S08" "sync_pedidos_offline (write)" $false $_.Exception.Message
    }
}

# ── S09: Picking FEFO ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "── S09: Picking FEFO + Override PIN ──────────────────────" -ForegroundColor DarkGray

# Auto-detect Sales Order si no fue especificado
if ([string]::IsNullOrWhiteSpace($SalesOrder)) {
    try {
        $encodedFilters = [uri]::EscapeDataString('[[&quot;docstatus&quot;,&quot;=&quot;,1]]')
        $soListUrl = "$BaseUrl/api/resource/Sales%20Order?filters=%5B%5B%22docstatus%22%2C%22%3D%22%2C1%5D%5D&fields=%5B%22name%22%5D&limit=1"
        $soList = Invoke-B3 -Method GET -Url $soListUrl -Session $sessionCom
        $SalesOrder = $soList.data[0].name ?? ""
        if ($SalesOrder) { Write-Host "  Auto-detected SO: $SalesOrder" -ForegroundColor DarkGray }
    } catch { }
}

if ($SalesOrder) {
    try {
        $pickUrl = "$LOGISTICA.get_pick_list?sales_order=$([uri]::EscapeDataString($SalesOrder))"
        $pick = Invoke-B3 -Method GET -Url $pickUrl -Session $sessionCom
        $ok = $null -ne $pick.message
        $itemCount = $pick.message.items?.Count ?? $pick.message.total_items ?? "N/A"
        Add-Result "S09" "get_pick_list" $ok "items=$itemCount SO=$SalesOrder"
    } catch {
        try {
            $pick = Invoke-B3 -Method GET -Url "$LOGISTICA_FB.get_pick_list?sales_order=$([uri]::EscapeDataString($SalesOrder))" -Session $sessionCom
            $ok = $null -ne $pick.message
            Add-Result "S09" "get_pick_list [fb]" $ok "fallback ok"
        } catch {
            Add-Result "S09" "get_pick_list" $false $_.Exception.Message
        }
    }

    try {
        $scanUrl = "$LOGISTICA.validar_scan_fefo"
        $scan = Invoke-B3 -Method POST -Url $scanUrl -Body @{
            sales_order       = $SalesOrder
            item_code         = $ItemCodeFefo
            batch_scanned     = $BatchFefo
            qty_ya_escaneada  = "0"
        } -Session $sessionCom
        $ok = $null -ne $scan.message
        $valido = $scan.message.valido ?? $scan.message.status ?? "N/A"
        Add-Result "S09" "validar_scan_fefo" $ok "valido=$valido"
    } catch {
        Add-Result "S09" "validar_scan_fefo" $false $_.Exception.Message
    }
} else {
    Add-Result "S09" "get_pick_list" $false "No SalesOrder disponible. Usar -SalesOrder XXXX o ejecutar seed-bloque-3.py primero"
    Add-Result "S09" "validar_scan_fefo" $false "Skipped (no SO)"
}

# ── S10: Chofer + POD ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "── S10: Chofer POD ────────────────────────────────────────" -ForegroundColor DarkGray

try {
    $entregas = Invoke-B3 -Method GET -Url "$LOGISTICA.get_entregas_pendientes_chofer?limit=10" -Session $sessionChofer
    $ok = $null -ne $entregas.message
    $total = $entregas.message.entregas?.Count ?? $entregas.message.total ?? "N/A"
    Add-Result "S10" "get_entregas_pendientes_chofer" $ok "total_entregas=$total"
} catch {
    try {
        $entregas = Invoke-B3 -Method GET -Url "$LOGISTICA_FB.get_entregas_pendientes_chofer?limit=10" -Session $sessionChofer
        $ok = $null -ne $entregas.message
        Add-Result "S10" "get_entregas_pendientes_chofer [fb]" $ok "fallback ok"
    } catch {
        Add-Result "S10" "get_entregas_pendientes_chofer" $false $_.Exception.Message
    }
}

# ── S11: Portal B2B + Loyalty ─────────────────────────────────────────────────
Write-Host ""
Write-Host "── S11: Portal B2B + Loyalty ──────────────────────────────" -ForegroundColor DarkGray

try {
    $dash = Invoke-B3 -Method GET -Url "$COMERCIAL.get_portal_dashboard?id_cliente=$ClienteId" -Session $sessionCom
    $ok = $null -ne $dash.message
    $bloq30 = $dash.message.bloqueado_30_dias ?? "N/A"
    Add-Result "S11" "get_portal_dashboard" $ok "bloqueado_30d=$bloq30"
} catch {
    Add-Result "S11" "get_portal_dashboard" $false $_.Exception.Message
}

try {
    $estado = Invoke-B3 -Method GET -Url "$COMERCIAL.get_portal_estado_cuenta?id_cliente=$ClienteId" -Session $sessionCom
    $ok = $null -ne $estado.message
    $factTotal = $estado.message.facturas?.Count ?? "N/A"
    Add-Result "S11" "get_portal_estado_cuenta" $ok "facturas=$factTotal"
} catch {
    Add-Result "S11" "get_portal_estado_cuenta" $false $_.Exception.Message
}

try {
    $loyalty = Invoke-B3 -Method GET -Url "$COMERCIAL.get_loyalty_points?id_cliente=$ClienteId" -Session $sessionCom
    $ok = $null -ne $loyalty.message
    $saldo = $loyalty.message.saldo?.saldo_puntos ?? "N/A"
    Add-Result "S11" "get_loyalty_points" $ok "saldo=$saldo pts"
} catch {
    Add-Result "S11" "get_loyalty_points" $false $_.Exception.Message
}

if ($IncludeWriteOps) {
    try {
        $itemsJson = '[{"item_code":"PT-TEST-B3-ITEM-A","qty":1}]'
        $pedido = Invoke-B3 -Method POST -Url "$COMERCIAL.crear_pedido_portal" -Body @{
            id_cliente = $ClienteId
            items      = $itemsJson
        } -Session $sessionCom
        $ok = $null -ne $pedido.message -and $pedido.message.status -ne "error"
        Add-Result "S11" "crear_pedido_portal (write)" $ok ($pedido.message.sales_order ?? $pedido.message.error_code ?? "ok")
    } catch {
        Add-Result "S11" "crear_pedido_portal (write)" $false $_.Exception.Message
    }

    try {
        $redimir = Invoke-B3 -Method POST -Url "$COMERCIAL.redimir_puntos" -Body @{
            id_cliente = $ClienteId
            puntos     = "10"
        } -Session $sessionCom
        $ok = $null -ne $redimir.message -and $redimir.message.status -ne "error"
        $desc = $redimir.message.descuento_aplicado_mad ?? "N/A"
        Add-Result "S11" "redimir_puntos (write)" $ok "descuento=${desc} MAD"
    } catch {
        Add-Result "S11" "redimir_puntos (write)" $false $_.Exception.Message
    }
}

# ── S12: Panel Gerencial 360° ─────────────────────────────────────────────────
Write-Host ""
Write-Host "── S12: Panel Gerencial 360° ──────────────────────────────" -ForegroundColor DarkGray
$fechaHoy = (Get-Date -Format "yyyy-MM-dd")

try {
    $panel = Invoke-B3 -Method GET -Url "$GERENCIAL.get_panel_gerencial_360?fecha=$fechaHoy" -Session $sessionCom
    $ok = $null -ne $panel.message
    $hitRate = $panel.message.hit_rate_hoy ?? $panel.message.visitas_hoy ?? "N/A"
    Add-Result "S12" "get_panel_gerencial_360" $ok "hit_rate=$hitRate"
} catch {
    try {
        $panel = Invoke-B3 -Method GET -Url "$GERENCIAL_FB.get_panel_gerencial_360?fecha=$fechaHoy" -Session $sessionCom
        Add-Result "S12" "get_panel_gerencial_360 [fb]" ($null -ne $panel.message) "fallback ok"
    } catch {
        Add-Result "S12" "get_panel_gerencial_360" $false $_.Exception.Message
    }
}

try {
    $mapa = Invoke-B3 -Method GET -Url "$GERENCIAL.get_cobertura_mapa?fecha=$fechaHoy" -Session $sessionCom
    $ok = $null -ne $mapa.message
    $puntos = $mapa.message.checkins?.Count ?? $mapa.message.puntos?.Count ?? "N/A"
    Add-Result "S12" "get_cobertura_mapa" $ok "checkins=$puntos"
} catch {
    Add-Result "S12" "get_cobertura_mapa" $false $_.Exception.Message
}

try {
    $fotos = Invoke-B3 -Method GET -Url "$GERENCIAL.get_reporte_fotos_competencia?limit=5" -Session $sessionCom
    $ok = $null -ne $fotos.message
    $total = $fotos.message.fotos?.Count ?? $fotos.message.total ?? "N/A"
    Add-Result "S12" "get_reporte_fotos_competencia" $ok "fotos=$total"
} catch {
    Add-Result "S12" "get_reporte_fotos_competencia" $false $_.Exception.Message
}

try {
    $csvUrl = "$GERENCIAL.export_scorecard_csv?fecha=$fechaHoy"
    $csv = Invoke-B3 -Method GET -Url $csvUrl -Session $sessionCom
    $ok = $null -ne $csv.message
    Add-Result "S12" "export_scorecard_csv" $ok ($csv.message.csv_b64 ? "csv_ok (base64)" : ($csv.message.error_code ?? "N/A"))
} catch {
    Add-Result "S12" "export_scorecard_csv" $false $_.Exception.Message
}

# ── RESUMEN ───────────────────────────────────────────────────────────────────
$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$total  = $results.Count

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  RESULTADO BLOQUE 3" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
$results | Format-Table -AutoSize -Property Sprint, Step, Status, Note
Write-Host ("  PASS={0}  FAIL={1}  TOTAL={2}" -f $passed, $failed, $total) -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($failed -gt 0) {
    Write-Host "DIAGNÓSTICO RÁPIDO:" -ForegroundColor Yellow
    Write-Host "  • SETUP FAIL  → Badge no existe. Ejecutar seed-bloque-3.py en Docker." -ForegroundColor Yellow
    Write-Host "  • S07 FAIL    → Namespace maroc_b2b no registrado. Verificar hooks.py." -ForegroundColor Yellow
    Write-Host "  • S09 FAIL    → Pasar -SalesOrder con un SO confirmado válido." -ForegroundColor Yellow
    Write-Host "  • S12 FAIL    → El comercial no tiene Sales Person vinculado al Employee." -ForegroundColor Yellow
}

exit $([int]($failed -gt 0))
