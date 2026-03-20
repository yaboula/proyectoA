/**
 * S11 — Portal B2B + Loyalty
 * =====================================================================
 * URL      : /portal-b2b  (meta: guest — sin login)
 * APIs mock: get_portal_dashboard, get_portal_estado_cuenta,
 *            get_loyalty_points, redimir_puntos
 *
 * Escenarios:
 *   S11-A  Página /portal-b2b carga con heading "Mon espace droguerie"
 *   S11-B  Widget loyalty muestra 250 puntos
 *   S11-C  Introducir 50 pts → Échanger → "50 points échangés" visible
 *   S11-D  Sección "Factures et paiements" visible con facturas/pagos
 */

import { test, expect } from '@playwright/test'

// ── Mock payloads ──────────────────────────────────────────────────────────────

const MOCK_DASHBOARD = {
  id_cliente: 'Droguerie Atlas Test',
  bloqueado_30_dias: false,
  mensaje_bloqueo_30_dias: null,
  estado_cuenta: { deuda_total: 12500, deuda_vencida: 0 },
  sugerencias: [
    { item_code: 'PT-TEST-B3-ITEM-A', item_name: 'Peinture Test A', score: 9 },
  ],
}

const MOCK_ESTADO_CUENTA = {
  facturas: [
    {
      name: 'ACC-SINV-2026-00001',
      posting_date: '2026-01-15',
      due_date: '2026-02-15',
      grand_total: 5000,
      outstanding_amount: 2500,
    },
  ],
  pagos: [
    {
      name: 'ACC-PAY-2026-00001',
      posting_date: '2026-01-20',
      paid_amount: 2500,
      currency: 'MAD',
    },
  ],
}

const MOCK_LOYALTY_250 = {
  saldo: { saldo_puntos: 250, puntos_acumulados: 300, puntos_canjeados: 50 },
  equivalencia_mad: 250,
  detalle_por_familia: [
    { familia: 'Peintures décoratives', puntos_estimados: 250, facturacion_ytd: 25000 },
  ],
}

const MOCK_LOYALTY_200 = {
  saldo: { saldo_puntos: 200, puntos_acumulados: 300, puntos_canjeados: 100 },
  equivalencia_mad: 200,
  detalle_por_familia: [],
}

const MOCK_REDIMIR = {
  puntos_canjeados: 50,
  descuento_aplicado_mad: 500,
  nuevo_saldo: 200,
}

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * Registra mocks para todas las APIs del portal.
 * loyaltyCallTracker permite devolver datos distintos en llamadas sucesivas.
 */
async function setupPortalMocks(page, { loyaltyCallTracker } = {}) {
  const tracker = loyaltyCallTracker ?? { count: 0 }

  await page.route(/get_portal_dashboard/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_DASHBOARD }),
    })
  })

  await page.route(/get_portal_estado_cuenta/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_ESTADO_CUENTA }),
    })
  })

  await page.route(/get_loyalty_points/, async route => {
    tracker.count++
    const payload = tracker.count === 1 ? MOCK_LOYALTY_250 : MOCK_LOYALTY_200
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: payload }),
    })
  })
}

