<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  CloudOff,
  DatabaseZap,
  Eraser,
  RefreshCcw,
  ScanLine,
  Send,
  Warehouse,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import ManualInputModal from '../components/ManualInputModal.vue'
import { useOperarioStore } from '../stores/operario'
import { useBlindInventoryStore } from '../stores/blindInventory'
import { useSyncQueueStore } from '../stores/syncQueue'
import { useScanner } from '../composables/useScanner'
import { subirConteoFisico } from '../api/kiosco'

const router = useRouter()
const operarioStore = useOperarioStore()
const blindStore = useBlindInventoryStore()
const syncQueueStore = useSyncQueueStore()

const loading = ref(false)
const submitting = ref(false)
const manualOpen = ref(false)
const manualValue = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const queueMessage = ref('')
const lastResult = ref(null)

const companyAbbr = computed(() => operarioStore.operario?.company_abbr ?? 'PDM')
const warehouseOptions = computed(() => [
  `Materia Prima Aprobada - ${companyAbbr.value}`,
  `Cuarentena MP - ${companyAbbr.value}`,
  `Producto Terminado - ${companyAbbr.value}`,
  `Cuarentena PT - ${companyAbbr.value}`,
])
const activeWarehouse = computed(() => blindStore.activeWarehouse || warehouseOptions.value[0])
const entries = computed(() => blindStore.currentEntries)
const totalScans = computed(() => blindStore.totalScans)
const distinctLots = computed(() => blindStore.distinctLots)
const pendingSync = computed(() => syncQueueStore.pendingCount)

function ensureWarehouseSelection() {
  if (!blindStore.activeWarehouse) {
    blindStore.setActiveWarehouse(warehouseOptions.value[0])
  }
}

function setWarehouse(warehouse) {
  blindStore.setActiveWarehouse(warehouse)
  errorMessage.value = ''
  successMessage.value = ''
  queueMessage.value = ''
}

function handleInventoryScan(rawValue) {
  errorMessage.value = ''
  successMessage.value = ''
  queueMessage.value = ''

  try {
    blindStore.addScan(activeWarehouse.value, rawValue)
  } catch {
    errorMessage.value = 'QR invalide. Format attendu: item_code|batch_no.'
  }
}

function submitManual(rawValue) {
  try {
    blindStore.addManualEntry(activeWarehouse.value, rawValue, 1)
    manualOpen.value = false
    manualValue.value = ''
    errorMessage.value = ''
  } catch {
    errorMessage.value = 'Saisie invalide. Utiliser item_code|batch_no.'
  }
}

function adjustQty(row, delta) {
  blindStore.updateEntryQty(
    activeWarehouse.value,
    row.item_code,
    row.batch_no,
    Number(row.qty_fisica ?? 0) + delta,
  )
}

function clearCurrentWarehouse() {
  blindStore.clearWarehouse(activeWarehouse.value)
  successMessage.value = ''
  queueMessage.value = ''
  errorMessage.value = ''
  lastResult.value = null
}

async function submitCount() {
  const conteo = blindStore.buildPayload(activeWarehouse.value)
  if (!conteo.length || submitting.value) return

  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  queueMessage.value = ''

  try {
    const offline = typeof navigator !== 'undefined' && !navigator.onLine
    if (offline) {
      throw new Error('NETWORK_OFFLINE')
    }

    const result = await subirConteoFisico(activeWarehouse.value, conteo)
    lastResult.value = result
    blindStore.clearWarehouse(activeWarehouse.value)
    successMessage.value = `Brouillon cree: ${result.reconciliation_doc}.`
  } catch (error) {
    const message = error?.message_fr || error?.message || ''
    const isOffline = message.includes('Network Error') || message.includes('NETWORK_OFFLINE')

    if (isOffline) {
      syncQueueStore.enqueueOperation('EP_REC_5_SUBIR_CONTEO', {
        warehouse: activeWarehouse.value,
        conteo,
      }, {
        title: `Inventaire rapide ${activeWarehouse.value}`,
      })
      blindStore.clearWarehouse(activeWarehouse.value)
      queueMessage.value = 'Comptage sauvegarde hors ligne et mis en file de synchronisation.'
    } else {
      errorMessage.value = error?.message_fr || 'Le brouillon de reconciliation n a pas pu etre cree.'
    }
  } finally {
    submitting.value = false
  }
}

async function syncPendingQueue() {
  loading.value = true
  try {
    const synced = await syncQueueStore.syncAll()
    if (synced) {
      successMessage.value = 'La file differee a ete synchronisee.'
      queueMessage.value = ''
    } else if (pendingSync.value > 0) {
      queueMessage.value = 'Aucune ligne n a pu etre synchronisee pour le moment.'
    }
  } finally {
    loading.value = false
  }
}

const { isScanning } = useScanner(handleInventoryScan, { disabled: submitting })

