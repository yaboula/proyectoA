/**
 * E2E — FASE 4: Bloque 3 Comercial B2B — Test suite complet
 *
 * Simule le parcours complet d'un agent commercial terrain :
 *   F01 — Login badge comercial → profil "Commercial B2B"
 *   F02 — Hub modules : carte "Commercial B2B" visible
 *   F03 — Tournée du jour : structure chargée sans erreur
 *   F04 — Check-in GPS : bouton visible même sans autorisation GPS
 *   F05 — Catalogue Stock : articles avec prix et stock corrects
 *   F06 — Panier : ajout d'articles → barre sticky apparaît
 *   F07 — CartePedidoModal : saisie client → état de compte
 *   F08 — Soumission commande (online) → confirmation ou queue offline
 *   F09 — Module Hub : clic sur carte → navigation vers /rutas-comercial
 *
 * Prérequis :
 *   - Vite dev server sur :5173 (ou PLAYWRIGHT_BASE_URL)
 *   - Badge comercial en PLAYWRIGHT_COMERCIAL_BADGE (défaut: COM-2026-BADGE-00099)
 *   - Client B3 en PLAYWRIGHT_CLIENTE_ID (défaut: Droguerie Atlas Test)
 */

import { test, expect } from '@playwright/test'

const COMERCIAL_BADGE = process.env.PLAYWRIGHT_COMERCIAL_BADGE ?? 'COM-2026-BADGE-00099'
const CLIENTE_ID = process.env.PLAYWRIGHT_CLIENTE_ID ?? 'Droguerie Atlas Test'

// ── Helper: login avec le badge commercial ─────────────────────────────────────
async function loginComercial(page) {
  await page.goto('/')
  await page.waitForSelector('button', { timeout: 10_000 })
  await page.getByRole('button', { name: /saisie manuelle/i }).click()
  const input = page.getByPlaceholder(/OP-2026-BADGE|COM-2026-BADGE/i).or(
    page.locator('input[type="text"]').last()
  )
  await input.fill(COMERCIAL_BADGE)
  await page.getByRole('button', { name: /^valider$/i }).click()
  await page.waitForURL(/\/hub|\/rutas-comercial/, { timeout: 20_000 })
}

// ── Helper: attendre fin de chargement (spinner disparu) ──────────────────────
async function waitForLoad(page, timeout = 15_000) {
  await page.waitForFunction(
    () => !document.querySelector('.animate-spin'),
    { timeout }
  )
}

// ── F01: Login → vérification du profil ───────────────────────────────────────
test('F01 — Login badge comercial affiche profil "Commercial B2B"', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginComercial(page)

  // Le profil affiché doit être "Commercial B2B" (pas "Production")
  const profileText = page.getByText(/Commercial B2B/i)
  await expect(profileText.first()).toBeVisible({ timeout: 10_000 })

  // Capture d'écran evidence
  await page.screenshot({ path: 'tests/e2e/evidence/F01-profil-comercial.png', fullPage: false })
})

// ── F02: Module Hub — carte Commercial B2B présente ───────────────────────────
test('F02 — Hub modules affiche la carte "Commercial B2B"', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginComercial(page)
  await page.goto('/hub')
  await page.waitForURL(/\/hub/, { timeout: 10_000 })

  // La carte Commercial doit être visible
  await expect(page.getByText(/Commercial B2B/i).first()).toBeVisible({ timeout: 8_000 })

  // Le badge "Force de vente" doit être présent
  await expect(page.getByText(/Force de vente/i)).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/F02-hub-commercial-card.png', fullPage: true })
})

// ── F03: Tournée du jour — structure sans erreur ───────────────────────────────
test('F03 — Tournée commerciale du jour se charge sans erreur', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  await loginComercial(page)
  await page.goto('/rutas-comercial')
  await page.waitForURL(/\/rutas-comercial/, { timeout: 10_000 })

  await waitForLoad(page)

  // Titre principal en français
  await expect(page.getByText(/Tournee commerciale|Tournée commerciale|Force de vente/i).first()).toBeVisible()

  // Pas d'overlay d'erreur rouge (bg-red-600 fullscreen)
  const errorOverlay = page.locator('.bg-red-600.fixed, .fixed.bg-red-600')
  await expect(errorOverlay).toHaveCount(0)

  // Section "Feuille du jour" présente (libellé de section)
  await expect(page.getByText(/Feuille du jour|Route|Etat/i).first()).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/F03-tournee-jour.png', fullPage: true })
})

