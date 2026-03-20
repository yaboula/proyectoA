/**
 * E2E — Sprint 09: Kiosco Picking FEFO
 *
 * Cubre los DoD de fase4.md (líneas 15-21):
 *   S09-A — Login badge logística → redirige a /picking-fefo
 *   S09-B — Introducir SAL-ORD → pick list carga con items pendientes
 *   S09-C — Primer batch sugerido: B3-FEFO-NEAR-001 (FEFO prioritario)
 *   S09-D — Escanear NEAR-001 → "Scan accepté" verde
 *   S09-E — Escanear FAR-001 primero → modal Override FEFO aparece (ámbar)
 *   S09-F — Override modal → PIN encargado → "Autoriser override" → éxito
 *
 * Datos de test (seed):
 *   Badge logística : CHOFER-2026-BADGE-00088
 *   Sales Order     : SAL-ORD-2026-00003 (Droguerie Atlas Test, To Deliver and Bill)
 *   Item A          : PT-TEST-B3-ITEM-A
 *   Batch FEFO correcto : B3-FEFO-NEAR-001 (expiry 2026-04-18, prioritario)
 *   Batch FEFO lejano   : B3-FEFO-FAR-001  (expiry 2026-09-15)
 *   Manager PIN     : OP-2026-BADGE-00042  (operario.poc@gcma.local, rol Stock Manager)
 */

import { test, expect } from '@playwright/test'

const LOGISTICA_BADGE = process.env.PLAYWRIGHT_LOGISTICA_BADGE ?? 'CHOFER-2026-BADGE-00088'
const SALES_ORDER     = process.env.PLAYWRIGHT_SO_FEFO       ?? 'SAL-ORD-2026-00003'
const ITEM_CODE       = 'PT-TEST-B3-ITEM-A'
const BATCH_NEAR      = 'B3-FEFO-NEAR-001'   // FEFO correcto (más antiguo)
const BATCH_FAR       = 'B3-FEFO-FAR-001'    // Violación FEFO
const MANAGER_PIN     = process.env.PLAYWRIGHT_MANAGER_PIN ?? 'OP-2026-BADGE-00042'

// ── Helper: login con badge logística ─────────────────────────────────────────
async function loginLogistica(page) {
  await page.goto('/')
  await page.waitForSelector('button', { timeout: 10_000 })
  await page.getByRole('button', { name: /saisie manuelle/i }).click()
  const input = page.getByPlaceholder(/OP-2026-BADGE|COM-2026-BADGE|CHOFER/i).or(
    page.locator('input[type="text"]').last()
  )
  await input.fill(LOGISTICA_BADGE)
  await page.getByRole('button', { name: /^valider$/i }).click()
  await page.waitForURL(/\/picking-fefo|\/hub/, { timeout: 20_000 })
}

// ── Helper: cargar el pick list ────────────────────────────────────────────────
async function loadPickList(page) {
  await page.goto('/picking-fefo')
  await page.waitForURL(/\/picking-fefo/, { timeout: 10_000 })

  const input = page.locator('input[placeholder="SO-00998"]').or(
    page.locator('input[type="text"]').first()
  )
  await input.fill(SALES_ORDER)
  await page.getByRole('button', { name: /Charger/i }).click()

  // Esperar a que la pick list cargue (el panel "Articles à préparer" aparece)
  await expect(page.getByText(/Articles à préparer/i)).toBeVisible({ timeout: 15_000 })
}

// ── S09-A: Login logística → /picking-fefo ────────────────────────────────────

test('S09-A — Badge logística redirige a /picking-fefo', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginLogistica(page)

  // Verificar que estamos en la vista de picking
  await expect(page).toHaveURL(/\/picking-fefo/)
  await expect(page.getByText(/Kiosco de Picking/i)).toBeVisible()
  await expect(page.getByText(/Poka-Yoke FEFO/i)).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/S09-A-login-logistica.png', fullPage: false })
})

// ── S09-B: Cargar pick list ────────────────────────────────────────────────────

