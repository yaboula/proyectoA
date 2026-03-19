import client from './client'

const BASE = '/api/method/gcma_kiosco.api.gerencial'

export function getPanelGerencial360(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return client.get(`${BASE}.get_panel_gerencial_360`, { params })
}

export function getCoberturaMapa(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return client.get(`${BASE}.get_cobertura_mapa`, { params })
}

export function getReporteFotosCompetencia(limit = 50) {
  return client.get(`${BASE}.get_reporte_fotos_competencia`, { params: { limit } })
}

export function runAlertaAbandonoClientes(fecha) {
  const payload = {}
  if (fecha) payload.fecha = fecha
  return client.post(`${BASE}.run_alerta_abandono_clientes`, payload)
}

export function exportScorecardCsv(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return client.get(`${BASE}.export_scorecard_csv`, { params })
}