onMounted(async () => {
  const hasSession = await operarioStore.ensureSession()
  if (!hasSession || !operarioStore.hasModule('reception')) {
    router.replace({ name: 'hub' })
    return
  }

  ensureWarehouseSelection()
})
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <ClipboardList :size="14" />
            Inventaire rapide
          </div>
          <div>
            <div class="gcma-section-label">Inventaire aveugle</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Comptage physique continu</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Scanner en continu sans appel serveur, consolider localement puis envoyer un brouillon de reconciliation ERPNext quand le poste est pret.
            </p>
          </div>
        </div>

        <div class="w-full max-w-md space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="gcma-stat">
              <div class="gcma-section-label">Scans</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ totalScans }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Lots</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ distinctLots }}</div>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="gcma-stat">
              <div class="gcma-section-label">Entrepot actif</div>
              <div class="mt-1 text-sm font-bold text-zinc-900">{{ activeWarehouse }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Sync differee</div>
              <div class="mt-1 text-sm font-bold text-zinc-900">{{ pendingSync }} element(s)</div>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <button @click="router.push({ name: 'recepcion' })"
                    class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 active:bg-zinc-50 transition flex items-center justify-center gap-2">
              <ArrowLeft :size="18" />
              Retour reception
            </button>
            <button @click="manualOpen = true"
                    class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 transition flex items-center justify-center gap-2">
              <ScanLine :size="18" />
              Saisie manuelle
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
      <div class="flex items-center gap-3">
        <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-blue-700">
          <RefreshCcw v-if="loading || isScanning" :size="22" class="animate-spin" />
          <Warehouse v-else :size="22" />
        </div>
        <div>
          <div class="gcma-section-label">Scan continu</div>
          <div class="text-lg font-bold text-zinc-900">{{ isScanning ? 'Lecture du code...' : 'Lecteur HID actif sans postback serveur' }}</div>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-4">
        <button v-for="warehouse in warehouseOptions"
                :key="warehouse"
                @click="setWarehouse(warehouse)"
                :class="warehouse === activeWarehouse ? 'border-blue-600 bg-blue-600 text-white' : 'border-zinc-300 bg-white text-zinc-700'"
                class="h-12 rounded-md border px-4 text-sm font-bold transition active:opacity-90">
          {{ warehouse }}
        </button>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700 flex items-start gap-3">
      <AlertTriangle :size="18" class="mt-0.5 shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>

    <div v-if="successMessage" class="rounded-md border border-green-200 bg-green-50 p-5 text-sm text-green-700 flex items-start gap-3">
      <CheckCircle2 :size="18" class="mt-0.5 shrink-0" />
      <span>{{ successMessage }}</span>
    </div>

    <div v-if="queueMessage" class="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-700 flex items-start gap-3">
      <CloudOff :size="18" class="mt-0.5 shrink-0" />
      <span>{{ queueMessage }}</span>
    </div>

    <EmptyState v-if="!entries.length"
                :icon="DatabaseZap"
                title="Aucun comptage local"
                message="Scanner des etiquettes Zebra QA ou saisir manuellement item_code|batch_no." />

    <div v-else class="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-3">
        <div v-for="row in entries" :key="`${row.item_code}-${row.batch_no}`" class="gcma-data-row p-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div class="text-lg font-bold text-zinc-900">{{ row.item_code }}</div>
            <div class="mt-1 text-sm text-zinc-500">{{ row.batch_no }}</div>
          </div>

          <div class="flex items-center gap-2">
            <button @click="adjustQty(row, -1)"
                    class="h-12 w-12 rounded-md border border-zinc-300 bg-white text-lg font-black text-zinc-700 active:bg-zinc-50 transition">
              -
            </button>
            <div class="gcma-stat min-w-24 text-center">
              <div class="gcma-section-label">Qté</div>
              <div class="mt-1 text-xl font-black text-zinc-900">{{ row.qty_fisica }}</div>
            </div>
            <button @click="adjustQty(row, 1)"
                    class="h-12 w-12 rounded-md border border-blue-200 bg-blue-50 text-lg font-black text-blue-700 active:bg-blue-100 transition">
              +
            </button>
          </div>
        </div>
      </div>

      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Cloture</div>
          <div class="mt-1 text-lg font-bold text-zinc-900">Envoyer le brouillon ERPNext</div>
          <p class="mt-2 text-sm text-zinc-500">Le comptage cree un document `Stock Reconciliation` en brouillon. Si le reseau tombe, la soumission passe en file differee locale.</p>
        </div>

        <button @click="submitCount"
                :disabled="submitting || !entries.length"
                class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2">
          <Send :size="18" />
          {{ submitting ? 'Envoi en cours...' : 'Envoyer le comptage' }}
        </button>

        <div class="grid gap-3 sm:grid-cols-2">
          <button @click="syncPendingQueue"
                  :disabled="loading || pendingSync === 0"
                  class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 disabled:opacity-40 transition flex items-center justify-center gap-2">
            <RefreshCcw :size="18" />
            Sync file differee
          </button>
          <button @click="clearCurrentWarehouse"
                  :disabled="!entries.length"
                  class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 active:bg-zinc-50 disabled:opacity-40 transition flex items-center justify-center gap-2">
            <Eraser :size="18" />
            Vider l'entrepot
          </button>
        </div>

        <div v-if="lastResult" class="gcma-data-row p-4 text-sm text-zinc-600">
          <div><span class="text-zinc-400">Document:</span> {{ lastResult.reconciliation_doc }}</div>
          <div class="mt-1"><span class="text-zinc-400">Lignes:</span> {{ lastResult.items_count }}</div>
        </div>
      </div>
    </div>

    <ManualInputModal v-model="manualValue"
                      :open="manualOpen"
                      title="Saisie manuelle inventaire"
                      description="Entrer item_code|batch_no pour ajouter une unite au comptage local."
                      placeholder="MP-RES-ALK-G70|LOTE-CIEGO-2026-0001"
                      :min-length="8"
                      @close="manualOpen = false"
                      @submit="submitManual" />
  </KioskLayout>
</template>
