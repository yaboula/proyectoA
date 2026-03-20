/**
 * S10 — Chofer POD (Proof of Delivery)
 * =====================================================================
 * Badge chofer : CHOFER-2026-BADGE-00088 (perfil logística)
 * DN de prueba : MAT-DN-2026-00003 (Droguerie Atlas Test)
 *
 * Escenarios:
 *   S10-A  Login badge chofer → navega a /chofer-pod
 *   S10-B  Delivery Note de "Droguerie Atlas Test" aparece en la lista
 *   S10-C  Firma canvas + foto habilitan botón "Valider POD"
 *   S10-D  Valider POD → mock API → mensaje de éxito "POD enregistre"
 */

import { test, expect } from '@playwright/test'

// Cada test requiere login (~25s) + navegación a /chofer-pod + assertions → >60s
test.describe.configure({ timeout: 120_000 })

const CHOFER_BADGE = process.env.PLAYWRIGHT_CHOFER_BADGE ?? 'CHOFER-2026-BADGE-00088'
const DN_ID        = 'MAT-DN-2026-00003'
const DN_CUSTOMER  = 'Droguerie Atlas Test'

// Minimal 1×1 JPEG en base64 (válido, no vacío)
const FAKE_JPG_B64 =
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDA' +
  'oMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wgARCAABAAEDASIAAhEB' +
  'AxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEA' +
  'AhADEAAAAFAP/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAA' +
  'AAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF/' +
  '/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAA' +
  'AAP/aAAgBAQABPyF//9oADAMBAAIAAwAAACBP/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAA' +
  'gBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAA' +
  'AAAAAAAAAAAAAP/aAAgBAQABPyF//9k='

// ── Helpers ────────────────────────────────────────────────────────────────────

async function loginChofer(page) {
  await page.goto('/')
  await page.waitForSelector('button', { timeout: 10_000 })
  await page.getByRole('button', { name: /saisie manuelle/i }).click()
  const input = page
    .getByPlaceholder(/OP-2026-BADGE|COM-2026-BADGE|CHOFER/i)
    .or(page.locator('input[type="text"]').last())
  await input.fill(CHOFER_BADGE)
  await page.getByRole('button', { name: /^valider$/i }).click()
  // El badge logística redirige a /picking-fefo por defecto; también puede ir al hub
  await page.waitForURL(/\/picking-fefo|\/hub|\/chofer-pod/, { timeout: 20_000 })
}

async function goToChoferPod(page) {
  await page.goto('/chofer-pod')
  await page.waitForURL(/\/chofer-pod/, { timeout: 10_000 })
  // Esperar el heading principal (siempre presente, fuera de v-if)
  await page.locator('h1').filter({ hasText: /Entregas del turno/i }).waitFor({
    state: 'visible',
    timeout: 30_000,
  })
}

async function waitForDNList(page) {
  // Esperar que desaparezca el skeleton (v-if="loading" → false)
  // o que aparezca el EmptyState
  await page.locator('.gcma-data-row, [data-testid="empty-state"]').first().waitFor({
    state: 'visible',
    timeout: 20_000,
  }).catch(async () => {
    // fallback: buscar el texto "Aucune livraison"
    await expect(
      page.getByText(/Aucune livraison|MAT-DN/i).first()
    ).toBeVisible({ timeout: 5_000 })
  })
}

async function drawOnCanvas(page) {
  const canvas = page.locator('canvas')
  const box = await canvas.boundingBox()
  if (!box) return
  await page.mouse.move(box.x + 50,  box.y + 50)
  await page.mouse.down()
  await page.mouse.move(box.x + 120, box.y + 70)
  await page.mouse.move(box.x + 200, box.y + 100)
  await page.mouse.move(box.x + 250, box.y + 80)
  await page.mouse.up()
}

