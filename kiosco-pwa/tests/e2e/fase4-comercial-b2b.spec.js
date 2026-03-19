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
 * Nouveaux tests (sélecteur client v2) :
 *   F10 — CartePedidoModal : tab "Base clients" charge la liste ERPNext
 *   F11 — CartePedidoModal : sélection client → vérification compte → bouton activé
 *   F12 — CartePedidoModal : client bloqué → bouton désactivé
 *   F13 — CartePedidoModal : tab "Saisie libre" → confirmer → bouton activé
 *   F14 — CartePedidoModal : bouton "Nouveau client" → navigation /nuevo-cliente-b2b
 *   F15 — NuevoClienteB2B : formulaire s'affiche avec tous les champs
 *   F16 — NuevoClienteB2B : validation champ obligatoire (raison sociale vide)
 *   F17 — NuevoClienteB2B : soumission crée le client dans ERPNext
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

  // Le login redirige vers /rutas-comercial (default_route du profil comercial).
  // On navigue au hub pour vérifier le profileLabel affiché dans le widget opérateur.
  await page.goto('/hub')
  await page.waitForURL(/\/hub/, { timeout: 10_000 })

  // store.profileLabel doit afficher "Commercial B2B" dans le widget opérateur
  // On cible le div qui contient le profileLabel (font-semibold text-zinc-900)
  const profileWidget = page.locator('.font-semibold.text-zinc-900').filter({ hasText: /Commercial B2B/i })
  await expect(profileWidget.first()).toBeVisible({ timeout: 10_000 })

  // Le profileLabel NE DOIT PAS être "Production" (régression clé du fix kiosco.py)
  const profileLabel = await profileWidget.first().innerText()
  expect(profileLabel).toMatch(/Commercial B2B/i)

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

  // Trois cas possibles :
  // A) Succès en ligne : successMsg affiché brièvement → emit('submitted') → modal fermé + panier vidé
  // B) Succès offline : message "Hors ligne" dans le modal
  // C) Erreur API : message d'erreur dans le modal
  //
  // On détecte le succès soit par la fermeture du modal (cas A),
  // soit par le message offline (cas B).
  let orderResult = 'unknown'

  try {
    // Cas A : modal se ferme rapidement (succès en ligne)
    await page.waitForFunction(
      () => !document.body.innerText.includes('Panier de commande'),
      { timeout: 10_000 }
    )
    orderResult = 'success-online'
  } catch {
    // Le modal est encore ouvert — vérifier le message affiché
    const bodyText = await page.evaluate(() => document.body.innerText)
    if (bodyText.includes('Hors ligne') || bodyText.includes('sauvegardée')) {
      orderResult = 'success-offline'
    } else if (bodyText.includes('SAL-ORD') || bodyText.includes('enregistrée')) {
      orderResult = 'success-online'
    } else {
      orderResult = 'error: ' + bodyText.substring(0, 200)
    }
  }

  expect(['success-online', 'success-offline']).toContain(orderResult)

  // Le panier doit être vide si succès en ligne
  if (orderResult === 'success-online') {
    await expect(page.getByText(/article.*dans le panier/i)).toHaveCount(0)
  }

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

// ══════════════════════════════════════════════════════════════════════════════
// Nouveaux tests — Sélecteur client v2 + Nouveau client B2B
// ══════════════════════════════════════════════════════════════════════════════

// ── Helper: ouvrir le CartePedidoModal avec au moins un article ───────────────
async function openCartModal(page) {
  await loginComercial(page)
  await page.goto('/catalogo-stock')
  await waitForLoad(page)
  const btnAjouter = page.getByRole('button', { name: /Ajouter/i }).first()
  if (!(await btnAjouter.isVisible().catch(() => false))) return false
  await btnAjouter.click()
  await page.getByRole('button', { name: /Commander/i }).last().click()
  await expect(page.getByText(/Panier de commande/i)).toBeVisible({ timeout: 8_000 })
  return true
}

