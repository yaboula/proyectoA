/**
 * Kiosk API — typed wrappers for Frappe endpoints.
 */
import client from './client'

const BASE = '/api/method/gcma_kiosco.api.kiosco'
const QUALITY_BASE = '/api/method/gcma_kiosco.api.calidad'
const RECEPTION_BASE = '/api/method/gcma_kiosco.api.recepcion'
const B2B_COMERCIAL_BASE = '/api/method/maroc_b2b.api.comercial'
const B2B_COMERCIAL_BASE_FALLBACK = '/api/method/gcma_kiosco.api.comercial'
const B2B_LOGISTICA_BASE = '/api/method/maroc_b2b.api.logistica'

function shouldNamespaceFallback(error) {
  const text = JSON.stringify(error || {})
  return text.includes('App maroc_b2b is not installed')
}

async function withNamespaceFallback(primaryRequest, fallbackRequest) {
  try {
    return await primaryRequest()
  } catch (error) {
    if (shouldNamespaceFallback(error)) {
      return fallbackRequest()
    }
    throw error
  }
}

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

/** EP5 — Consulta informativa de lote */
export function getInfoLote(batchNo, itemCode) {
  const params = { batch_no: batchNo }
  if (itemCode) params.item_code = itemCode
  return client.get(`${BASE}.info_lote`, { params })
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

export function getComprasPendientes(company, warehouse) {
  const params = { company }
  if (warehouse) params.warehouse = warehouse
  return client.get(`${RECEPTION_BASE}.get_compras_pendientes`, { params })
}

export function registrarRecepcion(poName, itemsRecibidos, warehouse) {
  const payload = {
    po_name: poName,
    items_recibidos: JSON.stringify(itemsRecibidos ?? []),
  }
  if (warehouse) payload.warehouse = warehouse
  return client.post(`${RECEPTION_BASE}.registrar_recepcion`, payload)
}

export function trasladarLoteAprobado({ itemCode, batchNo, qtyToMove, sourceWarehouse, targetWarehouse }) {
  const payload = {
    item_code: itemCode,
    batch_no: batchNo,
    qty_to_move: qtyToMove,
  }
  if (sourceWarehouse) payload.source_warehouse = sourceWarehouse
  if (targetWarehouse) payload.target_warehouse = targetWarehouse
  return client.post(`${RECEPTION_BASE}.trasladar_lote_aprobado`, payload)
}

export function getLoteParaImpresion(batchNo) {
  return client.get(`${RECEPTION_BASE}.get_lote_para_impresion`, {
    params: { batch_no: batchNo },
  })
}

export function subirConteoFisico(warehouse, conteo) {
  return client.post(`${RECEPTION_BASE}.subir_conteo_fisico`, {
    warehouse,
    conteo: JSON.stringify(conteo ?? []),
  })
}

export function getRutaDia() {
  return withNamespaceFallback(
    () => client.get(`${B2B_COMERCIAL_BASE}.get_ruta_dia`),
    () => client.get(`${B2B_COMERCIAL_BASE_FALLBACK}.get_ruta_dia`),
  )
}

export function postCheckin({ id_cliente, gps_lat_capturada, gps_lng_capturada, timestamp }) {
  const payload = {
    id_cliente,
    gps_lat_capturada,
    gps_lng_capturada,
    timestamp,
  }

  return withNamespaceFallback(
    () => client.post(`${B2B_COMERCIAL_BASE}.post_checkin`, payload),
    () => client.post(`${B2B_COMERCIAL_BASE_FALLBACK}.post_checkin`, payload),
  )
}

/** S09 — Lista de picking FEFO para un Sales Order */
export function getPickList(salesOrder) {
  return client.get(`${B2B_LOGISTICA_BASE}.get_pick_list`, {
    params: { sales_order: salesOrder },
  })
}

/** S09 — Validar scan FEFO con control de cantidad acumulada */
export function validarScanFefo({ sales_order, item_code, batch_scanned, qty_ya_escaneada = 0 }) {
  return client.post(`${B2B_LOGISTICA_BASE}.validar_scan_fefo`, {
    sales_order,
    item_code,
    batch_scanned,
    qty_ya_escaneada,
  })
}

/** S09 — Override de lote FEFO autorizado por PIN de encargado */
export function overrideFefoBatch({ sales_order, item_code, batch_requested, pin_manager, justificacion, qty_ya_escaneada = 0 }) {
  return client.post(`${B2B_LOGISTICA_BASE}.override_fefo_batch`, {
    sales_order,
    item_code,
    batch_requested,
    pin_manager,
    justificacion,
    qty_ya_escaneada,
  })
}

/** S10 — Entregas pendientes del turno del chofer */
export function getEntregasPendientesChofer(limit = 50) {
  return client.get(`${B2B_LOGISTICA_BASE}.get_entregas_pendientes_chofer`, {
    params: { limit },
  })
}

export function registrarPod({ delivery_note_id, b64_signature, b64_photo }) {
  return client.post(`${B2B_LOGISTICA_BASE}.registrar_pod`, {
    delivery_note_id,
    b64_signature,
    b64_photo,
  })
}