/** Navega a /portal-b2b y espera que el contenido principal cargue */
async function gotoPortal(page) {
  await page.goto('/portal-b2b')
  // El h1 siempre está presente (fuera de v-if)
  await page.locator('h1').filter({ hasText: /Mon espace droguerie/i }).waitFor({
    state: 'visible',
    timeout: 20_000,
  })
  // Esperar que desaparezca el spinner (loading → false)
  await page.locator('.animate-pulse').waitFor({ state: 'hidden', timeout: 15_000 }).catch(() => {})
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('S11 — Portal B2B + Loyalty', () => {
  // ── S11-A ──────────────────────────────────────────────────────────────────
  test('S11-A: /portal-b2b carga con heading Mon espace droguerie', async ({ page }) => {
    await setupPortalMocks(page)
    await gotoPortal(page)

    // Título y chip "Portail B2B Client"
    await expect(page.getByText(/Portail B2B Client/i)).toBeVisible()
    await expect(page.locator('h1').filter({ hasText: /Mon espace droguerie/i })).toBeVisible()

    // Client stat
    await expect(page.getByText(/Droguerie Atlas Test/i).first()).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S11-A-portal-b2b.png',
      fullPage: false,
    })
  })

  // ── S11-B ──────────────────────────────────────────────────────────────────
  test('S11-B: Widget loyalty muestra 250 puntos', async ({ page }) => {
    await setupPortalMocks(page)
    await gotoPortal(page)

    // Sección loyalty — section.kiosk-panel que contiene el h2 de fidelidad
    const loyaltySection = page.locator('section.kiosk-panel').filter({
      has: page.locator('h2').filter({ hasText: 'Programme de fid' }),
    })
    await expect(loyaltySection).toBeVisible({ timeout: 10_000 })

    // El contador grande (amber-600) muestra 250
    const puntosDisplay = loyaltySection.locator('.text-amber-600').first()
    await expect(puntosDisplay).toHaveText('250', { timeout: 5_000 })

    // Estadísticas: 300 acumulados, 50 canjeados
    await expect(loyaltySection.getByText('300')).toBeVisible()
    // '50' aparece dos veces (canjeados previos + en la barra de puntos) → primera coincidencia
    await expect(loyaltySection.getByText('50').first()).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S11-B-loyalty-250.png',
      fullPage: false,
    })
  })

  // ── S11-C ──────────────────────────────────────────────────────────────────
  test('S11-C: Introducir 50 pts → Echanger → feedback de canje visible', async ({ page }) => {
    const loyaltyCallTracker = { count: 0 }
    await setupPortalMocks(page, { loyaltyCallTracker })

    // Mock redimir_puntos
    await page.route(/redimir_puntos/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: MOCK_REDIMIR }),
      })
    })

    await gotoPortal(page)

    // Esperar sección loyalty (section.kiosk-panel con h2 de fidelidad)
    const loyaltySection = page.locator('section.kiosk-panel').filter({
      has: page.locator('h2').filter({ hasText: 'Programme de fid' }),
    })
    await expect(loyaltySection).toBeVisible({ timeout: 10_000 })

    // Input de puntos a redimir (valor inicial = 100) → cambiar a 50
    const puntosInput = loyaltySection.locator('input[type="number"][min="10"]')
    await expect(puntosInput).toBeVisible()
    await puntosInput.fill('50')

    // Click botón Echanger — "changer" sin acento inicial para el regex
    const btnEchanger = loyaltySection.getByRole('button', { name: /changer/i })
    await expect(btnEchanger).toBeEnabled({ timeout: 3_000 })
    await btnEchanger.click()

    // Mensaje de éxito debe aparecer
    const successPanel = page.locator('.border-green-200.bg-green-50')
    await expect(successPanel).toBeVisible({ timeout: 10_000 })
    // El mensaje es "50 points échangés — remise de 500 MAD..."
    await expect(successPanel).toContainText('50 points', { timeout: 5_000 })
    await expect(successPanel).toContainText('500 MAD', { timeout: 3_000 })

    // Tras recarga: saldo baja a 200 (segunda llamada a getLoyaltyPoints)
    await expect(loyaltySection.locator('.text-amber-600').first()).toHaveText('200', { timeout: 10_000 })

    await page.screenshot({
      path: 'tests/e2e/evidence/S11-C-loyalty-echanger.png',
      fullPage: false,
    })
  })

  // ── S11-D ──────────────────────────────────────────────────────────────────
  test('S11-D: Sección "Factures et paiements" visible con datos', async ({ page }) => {
    await setupPortalMocks(page)
    await gotoPortal(page)

    // Heading de la sección
    await expect(page.getByText(/Factures et paiements/i)).toBeVisible({ timeout: 10_000 })

    // Subsecciones
    const facturesPanel = page.locator('article').filter({ hasText: /Factures/i }).first()
    const paiementsPanel = page.locator('article').filter({ hasText: /Paiements/i }).first()

    await expect(facturesPanel).toBeVisible()
    await expect(paiementsPanel).toBeVisible()

    // Al menos una factura del mock
    await expect(facturesPanel.getByText('ACC-SINV-2026-00001')).toBeVisible()

    // Al menos un pago del mock
    await expect(paiementsPanel.getByText('ACC-PAY-2026-00001')).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S11-D-factures-paiements.png',
      fullPage: false,
    })
  })
})
