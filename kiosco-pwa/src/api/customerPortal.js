import client from './client'

const PORTAL_BASE = '/api/method/maroc_b2b.api.comercial'
const PORTAL_BASE_FALLBACK = '/api/method/gcma_kiosco.api.comercial'

function shouldFallback(error) {
  const text = JSON.stringify(error || {})
  return text.includes('App maroc_b2b is not installed')
}

async function withNamespaceFallback(requestPrimary, requestFallback) {
  try {
    return await requestPrimary()
  } catch (error) {
    if (shouldFallback(error)) {
      return requestFallback()
    }
    throw error
  }
}

export function getPortalDashboard(idCliente) {
  const params = {}
  if (idCliente) params.id_cliente = idCliente
  return withNamespaceFallback(
    () => client.get(`${PORTAL_BASE}.get_portal_dashboard`, { params }),
    () => client.get(`${PORTAL_BASE_FALLBACK}.get_portal_dashboard`, { params }),
  )
}

export function getPortalEstadoCuenta(idCliente, limit = 20) {
  const params = { limit }
  if (idCliente) params.id_cliente = idCliente
  return withNamespaceFallback(
    () => client.get(`${PORTAL_BASE}.get_portal_estado_cuenta`, { params }),
    () => client.get(`${PORTAL_BASE_FALLBACK}.get_portal_estado_cuenta`, { params }),
  )
}

export function crearPedidoPortal({ id_cliente, items }) {
  const payload = {
    id_cliente,
    items: JSON.stringify(items ?? []),
  }

  return withNamespaceFallback(
    () => client.post(`${PORTAL_BASE}.crear_pedido_portal`, payload),
    () => client.post(`${PORTAL_BASE_FALLBACK}.crear_pedido_portal`, payload),
  )
}

/** S08 — Estado de cuenta de un cliente (bloqueo por mora) */
export function getEstadoCuenta(idCliente) {
  return withNamespaceFallback(
    () => client.get(`${PORTAL_BASE}.get_estado_cuenta`, { params: { id_cliente: idCliente } }),
    () => client.get(`${PORTAL_BASE_FALLBACK}.get_estado_cuenta`, { params: { id_cliente: idCliente } }),
  )
}

/** S08 — Sincronizar pedidos offline como Sales Orders */
export function syncPedidosOffline(pedidos) {
  return withNamespaceFallback(
    () => client.post(`${PORTAL_BASE}.sync_pedidos_offline`, { pedidos: JSON.stringify(pedidos) }),
    () => client.post(`${PORTAL_BASE_FALLBACK}.sync_pedidos_offline`, { pedidos: JSON.stringify(pedidos) }),
  )
}

/** S07 — Catálogo de ítems con stock proyectado para el comercial */
export function getCatalogoStock({ search, warehouse, limit = 40 } = {}) {
  const params = { limit }
  if (search) params.search = search
  if (warehouse) params.warehouse = warehouse
  return withNamespaceFallback(
    () => client.get(`${PORTAL_BASE}.get_catalogo_stock`, { params }),
    () => client.get(`${PORTAL_BASE_FALLBACK}.get_catalogo_stock`, { params }),
  )
}

/** S08 — Registro de cobro (cheque/efectivo) desde PWA comercial */
export function postCobro({ id_cliente, monto, modo_pago, referencia, fecha }) {
  const payload = { id_cliente, monto: String(monto), modo_pago }
  if (referencia) payload.referencia = referencia
  if (fecha) payload.fecha = fecha

  return withNamespaceFallback(
    () => client.post(`${PORTAL_BASE}.post_cobro`, payload),
    () => client.post(`${PORTAL_BASE_FALLBACK}.post_cobro`, payload),
  )
}

/** S11 — Saldo y detalle de puntos de fidelidad del cliente */
export function getLoyaltyPoints(idCliente) {
  const params = {}
  if (idCliente) params.id_cliente = idCliente
  return withNamespaceFallback(
    () => client.get(`${PORTAL_BASE}.get_loyalty_points`, { params }),
    () => client.get(`${PORTAL_BASE_FALLBACK}.get_loyalty_points`, { params }),
  )
}

/** S11 — Canjear puntos de fidelidad por descuento en próximo pedido */
export function redimirPuntos({ idCliente, puntos }) {
  const payload = { puntos: String(puntos) }
  if (idCliente) payload.id_cliente = idCliente
  return withNamespaceFallback(
    () => client.post(`${PORTAL_BASE}.redimir_puntos`, payload),
    () => client.post(`${PORTAL_BASE_FALLBACK}.redimir_puntos`, payload),
  )
}

export async function createSupportTicket(description, b64Photo, affectedBatch, idCliente) {
  const payload = {
    description,
    b64Photo,
    affectedBatch,
  }

  if (idCliente) payload.id_cliente = idCliente

  return withNamespaceFallback(
    () => client.post(`${PORTAL_BASE}.create_support_ticket`, payload),
    () => client.post(`${PORTAL_BASE_FALLBACK}.create_support_ticket`, payload),
  )
}
