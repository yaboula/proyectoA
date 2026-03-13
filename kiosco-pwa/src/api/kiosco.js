/**
 * Kiosk API — typed wrappers for Frappe endpoints.
 */
import client from './client'

const BASE = '/api/method/gcma_kiosco.api.kiosco'
const QUALITY_BASE = '/api/method/gcma_kiosco.api.calidad'
const RECEPTION_BASE = '/api/method/gcma_kiosco.api.recepcion'
const B2B_COMERCIAL_BASE = '/api/method/maroc_b2b.api.comercial'
const B2B_LOGISTICA_BASE = '/api/method/maroc_b2b.api.logistica'

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
  return client.get(`${B2B_COMERCIAL_BASE}.get_ruta_dia`)
}

export function postCheckin({ id_cliente, gps_lat_capturada, gps_lng_capturada, timestamp }) {
  return client.post(`${B2B_COMERCIAL_BASE}.post_checkin`, {
    id_cliente,
    gps_lat_capturada,
    gps_lng_capturada,
    timestamp,
  })
}

export function validarScanFefo({ sales_order, item_code, batch_scanned }) {
  return client.post(`${B2B_LOGISTICA_BASE}.validar_scan_fefo`, {
    sales_order,
    item_code,
    batch_scanned,
  })
}

export function getEntregasPendientesChofer() {
  return client.get('/api/resource/Delivery Note', {
    params: {
      fields: JSON.stringify(['name', 'customer', 'posting_date', 'status', 'docstatus']),
      filters: JSON.stringify([['docstatus', 'in', [0, 1]], ['status', 'not in', ['Completed', 'Closed']]]),
      order_by: 'posting_date asc',
      limit_page_length: 50,
    },
  })
}

export function registrarPod({ delivery_note_id, b64_signature, b64_photo }) {
  return client.post(`${B2B_LOGISTICA_BASE}.registrar_pod`, {
    delivery_note_id,
    b64_signature,
    b64_photo,
  })
}