test('S09-B — Introducir SAL-ORD → pick list carga con items', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  await loginLogistica(page)
  await loadPickList(page)

  // Debe mostrar el cliente y al menos un artículo
  await expect(page.getByText(/Droguerie Atlas Test/i).first()).toBeVisible()
  await expect(page.getByText(/PT-TEST-B3-ITEM-A/i).first()).toBeVisible()
  await expect(page.getByText(/PT-TEST-B3-ITEM-B/i).first()).toBeVisible()

  // Botón "Nouveau bon" debe estar visible (indica que la lista cargó)
  await expect(page.getByRole('button', { name: /Nouveau bon/i })).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/S09-B-pick-list.png', fullPage: false })
})

// ── S09-C: Batch FEFO sugerido visible ────────────────────────────────────────

test('S09-C — Item A muestra B3-FEFO-NEAR-001 como batch FEFO sugerido', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  await loginLogistica(page)
  await loadPickList(page)

  // La fila de ITEM-A debe mostrar el lote FEFO sugerido
  const rowItemA = page.locator('.gcma-data-row').filter({ hasText: /PT-TEST-B3-ITEM-A/ })
  await expect(rowItemA).toBeVisible()
  await expect(rowItemA.getByText(BATCH_NEAR)).toBeVisible()

  // El campo de input de scan debe mostrar el placeholder del lote sugerido
  // Hacer clic en la fila de ITEM-A para activarla
  await rowItemA.click()

  const scanInput = page.locator('input[placeholder*="B3-FEFO"]').or(
    page.locator('input[placeholder*="LOTE"]')
  )
  await expect(scanInput).toBeVisible({ timeout: 5_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/S09-C-fefo-sugerido.png', fullPage: false })
})

// ── S09-D: Escanear NEAR → "Scan accepté" ─────────────────────────────────────

test('S09-D — Escanear B3-FEFO-NEAR-001 → "Scan accepté" verde', async ({ page }) => {
  page.setDefaultTimeout(35_000)
  await loginLogistica(page)
  await loadPickList(page)

  // Activar ITEM-A
  const rowItemA = page.locator('.gcma-data-row').filter({ hasText: /PT-TEST-B3-ITEM-A/ })
  await rowItemA.click()

  // Introducir el batch correcto y validar
  const scanInput = page.locator('input[placeholder*="B3-FEFO"]').or(
    page.locator('input[placeholder*="LOTE"]').or(
      page.locator('input.font-mono').last()
    )
  )
  await scanInput.fill(BATCH_NEAR)
  await page.getByRole('button', { name: /Valider/i }).last().click()

  // Feedback verde "Scan accepté" — el batch aparece en el panel de éxito
  await expect(page.getByText(/Scan accepté/i)).toBeVisible({ timeout: 10_000 })
  // El batch aparece en el mensaje de feedback inline (bg-green-50)
  const successPanel = page.locator('.bg-green-50')
  await expect(successPanel.getByText(new RegExp(BATCH_NEAR))).toBeVisible({ timeout: 5_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/S09-D-scan-accepte.png', fullPage: false })
})

// ── S09-E: Escanear FAR → Override modal ──────────────────────────────────────

test('S09-E — Escanear B3-FEFO-FAR-001 → modal "Override FEFO requis"', async ({ page }) => {
  page.setDefaultTimeout(35_000)
  await loginLogistica(page)
  await loadPickList(page)

  // Activar ITEM-A
  const rowItemA = page.locator('.gcma-data-row').filter({ hasText: /PT-TEST-B3-ITEM-A/ })
  await rowItemA.click()

  // Intentar escanear el batch lejano (FEFO violation)
  const scanInput = page.locator('input[placeholder*="B3-FEFO"]').or(
    page.locator('input[placeholder*="LOTE"]').or(
      page.locator('input.font-mono').last()
    )
  )
  await scanInput.fill(BATCH_FAR)
  await page.getByRole('button', { name: /Valider/i }).last().click()

  // El modal de Override FEFO debe aparecer (ámbar, no overlay rojo)
  const overrideModal = page.locator('.bg-amber-50').filter({ hasText: /Override FEFO requis/i })
  await expect(overrideModal).toBeVisible({ timeout: 10_000 })
  // El modal muestra el batch escaneado (FAR) y el batch esperado (NEAR)
  await expect(overrideModal.getByText(new RegExp(BATCH_FAR))).toBeVisible()
  await expect(overrideModal.getByText(new RegExp(BATCH_NEAR))).toBeVisible()

  // Cancelar para limpiar estado
  await page.getByRole('button', { name: /Annuler/i }).click()
  await expect(page.getByText(/Override FEFO requis/i)).toHaveCount(0, { timeout: 3_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/S09-E-fefo-violation.png', fullPage: false })
})

// ── S09-F: Override modal → PIN → confirmación ────────────────────────────────
// El backend ya fue verificado directamente (override_fefo_batch API test).
// Aquí verificamos el flujo UI: modal → PIN → feedback "Scan accepté".
// Se mockea la respuesta de red para aislar el test de latencias/errores de red.

test('S09-F — Override FEFO con PIN de encargado → autorizado', async ({ page }) => {
  page.setDefaultTimeout(30_000)

  // Capturar errores JS de la app
  const jsErrors = []
  page.on('pageerror', err => jsErrors.push(err.message))

  // Mock del endpoint override_fefo_batch → simula respuesta exitosa del servidor
  // Se usa regex porque la URL tiene puntos (gcma_kiosco.api.logistica.override_fefo_batch)
  await page.route(/override_fefo_batch/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        message: {
          status: 'override_autorizado',
          batch_override: BATCH_FAR,
          autorizado_por: 'operario.poc@gcma.local',
          qty_escaneada_total: 1.0,
          qty_pendiente: 5.0,
          qty_restante: 4.0,
          cierre_parcial: false,
        },
      }),
    })
  })

  await loginLogistica(page)
  await loadPickList(page)

  // Activar ITEM-A
  const rowItemA = page.locator('.gcma-data-row').filter({ hasText: /PT-TEST-B3-ITEM-A/ })
  await rowItemA.click()

  // Provocar violación FEFO
  const scanInput = page.locator('input[placeholder*="B3-FEFO"]').or(
    page.locator('input[placeholder*="LOTE"]').or(
      page.locator('input.font-mono').last()
    )
  )
  await scanInput.fill(BATCH_FAR)
  await page.getByRole('button', { name: /Valider/i }).last().click()

  // Override modal debe aparecer
  await expect(page.getByText(/Override FEFO requis/i)).toBeVisible({ timeout: 10_000 })

  // Introducir PIN del encargado
  const pinInput = page.locator('input[type="password"]')
  await pinInput.click()
  await pinInput.fill(MANAGER_PIN)
  await pinInput.dispatchEvent('input')

  // Botón habilitado → confirmar
  const btnAutoriser = page.getByRole('button', { name: /Autoriser override/i })
  await expect(btnAutoriser).toBeEnabled({ timeout: 3_000 })
  await btnAutoriser.click()

  // Modal debe cerrarse
  await expect(page.getByText(/Override FEFO requis/i)).toHaveCount(0, { timeout: 5_000 })

  // Pequeña pausa para que Vue procese el resultado del override
  await page.waitForTimeout(1000)

  // Diagnóstico: captura el estado del DOM para debug
  await page.screenshot({ path: 'tests/e2e/evidence/S09-F-debug-post-override.png', fullPage: true })

  // Si hay errores JS, reportarlos antes de la aserción final
  if (jsErrors.length > 0) {
    throw new Error(`JS errors after override: ${jsErrors.join(' | ')}`)
  }

  // "Scan accepté" debe aparecer (mock respondió con override_autorizado)
  await expect(page.getByText(/Scan accepté/i)).toBeVisible({ timeout: 8_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/S09-F-override-autorizado.png', fullPage: false })
})
