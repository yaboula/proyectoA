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
