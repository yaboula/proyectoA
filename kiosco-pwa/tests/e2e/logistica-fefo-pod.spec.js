import { expect, test } from '@playwright/test'

test.describe('Logistica FEFO/POD', () => {
  test('@block3 validates FEFO reject/accept and POD invalid/valid payloads', async ({ page }) => {
    const user = process.env.PLAYWRIGHT_MANAGER_USER
    const password = process.env.PLAYWRIGHT_MANAGER_PASSWORD

    test.skip(!user || !password, 'Set PLAYWRIGHT_MANAGER_USER and PLAYWRIGHT_MANAGER_PASSWORD.')

    const salesOrder = process.env.PLAYWRIGHT_FEFO_SO ?? 'SAL-ORD-2026-00001'
    const itemCode = process.env.PLAYWRIGHT_FEFO_ITEM ?? 'MP-H2O-DESMIN'
    const batchWrong = process.env.PLAYWRIGHT_FEFO_BATCH_WRONG ?? 'LOTE-H2O-2026-0001'
    const batchOk = process.env.PLAYWRIGHT_FEFO_BATCH_OK ?? 'LOTE-TEST-H2O-001'
    const deliveryNote = process.env.PLAYWRIGHT_POD_DN ?? 'MAT-DN-2026-00001'

    const loginResponse = await page.request.post('/api/method/login', {
      form: {
        usr: user,
        pwd: password,
      },
    })
    expect(loginResponse.ok()).toBeTruthy()

    const fefoWrong = await page.request.post('/api/method/gcma_kiosco.api.logistica.validar_scan_fefo', {
      form: {
        sales_order: salesOrder,
        item_code: itemCode,
        batch_scanned: batchWrong,
      },
    })
    expect(fefoWrong.status()).toBe(417)

    const fefoOk = await page.request.post('/api/method/gcma_kiosco.api.logistica.validar_scan_fefo', {
      form: {
        sales_order: salesOrder,
        item_code: itemCode,
        batch_scanned: batchOk,
      },
    })
    expect(fefoOk.ok()).toBeTruthy()

    const fefoPayload = await fefoOk.json()
    expect(fefoPayload?.message?.status).toBe('ok')

    const podInvalid = await page.request.post('/api/method/gcma_kiosco.api.logistica.registrar_pod', {
      form: {
        delivery_note_id: deliveryNote,
        b64_signature: 'INVALID@@',
        b64_photo: 'INVALID@@',
      },
    })
    expect(podInvalid.status()).toBe(417)

    const signaturePng = 'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGMUqbjDwMDAxMDAwMDAAAAQQgFsyLsfzAAAAABJRU5ErkJggg=='
    const photoJpg = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDkqKKK/FD+qD//2Q=='

    const podOk = await page.request.post('/api/method/gcma_kiosco.api.logistica.registrar_pod', {
      form: {
        delivery_note_id: deliveryNote,
        b64_signature: signaturePng,
        b64_photo: photoJpg,
      },
    })
    expect(podOk.ok()).toBeTruthy()

    const podPayload = await podOk.json()
    expect(podPayload?.message?.status).toBe('success')
    expect(podPayload?.message?.delivery_note).toBe(deliveryNote)
  })
})
