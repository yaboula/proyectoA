import client from './client'

const GERENCIAL_BASE = '/api/method/maroc_b2b.api.gerencial'
const GERENCIAL_BASE_FALLBACK = '/api/method/gcma_kiosco.api.gerencial'

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

export function getPanelGerencial360(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return withNamespaceFallback(
    () => client.get(`${GERENCIAL_BASE}.get_panel_gerencial_360`, { params }),
    () => client.get(`${GERENCIAL_BASE_FALLBACK}.get_panel_gerencial_360`, { params }),
  )
}

export function getCoberturaMapa(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return withNamespaceFallback(
    () => client.get(`${GERENCIAL_BASE}.get_cobertura_mapa`, { params }),
    () => client.get(`${GERENCIAL_BASE_FALLBACK}.get_cobertura_mapa`, { params }),
  )
}

export function getReporteFotosCompetencia(limit = 50) {
  return withNamespaceFallback(
    () =>
      client.get(`${GERENCIAL_BASE}.get_reporte_fotos_competencia`, {
        params: { limit },
      }),
    () =>
      client.get(`${GERENCIAL_BASE_FALLBACK}.get_reporte_fotos_competencia`, {
        params: { limit },
      }),
  )
}

export function runAlertaAbandonoClientes(fecha) {
  const payload = {}
  if (fecha) payload.fecha = fecha
  return withNamespaceFallback(
    () => client.post(`${GERENCIAL_BASE}.run_alerta_abandono_clientes`, payload),
    () => client.post(`${GERENCIAL_BASE_FALLBACK}.run_alerta_abandono_clientes`, payload),
  )
}

export function exportScorecardCsv(fecha) {
  const params = {}
  if (fecha) params.fecha = fecha
  return withNamespaceFallback(
    () => client.get(`${GERENCIAL_BASE}.export_scorecard_csv`, { params }),
    () => client.get(`${GERENCIAL_BASE_FALLBACK}.export_scorecard_csv`, { params }),
  )
}
