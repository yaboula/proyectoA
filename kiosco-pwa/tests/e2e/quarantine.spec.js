import { expect, test } from '@playwright/test'
import { loginToRoute, submitManualValue } from './helpers/kiosco'

test.describe('Quarantine flow', () => {
  test('@block2 transfers an approved lot out of quarantine', async ({ page }) => {
    await loginToRoute(page, '/traslado-cuarentena')

    const infoResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'GET'
        && response.url().includes('gcma_kiosco.api.kiosco.info_lote')
    })

    await submitManualValue(page, 'LOTE-QA-RECEP-0001', 'LOT-2026-0001')
    const infoResponse = await infoResponsePromise
    expect(infoResponse.ok()).toBeTruthy()

    await expect(page.getByText('LOTE-QA-RECEP-0001')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: /transferer vers mp approuvee/i })).toBeEnabled()

    const transferResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.trasladar_lote_aprobado')
    })

    await page.getByRole('button', { name: /transferer vers mp approuvee/i }).click()
    const transferResponse = await transferResponsePromise
    expect(transferResponse.ok()).toBeTruthy()

    const transferPayload = await transferResponse.json()
    expect(transferPayload?.message?.success).toBeTruthy()
    await expect(page.getByText(/Lot transfere via MAT-STE-/i)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('button', { name: /transferer vers mp approuvee/i })).toBeDisabled()
  })
})