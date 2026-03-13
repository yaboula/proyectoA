import { expect, test } from '@playwright/test'
import { loginToRoute, submitManualValue } from './helpers/kiosco'

test.describe('Reprint flow', () => {
  test('@block2 reloads label data and prints through the Zebra bridge', async ({ page }) => {
    const printRequests = []

    await page.route('http://localhost:9000/print', async (route) => {
      printRequests.push(route.request().postDataJSON())
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })

    await loginToRoute(page, '/reimpresion')

    const labelResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'GET'
        && response.url().includes('gcma_kiosco.api.recepcion.get_lote_para_impresion')
    })

    await submitManualValue(page, 'LOTE-QA-RECEP-0001', 'LOT-2026-0001')
    const labelResponse = await labelResponsePromise
    expect(labelResponse.ok()).toBeTruthy()

    await expect(page.getByText('LOTE-QA-RECEP-0001', { exact: true }).first()).toBeVisible({ timeout: 20_000 })
    await page.getByRole('button', { name: /imprimer etiquette/i }).click()

    await expect.poll(() => printRequests.length, { timeout: 20_000 }).toBe(1)
    expect(printRequests[0]?.zpl).toContain('LOTE-QA-RECEP-0001')
    await expect(page.getByText(/Etiquette reimprimee pour LOTE-QA-RECEP-0001\./i)).toBeVisible({ timeout: 20_000 })
  })
})