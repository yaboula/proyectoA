/**
 * Kiosk API — typed wrappers for Frappe endpoints.
 */
import client from './client'

const BASE = '/api/method/gcma_kiosco.api.kiosco'

/** EP1 — Login operario via QR badge token */
export function loginOperario(qrToken) {
  return client.post(`${BASE}.login_operario`, { qr_token: qrToken })
}

/** EP2 — Tareas (Work Orders pendientes) */
export function getTareas(company, warehouse) {
  const params = { company }
  if (warehouse) params.warehouse = warehouse
  return client.get(`${BASE}.get_tareas`, { params })
}

/** EP3 — Validar material (Poka-Yoke) */
export function validarMaterial(workOrder, qrData) {
  return client.post(`${BASE}.validar_material`, {
    work_order: workOrder,
    qr_data: qrData,
  })
}

/** EP4 — Reportar consumo real (cierre producción) */
export function reportarConsumo(workOrder, extras = []) {
  return client.post(`${BASE}.reportar_consumo`, {
    work_order: workOrder,
    extras: JSON.stringify(extras),
  })
}