async function uploadFakePhoto(page) {
  const fakeBuffer = Buffer.from(FAKE_JPG_B64, 'base64')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'sello.jpg',
    mimeType: 'image/jpeg',
    buffer: fakeBuffer,
  })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('S10 — Chofer POD', () => {
  // ── S10-A ──────────────────────────────────────────────────────────────────
  test('S10-A: Login badge chofer → accede a /chofer-pod', async ({ page }) => {
    await loginChofer(page)
    await goToChoferPod(page)

    await expect(page.getByText(/App Chofer POD/i)).toBeVisible()
    await expect(page.getByText(/Entregas del turno/i)).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S10-A-chofer-login.png',
      fullPage: false,
    })
  })

  // ── S10-B ──────────────────────────────────────────────────────────────────
  test('S10-B: Delivery Note de Droguerie Atlas Test aparece en lista', async ({ page }) => {
    await loginChofer(page)
    await goToChoferPod(page)
    await waitForDNList(page)

    await expect(page.getByText(DN_ID)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(DN_CUSTOMER).first()).toBeVisible()

    await page.screenshot({
      path: 'tests/e2e/evidence/S10-B-dn-list.png',
      fullPage: false,
    })
  })

  // ── S10-C ──────────────────────────────────────────────────────────────────
  test('S10-C: Canvas firma + foto habilitan botón Valider POD', async ({ page }) => {
    await loginChofer(page)
    await goToChoferPod(page)
    await waitForDNList(page)

    // Seleccionar el DN
    const dnRow = page.locator('.gcma-data-row').filter({ hasText: DN_ID })
    await expect(dnRow).toBeVisible({ timeout: 10_000 })
    await dnRow.click()

    // Botón deshabilitado sin foto
    const btnValider = page.getByRole('button', { name: /Valider POD/i })
    await expect(btnValider).toBeDisabled()

    // Dibujar en canvas
    await drawOnCanvas(page)

    // Subir foto falsa
    await uploadFakePhoto(page)

    // Verificar que el nombre del fichero aparece
    await expect(page.getByText(/sello\.jpg/i)).toBeVisible({ timeout: 5_000 })

    // Botón debe activarse (DN + foto presentes)
    await expect(btnValider).toBeEnabled({ timeout: 5_000 })

    await page.screenshot({
      path: 'tests/e2e/evidence/S10-C-canvas-photo.png',
      fullPage: false,
    })
  })

  // ── S10-D ──────────────────────────────────────────────────────────────────
  test('S10-D: Valider POD → feedback succès "POD enregistre"', async ({ page }) => {
    const jsErrors = []
    page.on('pageerror', err => jsErrors.push(err.message))

    // Interceptar registrar_pod → respuesta de éxito
    await page.route(/registrar_pod/, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: {
            status: 'success',
            delivery_note: DN_ID,
            estado_entrega_pwa: 'Entregado',
            firma_receptor: `/files/${DN_ID}-signature.png`,
            foto_sello_pod: `/files/${DN_ID}-photo.jpg`,
          },
        }),
      })
    })

    await loginChofer(page)
    await goToChoferPod(page)
    await waitForDNList(page)

    // Seleccionar DN
    const dnRow = page.locator('.gcma-data-row').filter({ hasText: DN_ID })
    await expect(dnRow).toBeVisible({ timeout: 10_000 })
    await dnRow.click()

    // Canvas + foto
    await drawOnCanvas(page)
    await uploadFakePhoto(page)

    // Esperar que el botón esté habilitado
    const btnValider = page.getByRole('button', { name: /Valider POD/i })
    await expect(btnValider).toBeEnabled({ timeout: 5_000 })

    // Enviar
    await btnValider.click()

    // Panel de éxito verde (border-green-200 bg-green-50) debe aparecer con el DN_ID
    const successPanel = page.locator('.border-green-200.bg-green-50')
    await expect(successPanel).toBeVisible({ timeout: 10_000 })
    await expect(successPanel).toContainText('POD enregistre', { timeout: 5_000 })
    await expect(successPanel).toContainText(DN_ID, { timeout: 5_000 })

    if (jsErrors.length > 0) {
      console.warn('⚠ JS errors during S10-D:', jsErrors)
    }

    await page.screenshot({
      path: 'tests/e2e/evidence/S10-D-pod-success.png',
      fullPage: false,
    })
  })
})
