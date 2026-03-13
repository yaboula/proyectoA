<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { AlertTriangle, BarChart3, Camera, Download, MapPin, RefreshCcw, Siren, Target } from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import {
  exportScorecardCsv,
  getCoberturaMapa,
  getPanelGerencial360,
  getReporteFotosCompetencia,
  runAlertaAbandonoClientes,
} from '../api/gerencial'

const loading = ref(false)
const runningAlert = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const fecha = ref(new Date().toISOString().slice(0, 10))
const panel = ref(null)
const cobertura = ref([])
const fotos = ref([])

const mapElement = ref(null)
let mapInstance = null
let markerLayer = null

const scorecard = computed(() => panel.value?.scorecard ?? [])
const hitRate = computed(() => panel.value?.hit_rate ?? {
  total_visitas: 0,
  visitas_con_pedido: 0,
  visitas_sin_pedido: 0,
  hit_rate: 0,
  por_comercial: [],
})

function normalizeError(error, fallback) {
  if (typeof error === 'string') return error
  return error?.message || error?.message_fr || fallback
}

function formatMoney(value) {
  return `${Number(value || 0).toFixed(2)} MAD`
}

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

async function initMap() {
  if (mapInstance || !mapElement.value) return

  const L = await import('leaflet')
  await import('leaflet/dist/leaflet.css')

  mapInstance = L.map(mapElement.value, {
    zoomControl: true,
    minZoom: 4,
    maxZoom: 12,
  }).setView([31.8, -7.1], 5)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(mapInstance)

  markerLayer = L.layerGroup().addTo(mapInstance)
}

async function renderMarkers() {
  await initMap()
  if (!mapInstance || !markerLayer) return

  const L = await import('leaflet')
  markerLayer.clearLayers()

  const bounds = []

  for (const row of cobertura.value) {
    const lat = Number(row.lat)
    const lng = Number(row.lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue

    const color = row.es_desviacion ? '#dc2626' : '#16a34a'
    const marker = L.circleMarker([lat, lng], {
      radius: 7,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: 0.8,
    })

    marker.bindPopup(`
      <strong>${row.comercial || 'N/A'}</strong><br>
      Client: ${row.cliente || '-'}<br>
      Heure: ${row.time || '-'}<br>
      Etat: ${row.estado_visita}
    `)

    marker.addTo(markerLayer)
    bounds.push([lat, lng])
  }

  if (bounds.length) {
    mapInstance.fitBounds(bounds, { padding: [24, 24], maxZoom: 10 })
  }
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const [panelRes, mapaRes, fotosRes] = await Promise.all([
      getPanelGerencial360(fecha.value),
      getCoberturaMapa(fecha.value),
      getReporteFotosCompetencia(30),
    ])

    panel.value = panelRes
    cobertura.value = mapaRes?.rows ?? []
    fotos.value = fotosRes?.rows ?? []

    await nextTick()
    await renderMarkers()
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Impossible de charger le dashboard gerencial.')
    panel.value = null
    cobertura.value = []
    fotos.value = []
  } finally {
    loading.value = false
  }
}

async function triggerAlertaAbandono() {
  if (runningAlert.value) return

  runningAlert.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const result = await runAlertaAbandonoClientes(fecha.value)
    successMessage.value = `Alerte executee: ${result?.total_alertas ?? 0} clients detectes.`
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Echec de lancement de l alerte quotidienne.')
  } finally {
    runningAlert.value = false
  }
}

async function downloadScorecardCsv() {
  errorMessage.value = ''

  try {
    const response = await exportScorecardCsv(fecha.value)
    const content = response?.content || ''
    const filename = response?.filename || `scorecard_${fecha.value}.csv`

    const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Echec de l export CSV.')
  }
}

