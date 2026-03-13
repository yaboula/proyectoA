import client from './client'

const PORTAL_BASE = '/api/method/maroc_b2b.api.comercial'

export function getPortalDashboard(idCliente) {
  const params = {}
  if (idCliente) params.id_cliente = idCliente
  return client.get(`${PORTAL_BASE}.get_portal_dashboard`, { params })
}

export function getPortalEstadoCuenta(idCliente, limit = 20) {
  const params = { limit }
  if (idCliente) params.id_cliente = idCliente
  return client.get(`${PORTAL_BASE}.get_portal_estado_cuenta`, { params })
}

export function crearPedidoPortal({ id_cliente, items }) {
  return client.post(`${PORTAL_BASE}.crear_pedido_portal`, {
    id_cliente,
    items: JSON.stringify(items ?? []),
  })
}

export async function createSupportTicket(description, b64Photo, affectedBatch, idCliente) {
  const payload = {
    description,
    b64Photo,
    affectedBatch,
  }

  if (idCliente) payload.id_cliente = idCliente

  return client.post(`${PORTAL_BASE}.create_support_ticket`, payload)
}
