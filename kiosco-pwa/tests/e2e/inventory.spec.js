import { expect, test } from '@playwright/test'
import { loginToRoute, submitManualValue } from './helpers/kiosco'

test.describe('Blind inventory flow', () => {
  test('@block2 counts locally and submits a draft reconciliation', async ({ page }) => {
    await loginToRoute(page, '/inventario-ciego')

    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')
    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')
    await submitManualValue(page, 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0002', 'MP-RES-ALK-G70|LOTE-CIEGO-2026-0001')

    await expect(page.getByText('LOTE-CIEGO-2026-0001')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('LOTE-CIEGO-2026-0002')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/^3$/).first()).toBeVisible()
    await expect(page.getByText(/^2$/).first()).toBeVisible()

    const submitResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.subir_conteo_fisico')
    })

    await page.getByRole('button', { name: /envoyer le comptage/i }).click()
    const submitResponse = await submitResponsePromise
    expect(submitResponse.ok()).toBeTruthy()

    const submitPayload = await submitResponse.json()
    expect(submitPayload?.message?.success).toBeTruthy()
    await expect(page.getByText(new RegExp(`Brouillon cree: ${submitPayload.message.reconciliation_doc}`, 'i'))).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText(/Aucun comptage local/i)).toBeVisible({ timeout: 20_000 })
  })
})