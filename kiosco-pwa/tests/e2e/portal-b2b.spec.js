import { expect, test } from '@playwright/test'

const PRIMARY_NS = '/api/method/maroc_b2b.api.comercial'
const FALLBACK_NS = '/api/method/gcma_kiosco.api.comercial'

async function postWithNamespaceFallback(request, method, form) {
  const primary = await request.post(`${PRIMARY_NS}.${method}`, { form })
  if (primary.status() !== 417) return primary

  const payload = await primary.json().catch(() => ({}))
  const message = JSON.stringify(payload || {})
  if (!message.includes('App maroc_b2b is not installed')) return primary

  return request.post(`${FALLBACK_NS}.${method}`, { form })
}

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

    const fraudResponse = await postWithNamespaceFallback(page.request, 'create_support_ticket', {
      description: 'Tentative frauduleuse QA',
      affectedBatch: 'BATCH-FRAUD-001',
      id_cliente: otherCustomer,
    })
    expect(fraudResponse.status()).toBe(403)

    const okResponse = await postWithNamespaceFallback(page.request, 'create_support_ticket', {
      description: 'Probleme qualite confirme depuis le portail.',
      affectedBatch: 'BATCH-QA-REAL-001',
      id_cliente: ownCustomer,
    })

    if (okResponse.status() === 403) {
      const forbiddenPayload = await okResponse.json().catch(() => ({}))
      const forbiddenText = JSON.stringify(forbiddenPayload || {})
      test.skip(
        forbiddenText.includes('Usuario portal sin Customer vinculado'),
        'Runtime portal user is not linked to a Customer in this environment.',
      )
    }

    expect(okResponse.ok()).toBeTruthy()

    const payload = await okResponse.json()
    expect(payload?.message?.status).toBe('success')
    expect(payload?.message?.issue_id).toMatch(/^ISS-/)
  })
})
