import { expect } from '@playwright/test'

const BADGE_TOKEN = process.env.PLAYWRIGHT_BADGE_TOKEN ?? 'OP-2026-BADGE-00042'

export async function loginToRoute(page, routePath) {
  await page.goto('/')
  await page.getByRole('button', { name: /saisie manuelle/i }).click()
  await page.getByPlaceholder('OP-2026-BADGE-00042').fill(BADGE_TOKEN)
  await page.getByRole('button', { name: /^valider$/i }).click()
  await page.waitForURL(/\/hub|\/tareas/, { timeout: 15_000 })

  if (routePath) {
    await page.goto(routePath)
    await expect(page).toHaveURL(new RegExp(`${escapeRegex(routePath)}$`), { timeout: 15_000 })
  }
}

export async function submitManualValue(page, value, placeholderPattern) {
  await page.getByRole('button', { name: /saisie manuelle|saisie lot/i }).click()
  await page.getByPlaceholder(placeholderPattern).fill(value)
  await page.getByRole('button', { name: /^valider$/i }).click()
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}