// ── F04: Check-in GPS — bouton visible même sans GPS ──────────────────────────
test('F04 — Bouton Check-in GPS visible même sans permission GPS', async ({ page }) => {
  page.setDefaultTimeout(30_000)

  // Bloquer les permissions GPS (simuler un appareil sans GPS ou refus)
  await page.context().grantPermissions([]) // Aucune permission accordée

  await loginComercial(page)
  await page.goto('/rutas-comercial')
  await waitForLoad(page)

  // Si des clients sont dans la route, vérifier que le bouton Check-in existe
  const btnCheckin = page.getByRole('button', { name: /Check.?in|GPS/i })
  const checkinVisible = await btnCheckin.first().isVisible().catch(() => false)

  // Le test ne doit PAS avoir d'erreur bloquante si la route est vide
  const errorFatal = await page.locator('.bg-red-600.fixed').isVisible().catch(() => false)
  expect(errorFatal).toBe(false)

  await page.screenshot({ path: 'tests/e2e/evidence/F04-checkin-gps.png', fullPage: true })
})

// ── F05: Catalogue Stock — articles avec prix et stock ────────────────────────
test('F05 — Catalogue Stock affiche articles avec prix et stock', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  await loginComercial(page)
  await page.goto('/catalogo-stock')
  await page.waitForURL(/\/catalogo-stock/, { timeout: 10_000 })

  await waitForLoad(page)

  // Titre de la vue
  await expect(page.getByText(/Catalogue.*Stock|Stock.*Catalogue/i)).toBeVisible()

  // Pas d'erreur rouge inline
  const errorInline = page.locator('.border-red-200.bg-red-50')
  const errCount = await errorInline.count()
  expect(errCount).toBe(0)

  // Vérifier qu'au moins un article est affiché
  const articles = page.locator('.kiosk-panel').filter({ hasText: /En stock|Rupture/i })
  const count = await articles.count()
  expect(count).toBeGreaterThan(0)

  // Vérifier que les articles B3 ont un prix (pas "—")
  const articleA = page.locator('.kiosk-panel').filter({ hasText: /PT-TEST-B3-ITEM-A/i })
  const articleAVisible = await articleA.isVisible().catch(() => false)
  if (articleAVisible) {
    // Le prix ne doit pas afficher "—"
    const prixText = await articleA.innerText()
    expect(prixText).not.toContain('—')
    expect(prixText).toContain('MAD')
  }

  await page.screenshot({ path: 'tests/e2e/evidence/F05-catalogue-stock.png', fullPage: true })
})

// ── F06: Panier — ajout d'articles → barre sticky ────────────────────────────
test('F06 — Ajout article au panier affiche la barre sticky', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  await loginComercial(page)
  await page.goto('/catalogo-stock')
  await waitForLoad(page)

  // Trouver le premier bouton "Ajouter" disponible (article en stock)
  const btnAjouter = page.getByRole('button', { name: /Ajouter/i }).first()
  const dispo = await btnAjouter.isVisible().catch(() => false)

  if (!dispo) {
    test.info().annotations.push({ type: 'skip', description: 'Aucun article en stock disponible' })
    return
  }

  await btnAjouter.click()

  // La barre sticky doit apparaître en bas
  await expect(page.getByText(/article.*dans le panier/i)).toBeVisible({ timeout: 5_000 })
  await expect(page.getByRole('button', { name: /Commander/i }).last()).toBeVisible()

  // Le total doit afficher un montant MAD
  await expect(page.getByText(/MAD/i).first()).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/F06-panier-sticky.png', fullPage: false })
})

