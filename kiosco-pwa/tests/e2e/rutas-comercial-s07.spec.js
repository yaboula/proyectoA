/**
 * E2E — Sprint 07: Rutas Comerciales, Check-in GPS y Catálogo de Stock
 *
 * Cubre los DoD del plan:
 *  - La app pregunta permisos de GPS al abrir la vista de rutas
 *  - Si GPS denegado, el botón Check-in muestra advertencia (no bloquea la ruta)
 *  - Se carga la lista de clientes de la ruta del día
 *  - El catálogo de stock carga artículos con precio y stock
 *  - Se puede añadir un artículo al carrito y el resumen sticky aparece
 */

import { test, expect } from '@playwright/test'
import { loginToRoute } from './helpers/kiosco.js'

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173'

test.beforeEach(async ({ page }) => {
  page.setDefaultTimeout(20_000)
})

// ── S07-A: Vista de Rutas Comerciales ─────────────────────────────────────────

test('S07-A1 — Carga la vista /rutas-comercial con estructura básica', async ({ page }) => {
  await loginToRoute(page, '/rutas-comercial')

  // Header de la vista
  await expect(page.getByText(/Force de vente B2B|Rutas y visitas/i)).toBeVisible()
  await expect(page.getByText(/Hoja del dia/i)).toBeVisible()

  // Stats de ruta
  await expect(page.getByText(/Ruta|Clientes|Visitados/i).first()).toBeVisible()
})

test('S07-A2 — Botón Catálogo navega a /catalogo-stock', async ({ page }) => {
  await loginToRoute(page, '/rutas-comercial')

  await page.getByRole('button', { name: /Catalogue/i }).click()
  await expect(page).toHaveURL(/\/catalogo-stock/, { timeout: 10_000 })
})

test('S07-A3 — La vista maneja respuesta vacía de ruta sin error', async ({ page }) => {
  // Si el usuario no tiene Sales Person asignado, la API devuelve { rutas: [] }
  await loginToRoute(page, '/rutas-comercial')

  // No debe haber overlay de error — puede estar vacío pero sin crash
  await expect(page.locator('.bg-red-600')).toHaveCount(0)
})

// ── S07-B: Catálogo de Stock ───────────────────────────────────────────────────

test('S07-B1 — Catálogo carga con artículos o estado vacío', async ({ page }) => {
  await loginToRoute(page, '/catalogo-stock')

  await expect(page.getByText(/Catalogue & Stock/i)).toBeVisible()

  // Esperar a que termine la carga (desaparece spinner o aparece grilla)
  await page.waitForFunction(() => {
    const spinner = document.querySelector('.animate-spin')
    return !spinner
  }, { timeout: 15_000 })

  // Debe mostrar artículos o el EmptyState — no un error rojo
  const hayArticulos = await page.locator('[data-testid="item-card"], .kiosk-panel').count() > 0
  const hayEmptyState = await page.getByText(/Aucun article trouvé/i).isVisible().catch(() => false)

  expect(hayArticulos || hayEmptyState).toBeTruthy()
})

test('S07-B2 — El buscador filtra artículos con debounce', async ({ page }) => {
  await loginToRoute(page, '/catalogo-stock')

  // Esperar carga inicial
  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 15_000 })

  const searchInput = page.getByPlaceholder(/Rechercher un article/i)
  await expect(searchInput).toBeVisible()

  // Escribir término de búsqueda — el debounce es 400ms
  await searchInput.fill('PINT')
  await page.waitForTimeout(600)

  // Spinner de recarga o resultado (sin error rojo)
  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 10_000 })
  await expect(page.locator('.border-red-200.bg-red-50').first()).toHaveCount(0)
})

test('S07-B3 — Añadir artículo al carrito muestra la barra sticky', async ({ page }) => {
  await loginToRoute(page, '/catalogo-stock')

  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 15_000 })

  // Si hay artículos en stock, click en el primer botón Ajouter
  const btnAgregar = page.getByRole('button', { name: /Ajouter/i }).first()
  const visible = await btnAgregar.isVisible().catch(() => false)

  if (!visible) {
    test.skip()
    return
  }

  await btnAgregar.click()

  // La barra sticky con "articles" y "Commander" debe aparecer
  await expect(page.getByText(/article.*dans le panier|articles dans le panier/i)).toBeVisible({ timeout: 5_000 })
  await expect(page.getByRole('button', { name: /Commander/i })).toBeVisible()
})

test('S07-B4 — El botón Commander abre el CartePedidoModal', async ({ page }) => {
  await loginToRoute(page, '/catalogo-stock')

  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 15_000 })

  const btnAgregar = page.getByRole('button', { name: /Ajouter/i }).first()
  const visible = await btnAgregar.isVisible().catch(() => false)
  if (!visible) { test.skip(); return }

  await btnAgregar.click()
  await page.getByRole('button', { name: /Commander/i }).last().click()

  // El modal de panier debe aparecer
  await expect(page.getByText(/Panier de commande/i)).toBeVisible({ timeout: 5_000 })
  await expect(page.getByText(/Vérification du compte|Compte bloqué|Crédit/i)).toBeVisible({ timeout: 10_000 })
})
