import { expect, test } from '@playwright/test'

const PRIMARY_NS = '/api/method/maroc_b2b.api.gerencial'
const FALLBACK_NS = '/api/method/gcma_kiosco.api.gerencial'

async function requestWithNamespaceFallback(request, method, options = {}) {
  const primary = await request.fetch(`${PRIMARY_NS}.${method}`, options)
  if (primary.status() !== 417) return primary

  const payload = await primary.json().catch(() => ({}))
  const message = JSON.stringify(payload || {})
  if (!message.includes('App maroc_b2b is not installed')) return primary

  return request.fetch(`${FALLBACK_NS}.${method}`, options)
}

test.describe('Panel gerencial 360', () => {
  test('@block3 loads dashboard and runs churn alert job', async ({ page }) => {
    const user = process.env.PLAYWRIGHT_MANAGER_USER
    const password = process.env.PLAYWRIGHT_MANAGER_PASSWORD

    test.skip(!user || !password, 'Set PLAYWRIGHT_MANAGER_USER and PLAYWRIGHT_MANAGER_PASSWORD.')

    const loginResponse = await page.request.post('/api/method/login', {
      form: {
        usr: user,
        pwd: password,
      },
    })
    expect(loginResponse.ok()).toBeTruthy()

    await page.goto('/panel-gerencial-360')
    await expect(page.getByRole('heading', { name: /centro de mando b2b/i })).toBeVisible({ timeout: 20_000 })

    const panelApiResponse = await requestWithNamespaceFallback(page.request, 'get_panel_gerencial_360', {
      method: 'GET',
    })

    if (panelApiResponse.status() === 403) {
      const forbiddenPayload = await panelApiResponse.json().catch(() => ({}))
      const forbiddenText = JSON.stringify(forbiddenPayload || {})
      test.skip(
        forbiddenText.includes('No permission for DocType'),
        'Runtime manager user lacks role permissions in this environment.',
      )
    }

    expect(panelApiResponse.ok()).toBeTruthy()

    const panelPayload = await panelApiResponse.json()
    expect(panelPayload?.message?.scorecard).toBeDefined()

    const alertApiResponse = await requestWithNamespaceFallback(page.request, 'run_alerta_abandono_clientes', {
      method: 'POST',
    })
    expect(alertApiResponse.ok()).toBeTruthy()

    const alertPayload = await alertApiResponse.json()
    expect(alertPayload?.message?.total_alertas).toBeGreaterThanOrEqual(0)

    await page.screenshot({ path: 'evidence/block3/panel-gerencial-360.png', fullPage: true })
  })
})
