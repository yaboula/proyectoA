import { expect, test } from '@playwright/test'

test.describe('Portal B2B client', () => {
  test('@block3 enforces tenant isolation and allows SOS support for owner customer', async ({ page }) => {
    const user = process.env.PLAYWRIGHT_PORTAL_USER
    const password = process.env.PLAYWRIGHT_PORTAL_PASSWORD
    const ownCustomer = process.env.PLAYWRIGHT_PORTAL_CUSTOMER
    const otherCustomer = process.env.PLAYWRIGHT_PORTAL_OTHER_CUSTOMER

    test.skip(
      !user || !password || !ownCustomer || !otherCustomer,
      'Set PLAYWRIGHT_PORTAL_USER, PLAYWRIGHT_PORTAL_PASSWORD, PLAYWRIGHT_PORTAL_CUSTOMER and PLAYWRIGHT_PORTAL_OTHER_CUSTOMER.',
    )

    const loginResponse = await page.request.post('/api/method/login', {
      form: {
        usr: user,
        pwd: password,
      },
    })
    expect(loginResponse.ok()).toBeTruthy()

    await page.goto('/portal-b2b')
    await expect(page.getByRole('heading', { name: /mon espace droguerie/i })).toBeVisible({ timeout: 15_000 })

    const fraudResponse = await page.request.post('/api/method/maroc_b2b.api.comercial.create_support_ticket', {
      form: {
        description: 'Tentative frauduleuse QA',
        affectedBatch: 'BATCH-FRAUD-001',
        id_cliente: otherCustomer,
      },
    })
    expect(fraudResponse.status()).toBe(403)

    const okResponse = await page.request.post('/api/method/maroc_b2b.api.comercial.create_support_ticket', {
      form: {
        description: 'Probleme qualite confirme depuis le portail.',
        affectedBatch: 'BATCH-QA-REAL-001',
        id_cliente: ownCustomer,
      },
    })

    expect(okResponse.ok()).toBeTruthy()

    const payload = await okResponse.json()
    expect(payload?.message?.status).toBe('success')
    expect(payload?.message?.issue_id).toMatch(/^ISS-/)
  })
})