onMounted(loadDashboard)

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markerLayer = null
  }
})
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <BarChart3 :size="14" />
            Panel Gerencial 360
          </div>
          <div>
            <div class="gcma-section-label">Direction Commerciale</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">
              Centro de mando B2B
            </h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Scorecard de droguerias, cobertura GPS con desviaciones y alerta diaria de abandono de clientes top.
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <input
            v-model="fecha"
            type="date"
            class="h-12 rounded-md border border-zinc-300 bg-white px-3 text-sm font-semibold text-zinc-900"
          >
          <button
            type="button"
            :disabled="loading"
            @click="loadDashboard"
            class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 disabled:opacity-40 transition flex items-center justify-center gap-2"
          >
            <RefreshCcw :size="18" />
            Actualiser
          </button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      {{ errorMessage }}
    </div>

    <div v-if="successMessage" class="rounded-md border border-green-200 bg-green-50 p-5 text-sm text-green-700">
      {{ successMessage }}
    </div>

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <article class="gcma-stat">
        <div class="gcma-section-label">Clientes scorecard</div>
        <div class="mt-1 text-2xl font-black text-zinc-900">{{ scorecard.length }}</div>
      </article>
      <article class="gcma-stat">
        <div class="gcma-section-label">Check-ins del dia</div>
        <div class="mt-1 text-2xl font-black text-zinc-900">{{ panel?.cobertura_resumen?.total_checkins || 0 }}</div>
      </article>
      <article class="gcma-stat">
        <div class="gcma-section-label">Desviaciones</div>
        <div class="mt-1 text-2xl font-black text-red-600">{{ panel?.cobertura_resumen?.desviaciones || 0 }}</div>
      </article>
      <article class="gcma-stat">
        <div class="gcma-section-label">Hit-rate</div>
        <div class="mt-1 text-2xl font-black text-green-700">{{ formatPercent(hitRate.hit_rate) }}</div>
      </article>
    </div>

    <div class="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
      <section class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="gcma-toolbar items-start">
          <div>
            <div class="gcma-section-label">Cobertura GPS</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
              <MapPin :size="20" class="text-blue-700" />
              Rutas y desviaciones
            </h2>
          </div>
          <span class="kiosk-chip rounded-md px-3 py-1 text-xs font-bold">
            Verde valida | Rouge desviada
          </span>
        </div>

        <div ref="mapElement" class="mt-4 h-88 w-full rounded-md border border-zinc-200" />
      </section>

      <section class="kiosk-panel rounded-md p-5 md:p-6 space-y-3">
        <div>
          <div class="gcma-section-label">Hit-rate</div>
          <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
            <Target :size="20" class="text-blue-700" />
            Visites avec/sans commande
          </h2>
        </div>

        <div class="kiosk-panel-soft rounded-md border p-4">
          <div class="text-sm text-zinc-500">Con pedido</div>
          <div class="mt-1 text-xl font-black text-green-700">{{ hitRate.visitas_con_pedido }}</div>
          <div class="mt-3 h-3 rounded-md bg-zinc-200">
            <div
              class="h-3 rounded-md bg-green-600"
              :style="{ width: `${Math.max(2, Number(hitRate.hit_rate || 0) * 100)}%` }"
            />
          </div>
        </div>

        <div class="kiosk-panel-soft rounded-md border p-4">
          <div class="text-sm text-zinc-500">Sin pedido</div>
          <div class="mt-1 text-xl font-black text-amber-700">{{ hitRate.visitas_sin_pedido }}</div>
          <div class="mt-3 h-3 rounded-md bg-zinc-200">
            <div
              class="h-3 rounded-md bg-amber-500"
              :style="{ width: `${Math.max(2, (1 - Number(hitRate.hit_rate || 0)) * 100)}%` }"
            />
          </div>
        </div>

        <button
          type="button"
          :disabled="runningAlert"
          @click="triggerAlertaAbandono"
          class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
        >
          <Siren :size="18" />
          {{ runningAlert ? 'Execution...' : 'Lancer alerte abandon' }}
        </button>

        <button
          type="button"
          @click="downloadScorecardCsv"
          class="h-12 w-full rounded-md border border-zinc-300 bg-white px-4 text-sm font-bold text-zinc-700 active:bg-zinc-50 transition flex items-center justify-center gap-2"
        >
          <Download :size="18" />
          Export CSV
        </button>
      </section>
    </div>

    <section class="kiosk-panel rounded-md p-5 md:p-6">
      <div class="gcma-toolbar items-start">
        <div>
          <div class="gcma-section-label">Scorecard</div>
          <h2 class="mt-1 text-xl font-black text-zinc-900">Facturation vs dette vs frequence</h2>
        </div>
      </div>

      <div class="mt-4 overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead>
            <tr class="border-b border-zinc-200 text-zinc-500">
              <th class="px-3 py-2">Client</th>
              <th class="px-3 py-2">YTD</th>
              <th class="px-3 py-2">Dette echue</th>
              <th class="px-3 py-2">Freq/mois</th>
              <th class="px-3 py-2">Jours sans achat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in scorecard.slice(0, 50)" :key="row.customer" class="border-b border-zinc-100">
              <td class="px-3 py-2">
                <div class="font-semibold text-zinc-900">{{ row.customer_name || row.customer }}</div>
                <div class="text-xs text-zinc-500">{{ row.customer }}</div>
              </td>
              <td class="px-3 py-2 font-semibold text-zinc-900">{{ formatMoney(row.facturacion_ytd) }}</td>
              <td class="px-3 py-2" :class="Number(row.deuda_vencida) > 0 ? 'text-red-600 font-semibold' : 'text-zinc-700'">
                {{ formatMoney(row.deuda_vencida) }}
              </td>
              <td class="px-3 py-2 text-zinc-700">{{ row.frecuencia_mensual }}</td>
              <td class="px-3 py-2 text-zinc-700">{{ row.dias_sin_compra ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="kiosk-panel rounded-md p-5 md:p-6">
      <div class="gcma-toolbar items-start">
        <div>
          <div class="gcma-section-label">Competencia</div>
          <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
            <Camera :size="20" class="text-blue-700" />
            Fotos de precios en calle
          </h2>
        </div>
        <span class="kiosk-chip rounded-md px-3 py-1 text-xs font-bold">{{ fotos.length }} fotos</span>
      </div>

      <div v-if="!fotos.length" class="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 flex items-center gap-2">
        <AlertTriangle :size="16" />
        No hay fotos etiquetadas como competencia/precio para el periodo consultado.
      </div>

      <div v-else class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <a
          v-for="row in fotos"
          :key="`${row.origen_docname}-${row.file_url}`"
          :href="row.file_url"
          target="_blank"
          rel="noreferrer"
          class="gcma-data-row block rounded-md border p-3 transition hover:border-blue-300"
        >
          <div class="text-sm font-semibold text-zinc-900">{{ row.origen_docname }}</div>
          <div class="mt-1 text-xs text-zinc-500">{{ row.created_at }}</div>
          <div class="mt-2 text-xs text-zinc-600 line-clamp-2">{{ row.asunto || row.descripcion || 'Photo concurrence' }}</div>
        </a>
      </div>
    </section>
  </KioskLayout>
</template>