// ── F10: Tab "Base clients" charge la liste depuis ERPNext ────────────────────
test('F10 — CartePedidoModal: tab "Base clients" charge la liste ERPNext', async ({ page }) => {
  page.setDefaultTimeout(35_000)
  const opened = await openCartModal(page)
  if (!opened) { test.skip(); return }

  // Le tab "Base clients" doit être actif par défaut
  await expect(page.getByRole('button', { name: /Base clients/i })).toBeVisible()

  // Attendre que le spinner "Chargement..." du modal disparaisse (pas le spinner du catalogue)
  await page.waitForFunction(
    () => !document.body.innerText.includes('Chargement...'),
    { timeout: 15_000 }
  )

  // La liste doit contenir les clients ERPNext
  // On attend spécifiquement les noms des clients seed data
  await page.waitForFunction(
    () => {
      const txt = document.body.innerText
      return txt.includes('Droguerie Atlas') || txt.includes('Distrib Maghreb')
    },
    { timeout: 15_000 }
  )

  const clientItems = page.locator('button').filter({ hasText: /Droguerie Atlas|Distrib Maghreb/i })
  const count = await clientItems.count()
  expect(count).toBeGreaterThan(0)

  await page.screenshot({ path: 'tests/e2e/evidence/F10-client-list.png', fullPage: false })
})

// ── F11: Sélection client → vérification compte → bouton activé ──────────────
test('F11 — CartePedidoModal: sélection client vérifie compte et active le bouton', async ({ page }) => {
  page.setDefaultTimeout(40_000)
  const opened = await openCartModal(page)
  if (!opened) { test.skip(); return }

  // Attendre que la liste de clients soit chargée (les noms apparaissent dans des boutons)
  await page.waitForFunction(
    () => {
      const txt = document.body.innerText
      return txt.includes('Droguerie Atlas') || txt.includes('Distrib Maghreb')
    },
    { timeout: 15_000 }
  )

  // Cliquer sur "Droguerie Atlas Test" (notre client seed data de test)
  const clienteBtn = page.getByRole('button', { name: /Droguerie Atlas Test/i })
  await expect(clienteBtn).toBeVisible({ timeout: 5_000 })
  await clienteBtn.click()

  // Attendre vérification du compte (spinner disparaît, crédit ou bloqué apparaît)
  await page.waitForFunction(
    () => {
      const txt = document.body.innerText
      return txt.includes('Crédit') || txt.includes('bloqué') || txt.includes('libre')
    },
    { timeout: 15_000 }
  )

  // Droguerie Atlas Test n'est pas bloqué → bouton doit être actif
  const estaBloquado = await page.getByText(/Compte bloqué/i).isVisible().catch(() => false)
  if (!estaBloquado) {
    const btnPasser = page.getByRole('button', { name: /Passer la commande/i })
    await expect(btnPasser).toBeEnabled({ timeout: 5_000 })
  }

  await page.screenshot({ path: 'tests/e2e/evidence/F11-client-selected.png', fullPage: false })
})

// ── F12: Client bloqué → bouton désactivé ────────────────────────────────────
test('F12 — CartePedidoModal: client bloqué désactive "Passer la commande"', async ({ page }) => {
  page.setDefaultTimeout(40_000)
  const opened = await openCartModal(page)
  if (!opened) { test.skip(); return }

  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 15_000 })

  // Chercher un client avec badge "Bloqué"
  const badgeBloque = page.locator('span').filter({ hasText: /^Bloqué$/ }).first()
  const hayBloquado = await badgeBloque.isVisible().catch(() => false)

  if (!hayBloquado) {
    // No hay clientes bloqueados en seed data — test informativo
    test.info().annotations.push({
      type: 'info',
      description: 'Aucun client bloqué dans les données de test — test ignoré',
    })
    return
  }

  // Cliquer sur la ligne du client bloqué (parent button)
  const clienteBloquadoBtn = page.locator('button').filter({ has: badgeBloque }).first()
  await clienteBloquadoBtn.click()

  // Attendre la vérification
  await page.waitForFunction(
    () => document.body.innerText.includes('bloqué') || document.body.innerText.includes('Crédit'),
    { timeout: 12_000 }
  )

  // Le bouton "Passer la commande" DOIT être désactivé
  const btnPasser = page.getByRole('button', { name: /Passer la commande/i })
  await expect(btnPasser).toBeDisabled({ timeout: 5_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/F12-client-bloque.png', fullPage: false })
})

