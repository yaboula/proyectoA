import { expect, test } from '@playwright/test'
import { loginToRoute } from './helpers/kiosco'

test.describe('Reception flow', () => {
  test('@block2 keeps the purchase order visible after a partial reception', async ({ page }) => {
    await loginToRoute(page, '/recepcion')

    const firstOrderCard = page.locator('article.kiosk-panel').first()
    await expect(firstOrderCard).toBeVisible()

    const orderName = (await firstOrderCard.getByRole('heading').textContent())?.trim()
    const preferredItemRow = firstOrderCard.locator('.gcma-data-row', { hasText: 'ENV-BID-20L-BLC' }).first()
    const firstItemRow = await preferredItemRow.count() ? preferredItemRow : firstOrderCard.locator('.gcma-data-row').last()
    const firstReceptionButton = firstItemRow.getByRole('button', { name: /receptionner/i })
    const itemCodeText = (await firstItemRow.locator('.text-sm.text-zinc-500').first().textContent())?.trim()
    const pendingBefore = await firstItemRow.locator('text=/Reliquat/i').first().textContent()
    const pendingBeforeValue = extractPendingQty(pendingBefore)

    await firstReceptionButton.click()
    await page.locator('input[type="number"]').fill('1')
    const submitResponsePromise = page.waitForResponse((response) => {
      return response.request().method() === 'POST'
        && response.url().includes('gcma_kiosco.api.recepcion.registrar_recepcion')
    })
    await page.getByRole('button', { name: /valider la reception/i }).click()
    const submitResponse = await submitResponsePromise
    expect(submitResponse.ok()).toBeTruthy()

    const submitPayload = await submitResponse.json()
    expect(submitPayload?.message?.success).toBeTruthy()

    await expect(page.getByText(/Erreur interne pendant l'enregistrement de la reception\./i)).toHaveCount(0, { timeout: 20_000 })
    await expect(page.getByRole('heading', { name: /capturer la reception/i })).toBeHidden({ timeout: 20_000 })

    const reloadedOrder = page.locator('article.kiosk-panel', { has: page.getByRole('heading', { name: orderName ?? '' }) }).first()
    await expect(reloadedOrder).toBeVisible({ timeout: 20_000 })

    const reloadedItemRow = reloadedOrder.locator('.gcma-data-row', { hasText: itemCodeText ?? '' }).first()
    await expect(reloadedItemRow).toBeVisible()

    const pendingAfter = await reloadedItemRow.locator('text=/Reliquat/i').first().textContent()
    const pendingAfterValue = extractPendingQty(pendingAfter)

    expect(pendingAfterValue).toBeLessThan(pendingBeforeValue)
  })
})

function extractPendingQty(label) {
  const match = String(label ?? '').match(/Reliquat\s+([0-9]+(?:[.,][0-9]+)?)/i)
  if (!match) {
    throw new Error(`Unable to parse pending quantity from label: ${label}`)
  }

  return Number(match[1].replace(',', '.'))
}