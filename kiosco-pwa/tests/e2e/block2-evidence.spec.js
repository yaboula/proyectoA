import fs from 'node:fs/promises'
import path from 'node:path'
import { expect, test } from '@playwright/test'
import { loginToRoute, submitManualValue } from './helpers/kiosco'

const evidenceDir = path.resolve(process.cwd(), 'evidence', 'block2')
const evidenceJsonPath = path.join(evidenceDir, 'evidence.json')

test.describe('Block 2 evidence pack', () => {
  test('captures screenshots and ERP doc IDs for reception, quarantine, reprint and blind inventory', async ({ page }) => {
    await fs.mkdir(evidenceDir, { recursive: true })

    const evidence = {
      generated_at: new Date().toISOString(),
      reception: {},
      quarantine: {},
      reprint: {},
      inventory: {},
    }

    await page.goto('/')
    await page.getByRole('button', { name: /saisie manuelle/i }).click()
    await page.getByPlaceholder('OP-2026-BADGE-00042').fill(process.env.PLAYWRIGHT_BADGE_TOKEN ?? 'OP-2026-BADGE-00042')
    await page.getByRole('button', { name: /^valider$/i }).click()
    await page.waitForURL(/\/hub|\/tareas/, { timeout: 15_000 })
    await page.screenshot({ path: path.join(evidenceDir, '01-login-kiosco.png'), fullPage: true })

    await page.goto('/recepcion')
    const firstOrderCard = page.locator('article.kiosk-panel').first()
    await expect(firstOrderCard).toBeVisible({ timeout: 20_000 })

    const orderName = (await firstOrderCard.getByRole('heading').textContent())?.trim() ?? ''
    const preferredItemRow = firstOrderCard.locator('.gcma-data-row', { hasText: 'ENV-BID-20L-BLC' }).first()
    const firstItemRow = (await preferredItemRow.count()) ? preferredItemRow : firstOrderCard.locator('.gcma-data-row').last()
    const itemCodeText = (await firstItemRow.locator('.text-sm.text-zinc-500').first().textContent())?.trim() ?? ''
    const pendingBeforeLabel = await firstItemRow.locator('text=/Reliquat/i').first().textContent()
    const pendingBefore = extractPendingQty(pendingBeforeLabel)

    evidence.reception.purchase_order = orderName
    evidence.reception.item_code = itemCodeText
    evidence.reception.pending_before = pendingBefore

    await page.screenshot({ path: path.join(evidenceDir, '02-reception-before-reliquat.png'), fullPage: true })

    await firstItemRow.getByRole('button', { name: /receptionner/i }).click()
    await page.locator('input[type="number"]').fill('1')

    const receptionResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.registrar_recepcion')
    })

    await page.getByRole('button', { name: /valider la reception/i }).click()
    const receptionResponse = await receptionResponsePromise
    expect(receptionResponse.ok()).toBeTruthy()

    const receptionPayload = await receptionResponse.json()
    const prName = receptionPayload?.message?.purchase_receipt
    evidence.reception.purchase_receipt = prName ?? null

    const reloadedOrder = page.locator('article.kiosk-panel', { has: page.getByRole('heading', { name: orderName }) }).first()
    await expect(reloadedOrder).toBeVisible({ timeout: 20_000 })
    const reloadedItemRow = reloadedOrder.locator('.gcma-data-row', { hasText: itemCodeText }).first()
    await expect(reloadedItemRow).toBeVisible({ timeout: 20_000 })

    const pendingAfterLabel = await reloadedItemRow.locator('text=/Reliquat/i').first().textContent()
    const pendingAfter = extractPendingQty(pendingAfterLabel)
    evidence.reception.pending_after = pendingAfter

    await page.screenshot({ path: path.join(evidenceDir, '03-reception-after-reliquat.png'), fullPage: true })

    await page.goto('/traslado-cuarentena')
    const lotInfoResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'GET'
        && response.url().includes('gcma_kiosco.api.kiosco.info_lote')
    })

    await submitManualValue(page, 'LOTE-QA-RECEP-0001', 'LOT-2026-0001')
    const lotInfoResponse = await lotInfoResponsePromise
    expect(lotInfoResponse.ok()).toBeTruthy()
    await expect(page.getByText('LOTE-QA-RECEP-0001')).toBeVisible({ timeout: 20_000 })

    await page.screenshot({ path: path.join(evidenceDir, '04-cuarentena-before-transfer.png'), fullPage: true })

    const transferResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.trasladar_lote_aprobado')
    })

    await page.getByRole('button', { name: /transferer vers mp approuvee/i }).click()
    const transferResponse = await transferResponsePromise
    expect(transferResponse.ok()).toBeTruthy()

    const transferPayload = await transferResponse.json()
    evidence.quarantine.stock_entry = transferPayload?.message?.stock_entry ?? null
    await expect(page.getByText(/Lot transfere via MAT-STE-/i)).toBeVisible({ timeout: 20_000 })

    await page.screenshot({ path: path.join(evidenceDir, '05-cuarentena-transfer-success.png'), fullPage: true })

    await page.goto('/reimpresion')
    const reprintDataResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'GET'
        && response.url().includes('gcma_kiosco.api.recepcion.get_lote_para_impresion')
    })

    await submitManualValue(page, 'LOTE-QA-RECEP-0001', 'LOT-2026-0001')
    const reprintDataResponse = await reprintDataResponsePromise
    expect(reprintDataResponse.ok()).toBeTruthy()

    const reprintPayload = await reprintDataResponse.json()
    evidence.reprint.batch_no = reprintPayload?.message?.etiqueta?.batch_no ?? null
    evidence.reprint.item_code = reprintPayload?.message?.etiqueta?.item_code ?? null
    evidence.reprint.item_name = reprintPayload?.message?.etiqueta?.item_name ?? null
    evidence.reprint.expiry_date = reprintPayload?.message?.etiqueta?.expiry_date ?? null

    await page.screenshot({ path: path.join(evidenceDir, '06-reprint-data-loaded.png'), fullPage: true })

    let printMode = 'success'
    await page.route('http://localhost:9000/print', async (route) => {
      if (printMode === 'success') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        })
        return
      }

      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ success: false, error: 'BRIDGE_DOWN' }),
      })
    })

    await page.getByRole('button', { name: /imprimer etiquette/i }).click()
    await expect(page.getByText(/Etiquette reimprimee pour LOTE-QA-RECEP-0001\./i)).toBeVisible({ timeout: 20_000 })
    evidence.reprint.bridge_active_message = 'Etiquette reimprimee pour LOTE-QA-RECEP-0001.'

    await page.screenshot({ path: path.join(evidenceDir, '07-reprint-print-success.png'), fullPage: true })

    printMode = 'error'
    await page.getByRole('button', { name: /imprimer etiquette/i }).click()
    await expect(page.getByText(/PRINT_HTTP_503/i)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('LOTE-QA-RECEP-0001', { exact: true }).first()).toBeVisible({ timeout: 20_000 })
    evidence.reprint.bridge_down_message = 'PRINT_HTTP_503'

    await page.screenshot({ path: path.join(evidenceDir, '08-reprint-print-controlled-error.png'), fullPage: true })

    await page.goto('/inventario-ciego')

    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')
    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')
    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0002', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')

    await expect(page.getByText('LOTE-CIEGO-2026-0001')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('LOTE-CIEGO-2026-0002')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/^3$/).first()).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/^2$/).first()).toBeVisible({ timeout: 20_000 })

    evidence.inventory.scans_before_submit = 3
    evidence.inventory.distinct_lots_before_submit = 2

    await page.screenshot({ path: path.join(evidenceDir, '09-inventory-before-submit.png'), fullPage: true })

    const inventorySubmitResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.subir_conteo_fisico')
    })

    await page.getByRole('button', { name: /envoyer le comptage/i }).click()
    const inventorySubmitResponse = await inventorySubmitResponsePromise
    expect(inventorySubmitResponse.ok()).toBeTruthy()

    const inventoryPayload = await inventorySubmitResponse.json()
    const reconciliationDoc = inventoryPayload?.message?.reconciliation_doc
    evidence.inventory.reconciliation_doc = reconciliationDoc ?? null

    await expect(page.getByText(new RegExp(`Brouillon cree: ${reconciliationDoc}`, 'i'))).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/Aucun comptage local/i)).toBeVisible({ timeout: 20_000 })

    await page.screenshot({ path: path.join(evidenceDir, '10-inventory-submit-success.png'), fullPage: true })

    await fs.writeFile(evidenceJsonPath, JSON.stringify(evidence, null, 2), 'utf-8')
  })
})

function extractPendingQty(label) {
  const match = String(label ?? '').match(/Reliquat\s+([0-9]+(?:[.,][0-9]+)?)/i)
  if (!match) {
    throw new Error(`Unable to parse pending quantity from label: ${label}`)
  }

  return Number(match[1].replace(',', '.'))
}