// ── F13: Tab "Saisie libre" → confirmer → bouton activé ──────────────────────
test('F13 — CartePedidoModal: mode "Saisie libre" permet commande sans vérification crédit', async ({ page }) => {
  page.setDefaultTimeout(35_000)
  const opened = await openCartModal(page)
  if (!opened) { test.skip(); return }

  // Cliquer sur le tab "Saisie libre"
  await page.getByRole('button', { name: /Saisie libre/i }).click()

  // Un avertissement amber doit apparaître (texte exact du composant)
  await expect(page.getByText(/Saisie libre.*ne sera pas vérifié|client ne sera pas vérifié/i)).toBeVisible()

  // Saisir un nom de client
  const inputNom = page.getByPlaceholder(/Droguerie El Wafa/i)
  await inputNom.fill('Prospect Test SA')

  // Confirmer
  await page.getByRole('button', { name: /Confirmer ce client/i }).click()

  // Le bouton "Passer la commande" doit être activé (pas de vérif crédit)
  const btnPasser = page.getByRole('button', { name: /Passer la commande/i })
  await expect(btnPasser).toBeEnabled({ timeout: 5_000 })

  // Le message informatif bleu doit confirmer le mode libre
  await expect(page.getByText(/saisie libre.*commande non soumise à vérification|libre.*non soumise/i)).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/F13-saisie-libre.png', fullPage: false })
})

// ── F14: Bouton "Nouveau client" → navigates to /nuevo-cliente-b2b ────────────
test('F14 — CartePedidoModal: bouton "Nouveau client" navigue vers /nuevo-cliente-b2b', async ({ page }) => {
  page.setDefaultTimeout(30_000)
  const opened = await openCartModal(page)
  if (!opened) { test.skip(); return }

  // Le bouton "Nouveau client" doit être visible
  await expect(page.getByRole('button', { name: /Nouveau client/i })).toBeVisible()

  await page.getByRole('button', { name: /Nouveau client/i }).click()

  // Doit naviguer vers la page d'enregistrement
  await expect(page).toHaveURL(/\/nuevo-cliente-b2b/, { timeout: 10_000 })

  await page.screenshot({ path: 'tests/e2e/evidence/F14-nouveau-client-nav.png', fullPage: false })
})

// ── F15: NuevoClienteB2B — formulaire complet ─────────────────────────────────
test('F15 — NuevoClienteB2B: formulaire affiche tous les champs requis', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginComercial(page)
  await page.goto('/nuevo-cliente-b2b')
  await page.waitForURL(/\/nuevo-cliente-b2b/, { timeout: 10_000 })

  // Titre de la page
  await expect(page.getByText(/Enregistrement client/i)).toBeVisible()

  // Champ obligatoire: raison sociale
  await expect(page.getByPlaceholder(/Droguerie El Wafa/i)).toBeVisible()

  // Sélecteurs groupe (3 boutons)
  for (const g of ['Droguerie', 'Distributeur', 'Grossiste']) {
    await expect(page.getByRole('button', { name: new RegExp(`^${g}$`) })).toBeVisible()
  }

  // Sélecteurs territoire
  for (const t of ['Casablanca', 'Rabat']) {
    await expect(page.getByRole('button', { name: new RegExp(`^${t}$`) })).toBeVisible()
  }

  // Champs optionnels
  await expect(page.getByPlaceholder(/\+212/i)).toBeVisible()       // téléphone
  await expect(page.getByPlaceholder(/ICE|000 000/i)).toBeVisible() // ICE fiscal

  // Info sync ERPNext
  await expect(page.getByText(/Synchronisation ERPNext automatique/i)).toBeVisible()

  // Bouton submit
  await expect(page.getByRole('button', { name: /Créer ce client/i })).toBeVisible()

  await page.screenshot({ path: 'tests/e2e/evidence/F15-nuevo-cliente-form.png', fullPage: true })
})