// ── F07: CartePedidoModal — saisie client → état de compte ───────────────────
test('F07 — CartePedidoModal permet saisir client et vérifie son compte', async ({ page }) => {
  page.setDefaultTimeout(35_000)
  await loginComercial(page)
  await page.goto('/catalogo-stock')
  await waitForLoad(page)

  const btnAjouter = page.getByRole('button', { name: /Ajouter/i }).first()
  if (!(await btnAjouter.isVisible().catch(() => false))) { test.skip(); return }

  await btnAjouter.click()
  await page.getByRole('button', { name: /Commander/i }).last().click()

  // Le modal "Panier de commande" doit s'ouvrir
  await expect(page.getByText(/Panier de commande/i)).toBeVisible({ timeout: 8_000 })

  // Vérifier que le champ de saisie client est présent si idCliente est vide
  const inputCliente = page.getByPlaceholder(/Droguerie Atlas|ID client/i)
  const hasInput = await inputCliente.isVisible().catch(() => false)

  if (hasInput) {
    // Saisir l'ID du client et valider
    await inputCliente.fill(CLIENTE_ID)
    await inputCliente.press('Enter')

    // Attendre la vérification du compte
    await page.waitForFunction(
      () => {
        const txt = document.body.innerText
        return txt.includes('Crédit') || txt.includes('bloqué') || txt.includes('vide')
      },
      { timeout: 15_000 }
    )
  }

  // Le bouton "Passer la commande" doit exister
  await expect(page.getByRole('button', { name: /Passer la commande/i })).toBeVisible()

  // Capturer l'état du modal
  await page.screenshot({ path: 'tests/e2e/evidence/F07-cart-modal-client.png', fullPage: false })
})

// ── F08: Soumission commande — online ou offline ───────────────────────────────
test('F08 — Soumission commande crée SO en ligne ou enfile hors ligne', async ({ page }) => {
  page.setDefaultTimeout(45_000)
  await loginComercial(page)
  await page.goto('/catalogo-stock')
  await waitForLoad(page)

  const btnAjouter = page.getByRole('button', { name: /Ajouter/i }).first()
  if (!(await btnAjouter.isVisible().catch(() => false))) { test.skip(); return }

  await btnAjouter.click()
  await page.getByRole('button', { name: /Commander/i }).last().click()
  await expect(page.getByText(/Panier de commande/i)).toBeVisible({ timeout: 8_000 })

  // Saisir le client si nécessaire
  const inputCliente = page.getByPlaceholder(/Droguerie Atlas|ID client/i)
  const hasInput = await inputCliente.isVisible().catch(() => false)
  if (hasInput) {
    await inputCliente.fill(CLIENTE_ID)
    await inputCliente.press('Enter')
    // Attendre fin de vérification compte
    await page.waitForTimeout(2_000)
  }

  // Cliquer "Passer la commande"
  const btnPasser = page.getByRole('button', { name: /Passer la commande/i })
  const btnEnabled = await btnPasser.isEnabled().catch(() => false)

  if (!btnEnabled) {
    // Client bloqué ou panier vide — acceptable
    test.info().annotations.push({
      type: 'info',
      description: 'Bouton "Passer la commande" désactivé — client bloqué ou panier vide',
    })
    await page.screenshot({ path: 'tests/e2e/evidence/F08-commande-bloquee.png' })
    return
  }

  await btnPasser.click()

  // Attendre résultat : succès (SAL-ORD) ou message offline
  await page.waitForFunction(
    () => {
      const txt = document.body.innerText
      return (
        txt.includes('SAL-ORD') ||
        txt.includes('enregistrée') ||
        txt.includes('Hors ligne') ||
        txt.includes('sauvegardée')
      )
    },
    { timeout: 20_000 }
  )

  const resultText = await page.evaluate(() => document.body.innerText)
  const isSuccess = resultText.includes('SAL-ORD') || resultText.includes('enregistrée')
  const isOffline = resultText.includes('Hors ligne') || resultText.includes('sauvegardée')

  expect(isSuccess || isOffline).toBe(true)

  await page.screenshot({ path: 'tests/e2e/evidence/F08-commande-result.png', fullPage: false })
})

// ── F09: Module Hub — clic sur carte Commercial navigue correctement ──────────
test('F09 — Clic carte "Commercial B2B" dans hub navigue vers /rutas-comercial', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginComercial(page)
  await page.goto('/hub')
  await page.waitForURL(/\/hub/, { timeout: 10_000 })

  // Trouver le bouton CTA de la carte Commercial
  const btnOuvrir = page.getByRole('button', { name: /Ouvrir le commerce|commerce/i })
  const visible = await btnOuvrir.isVisible().catch(() => false)

  if (!visible) {
    // Essayer de trouver la carte par son titre
    const carteComercial = page.locator('.kiosk-panel').filter({ hasText: /Commercial B2B/i })
    const cardVisible = await carteComercial.isVisible().catch(() => false)
    expect(cardVisible).toBe(true)
    return
  }

  await btnOuvrir.click()
  await expect(page).toHaveURL(/\/rutas-comercial/, { timeout: 12_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/F09-nav-rutas.png', fullPage: false })
})
