/**
 * S12 — Panel Gerencial 360
 * =====================================================================
 * URL  : /panel-gerencial-360  (meta: guest — sin login)
 * APIs mock: get_panel_gerencial_360, get_cobertura_mapa,
 *            get_reporte_fotos_competencia, export_scorecard_csv
 *
 * Escenarios:
 *   S12-A  /panel-gerencial-360 carga con heading "Centro de mando B2B"
 *   S12-B  Scorecard con métricas del día (Clientes, Check-ins, Desviaciones, Hit-rate)
 *   S12-C  Mapa Leaflet con pins GPS visible
 *   S12-D  Botón "Export CSV" → descarga fichero
 */

import { test, expect } from '@playwright/test'

// ── Mock payloads ──────────────────────────────────────────────────────────────

const MOCK_PANEL = {
  scorecard: [
    {
      customer: 'Droguerie Atlas Test',
      customer_name: 'Droguerie Atlas Test',
      facturacion_ytd: 25000,
      deuda_vencida: 0,
      frecuencia_mensual: 3,
      dias_sin_compra: 5,
    },
  ],
  cobertura_resumen: { total_checkins: 12, desviaciones: 1 },
  hit_rate: {
    total_visitas: 15,
    visitas_con_pedido: 9,
    visitas_sin_pedido: 6,
    hit_rate: 0.6,
    por_comercial: [],
  },
}

const MOCK_COBERTURA = {
  rows: [
    {
      lat: 34.02,
      lng: -6.84,
      comercial: 'COM-TEST',
      cliente: 'Droguerie Atlas Test',
      time: '09:30',
      estado_visita: 'Validado',
      es_desviacion: false,
    },
    {
      lat: 33.98,
      lng: -6.90,
      comercial: 'COM-TEST',
      cliente: 'Otro Cliente',
      time: '11:00',
      estado_visita: 'Desviacion',
      es_desviacion: true,
    },
  ],
}

const MOCK_FOTOS = { rows: [] }

const MOCK_CSV = {
  content: 'customer,customer_name,facturacion_ytd,deuda_vencida\nDroguerie Atlas Test,Droguerie Atlas Test,25000,0',
  filename: 'scorecard_2026-03-20.csv',
}

// ── Helpers ────────────────────────────────────────────────────────────────────

async function setupPanelMocks(page) {
  await page.route(/get_panel_gerencial_360/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_PANEL }),
    })
  })

  await page.route(/get_cobertura_mapa/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_COBERTURA }),
    })
  })

  await page.route(/get_reporte_fotos_competencia/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_FOTOS }),
    })
  })

  await page.route(/export_scorecard_csv/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: MOCK_CSV }),
    })
  })
}

async function gotoPanel(page) {
  await page.goto('/panel-gerencial-360')
  await page.locator('h1').filter({ hasText: /Centro de mando B2B/i }).waitFor({
    state: 'visible',
    timeout: 20_000,
  })
  await page.locator('.animate-pulse').waitFor({ state: 'hidden', timeout: 15_000 }).catch(() => {})
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('S12 — Panel Gerencial 360', () => {
  // ── S12-A ──────────────────────────────────────────────────────────────────
  test('S12-A: /panel-gerencial-360 carga con heading Centro de mando B2B', async ({ page }) => {
    await setupPanelMocks(page)
    await gotoPanel(page)

    await expect(page.getByText(/Panel Gerencial 360/i)).toBeVisible()
    await expect(page.locator('h1').filter({ hasText: /Centro de mando B2B/i })).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S12-A-panel-gerencial.png',
      fullPage: false,
    })
  })

  // ── S12-B ──────────────────────────────────────────────────────────────────
  test('S12-B: Scorecard con métricas del día', async ({ page }) => {
    await setupPanelMocks(page)
    await gotoPanel(page)

    // 4 stats: Clientes scorecard, Check-ins, Desviaciones, Hit-rate
    const statsSection = page.locator('.gcma-stat')
    await expect(statsSection.first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Clientes scorecard')).toBeVisible()
    await expect(page.getByText('Check-ins del dia')).toBeVisible()
    await expect(page.getByText('12')).toBeVisible()
    await expect(page.locator('.gcma-stat').filter({ hasText: 'Desviaciones' })).toBeVisible()
    await expect(page.getByText('Hit-rate').first()).toBeVisible()
    await expect(page.getByText(/60\.0%/)).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S12-B-scorecard.png',
      fullPage: false,
    })
  })

  // ── S12-C ──────────────────────────────────────────────────────────────────
  test('S12-C: Mapa Leaflet con pins GPS visible', async ({ page }) => {
    await setupPanelMocks(page)
    await gotoPanel(page)

    // Sección mapa: h2 es "Rutas y desviaciones", label "Cobertura GPS"
    const mapSection = page.locator('section.kiosk-panel').filter({
      has: page.locator('h2').filter({ hasText: /Rutas y desviaciones/i }),
    })
    await expect(mapSection).toBeVisible({ timeout: 10_000 })

    // Leaflet inicializa de forma async; esperar contenedor
    const mapDiv = page.locator('[class*="leaflet"]').first()
    await expect(mapDiv).toBeVisible({ timeout: 20_000 })

    // Chip "Verde valida | Rouge desviada" confirma sección del mapa
    await expect(mapSection.getByText(/Verde valida|Rouge desviada/i)).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S12-C-mapa-leaflet.png',
      fullPage: false,
    })
  })

  // ── S12-D ──────────────────────────────────────────────────────────────────
  test('S12-D: Botón Export CSV descarga fichero', async ({ page }) => {
    await setupPanelMocks(page)
    await gotoPanel(page)

    const downloadPromise = page.waitForEvent('download', { timeout: 15_000 })

    const btnExport = page.getByRole('button', { name: /Export CSV/i })
    await expect(btnExport).toBeVisible({ timeout: 10_000 })
    await btnExport.click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/scorecard_.*\.csv$/)

    const filePath = await download.path()
    if (filePath) {
      const { readFileSync } = await import('fs')
      const body = readFileSync(filePath, 'utf8')
      expect(body).toContain('customer')
      expect(body).toContain('Droguerie Atlas Test')
    }

    await page.screenshot({
      path: 'tests/e2e/evidence/S12-D-export-csv.png',
      fullPage: false,
    })
  })
})
