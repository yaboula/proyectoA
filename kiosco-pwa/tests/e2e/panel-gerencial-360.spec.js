import { expect, test } from '@playwright/test'

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

    const panelApiResponse = await page.request.get('/api/method/maroc_b2b.api.gerencial.get_panel_gerencial_360')
    expect(panelApiResponse.ok()).toBeTruthy()

    const panelPayload = await panelApiResponse.json()
    expect(panelPayload?.message?.scorecard).toBeDefined()

    const alertApiResponse = await page.request.post('/api/method/maroc_b2b.api.gerencial.run_alerta_abandono_clientes')
    expect(alertApiResponse.ok()).toBeTruthy()

    const alertPayload = await alertApiResponse.json()
    expect(alertPayload?.message?.total_alertas).toBeGreaterThanOrEqual(0)

    await page.screenshot({ path: 'evidence/block3/panel-gerencial-360.png', fullPage: true })
  })
})