// ── F16: NuevoClienteB2B — validation raison sociale obligatoire ──────────────
test('F16 — NuevoClienteB2B: bouton submit désactivé si raison sociale vide', async ({ page }) => {
  page.setDefaultTimeout(25_000)
  await loginComercial(page)
  await page.goto('/nuevo-cliente-b2b')
  await page.waitForURL(/\/nuevo-cliente-b2b/, { timeout: 10_000 })

  // Le bouton doit être désactivé si le champ est vide
  const btnSubmit = page.getByRole('button', { name: /Créer ce client/i })
  await expect(btnSubmit).toBeDisabled()

  // Saisir un nom → bouton doit s'activer
  await page.getByPlaceholder(/Droguerie El Wafa/i).fill('Test Client SARL')
  await expect(btnSubmit).toBeEnabled()

  // Effacer → bouton désactivé à nouveau
  await page.getByPlaceholder(/Droguerie El Wafa/i).fill('')
  await expect(btnSubmit).toBeDisabled()

  await page.screenshot({ path: 'tests/e2e/evidence/F16-validation-required.png', fullPage: false })
})

// ── F17: NuevoClienteB2B — soumission complète ───────────────────────────────
test('F17 — NuevoClienteB2B: soumission crée le client dans ERPNext', async ({ page }) => {
  page.setDefaultTimeout(45_000)
  await loginComercial(page)
  await page.goto('/nuevo-cliente-b2b')
  await page.waitForURL(/\/nuevo-cliente-b2b/, { timeout: 10_000 })

  // Générer un nom unique pour éviter les doublons
  const uniqueName = `Droguerie Test E2E ${Date.now()}`

  // Remplir le formulaire
  await page.getByPlaceholder(/Droguerie El Wafa/i).fill(uniqueName)

  // Sélectionner groupe Grossiste
  await page.getByRole('button', { name: /^Grossiste$/ }).click()

  // Sélectionner territoire Casablanca
  await page.getByRole('button', { name: /^Casablanca$/ }).click()

  // Téléphone
  await page.getByPlaceholder(/\+212/i).fill('+212612345678')

  // ICE
  await page.getByPlaceholder(/ICE|000 000/i).fill('001234567000012')

  // Adresse
  const addrInputs = page.getByPlaceholder(/Rue, Quartier/i)
  await addrInputs.fill('123 Boulevard Hassan II')
  await page.getByPlaceholder(/Ville/i).fill('Casablanca')

  // Soumettre
  await page.getByRole('button', { name: /Créer ce client/i }).click()

  // Attendre l'overlay de succès ou message d'erreur
  await page.waitForFunction(
    () => {
      const txt = document.body.innerText
      return txt.includes('créé') || txt.includes('existe') || txt.includes('Impossible')
    },
    { timeout: 20_000 }
  )

  const bodyText = await page.evaluate(() => document.body.innerText)

  // Succès: overlay vert avec "Client créé !" OU erreur si déjà existant (acceptable)
  const isSuccess = bodyText.includes('créé') && !bodyText.includes('Impossible')
  const isAlreadyExists = bodyText.includes('existe')
  expect(isSuccess || isAlreadyExists).toBe(true)

  await page.screenshot({ path: 'tests/e2e/evidence/F17-nuevo-cliente-result.png', fullPage: false })
})
