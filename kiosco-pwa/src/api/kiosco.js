/**
 * Kiosk API — typed wrappers for Frappe endpoints.
 */
import client from './client'

const BASE = '/api/method/gcma_kiosco.api.kiosco'
const QUALITY_BASE = '/api/method/gcma_kiosco.api.calidad'

/** EP1 — Login operario via QR badge token */
export function loginOperario(qrToken) {
  return client.post(`${BASE}.login_operario`, { qr_token: qrToken })
}

export function getOperarioSession() {
  return client.get(`${BASE}.get_operario_session`)
}

export function logoutOperario() {
  return client.post(`${BASE}.logout_operario`)
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

/** EP4 — Reportar consumo real y cerrar producción */
export function reportarConsumo(workOrder, lotesUsados = {}, consumosExtra = {}) {
  return client.post(`${BASE}.reportar_consumo`, {
    work_order: workOrder,
    lotes_usados: JSON.stringify(lotesUsados),
    consumos_extra: JSON.stringify(consumosExtra),
  })
}

export function getLotesCuarentena(warehouse) {
  const params = {}
  if (warehouse) params.warehouse = warehouse
  return client.get(`${QUALITY_BASE}.get_lotes_cuarentena`, { params })
}

export function aprobarCalidad({
  itemCode,
  batchNo,
  qty,
  parametros,
  aprobada,
  resultado,
  remarks,
}) {
  return client.post(`${QUALITY_BASE}.aprobar_calidad`, {
    item_code: itemCode,
    batch_no: batchNo,
    qty,
    parametros: JSON.stringify(parametros ?? {}),
    aprobada,
    resultado,
    remarks,
  })
}
