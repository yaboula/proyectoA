<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  Boxes,
  CheckCircle2,
  MoveRight,
  RefreshCcw,
  ScanLine,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import ManualInputModal from '../components/ManualInputModal.vue'
import { useOperarioStore } from '../stores/operario'
import { useScanner } from '../composables/useScanner'
import { getInfoLote, trasladarLoteAprobado } from '../api/kiosco'

const router = useRouter()
const store = useOperarioStore()

const loading = ref(false)
const transferring = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const manualBatch = ref('')
const manualOpen = ref(false)
const loteInfo = ref(null)
const transferAudit = ref(null)
const scannedBatch = ref('')

const companyAbbr = computed(() => store.operario?.company_abbr ?? 'PDM')
const quarantineWarehouse = computed(() => `Cuarentena MP - ${companyAbbr.value}`)
const approvedWarehouse = computed(() => `Materia Prima Aprobada - ${companyAbbr.value}`)
const availableInQuarantine = computed(() => {
  const rows = loteInfo.value?.stock_por_almacen ?? []
  const row = rows.find(entry => entry.warehouse === quarantineWarehouse.value)
  return Number(row?.qty ?? 0)
})
const isTransferable = computed(() => {
  if (!loteInfo.value?.lote?.batch_no) return false
  return availableInQuarantine.value > 0
})
const transferQty = computed(() => availableInQuarantine.value)

function getQtyForWarehouse(info, warehouse) {
  const rows = info?.stock_por_almacen ?? []
  const row = rows.find(entry => entry.warehouse === warehouse)
  return Number(row?.qty ?? 0)
}

function normalizeBatchInput(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return ''
  const parts = value.split('|').map(part => part.trim()).filter(Boolean)
  return parts.length >= 2 ? parts[1] : value
}

async function fetchBatch(batchInput, options = {}) {
  const batchNo = normalizeBatchInput(batchInput)
  if (!batchNo) return

  const suppressNoQuarantineError = options.suppressNoQuarantineError === true
  const preserveMessages = options.preserveMessages === true

  loading.value = true
  if (!preserveMessages) {
    errorMessage.value = ''
    successMessage.value = ''
  }
  if (!preserveMessages) {
    transferAudit.value = null
  }
  loteInfo.value = null
  scannedBatch.value = batchNo

  try {
    const result = await getInfoLote(batchNo)
    loteInfo.value = result

    const inQuarantine = (result.stock_por_almacen ?? []).some(row => row.warehouse === quarantineWarehouse.value && Number(row.qty) > 0)
    if (!inQuarantine && !suppressNoQuarantineError) {
      errorMessage.value = "Le lot n'est pas en quarantaine MP."
    }
  } catch (error) {
    errorMessage.value = error?.message_fr || 'Impossible de charger les informations du lot.'
  } finally {
    loading.value = false
    manualOpen.value = false
  }
}

async function transferBatch() {
  if (!isTransferable.value || transferring.value) return

  transferring.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const lote = loteInfo.value.lote
    const result = await trasladarLoteAprobado({
      itemCode: lote.item_code,
      batchNo: lote.batch_no,
      qtyToMove: transferQty.value,
      sourceWarehouse: quarantineWarehouse.value,
      targetWarehouse: approvedWarehouse.value,
    })

    transferAudit.value = result
    await fetchBatch(lote.batch_no, {
      suppressNoQuarantineError: true,
      preserveMessages: true,
    })
    successMessage.value = `Lot transfere via ${result.stock_entry}.`
  } catch (error) {
    // If the transfer response is lost (timeout/proxy hiccup), reconcile using live stock state.
    const lote = loteInfo.value?.lote
    let reconciledAsSuccess = false

    if (lote?.batch_no) {
      try {
        const refreshed = await getInfoLote(lote.batch_no)
        loteInfo.value = refreshed

        const quarantineQty = getQtyForWarehouse(refreshed, quarantineWarehouse.value)
        const approvedQty = getQtyForWarehouse(refreshed, approvedWarehouse.value)

        if (quarantineQty <= 0 && approvedQty > 0) {
          transferAudit.value = {
            stock_entry: null,
            batch_no: lote.batch_no,
          }
          successMessage.value = 'Transfert execute dans ERPNext. Reponse reseau non recue, etat reconcilie.'
          errorMessage.value = ''
          reconciledAsSuccess = true
        }
      } catch {
        // Keep the original error message below when reconciliation fails.
      }
    }

    if (!reconciledAsSuccess) {
      errorMessage.value = error?.message_fr || 'Le transfert du lot a echoue.'
    }
  } finally {
    transferring.value = false
  }
}

const { isScanning } = useScanner(fetchBatch, { disabled: transferring })
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <MoveRight :size="14" />
            Gestion quarantaine
          </div>
          <div>
            <div class="gcma-section-label">Transfert MP approuvee</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Sortie de quarantaine MP</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Scanner le lot, verifier sa presence en quarantaine MP puis lancer le transfert vers le stock approuve.
            </p>
          </div>
        </div>

        <div class="w-full max-w-md space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="gcma-stat">
              <div class="gcma-section-label">Source</div>
              <div class="mt-1 text-sm font-bold text-zinc-900">{{ quarantineWarehouse }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Cible</div>
              <div class="mt-1 text-sm font-bold text-zinc-900">{{ approvedWarehouse }}</div>
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
              Saisie lot
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="kiosk-panel rounded-md p-5 md:p-6">
      <div class="flex items-center gap-3">
        <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-blue-700">
          <RefreshCcw v-if="loading || isScanning" :size="22" class="animate-spin" />
          <Boxes v-else :size="22" />
        </div>
        <div>
          <div class="gcma-section-label">Scanner</div>
          <div class="text-lg font-bold text-zinc-900">{{ loading ? 'Lecture du lot...' : 'Pret pour scan HID ou saisie manuelle' }}</div>
        </div>
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

    <EmptyState v-if="!loteInfo && !loading"
                :icon="Boxes"
                title="Aucun lot scanne"
                message="Scanner un QR lot ou saisir un batch_no pour verifier la quarantaine." />

    <div v-else-if="loteInfo" class="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Lot detecte</div>
          <h2 class="mt-1 text-2xl font-black text-zinc-900">{{ loteInfo.lote.item_name }}</h2>
          <p class="mt-2 text-sm text-zinc-500">{{ loteInfo.lote.item_code }} · {{ loteInfo.lote.batch_no }}</p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="gcma-stat">
            <div class="gcma-section-label">Stock en quarantaine</div>
            <div class="mt-1 text-2xl font-black text-zinc-900">{{ availableInQuarantine }}</div>
          </div>
          <div class="gcma-stat">
            <div class="gcma-section-label">A transferer</div>
            <div class="mt-1 text-2xl font-black text-zinc-900">{{ transferQty }}</div>
          </div>
        </div>

        <div class="space-y-3">
          <div v-for="row in loteInfo.stock_por_almacen" :key="row.warehouse" class="gcma-data-row p-4 flex items-center justify-between gap-4 text-sm">
            <div>
              <div class="gcma-section-label">Emplacement</div>
              <div class="mt-1 font-semibold text-zinc-900">{{ row.warehouse }}</div>
            </div>
            <div class="text-lg font-black text-zinc-900">{{ row.qty }}</div>
          </div>
        </div>
      </div>

      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Action</div>
              <div class="mt-1 text-lg font-bold text-zinc-900">Transfert vers stock approuve</div>
          <p class="mt-2 text-sm text-zinc-500">Le flux de sprint 5 deplace la quantite disponible depuis la quarantaine MP vers l'entrepot approuve.</p>
        </div>

        <button @click="transferBatch"
                :disabled="!isTransferable || transferring"
                class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-blue-700 disabled:opacity-40 transition">
              {{ transferring ? 'Transfert en cours...' : 'Transferer vers MP approuvee' }}
        </button>

        <div v-if="transferAudit" class="gcma-data-row p-4 text-sm text-zinc-600">
          <div><span class="text-zinc-400">Stock Entry:</span> {{ transferAudit.stock_entry }}</div>
          <div class="mt-1"><span class="text-zinc-400">Lot:</span> {{ transferAudit.batch_no }}</div>
        </div>
      </div>
    </div>

    <ManualInputModal v-model="manualBatch"
                      :open="manualOpen"
                      title="Saisir un lot"
                      description="Entrer un batch_no ou scanner un QR complet item|lot."
                      placeholder="LOT-2026-0001"
                      :min-length="4"
                      @close="manualOpen = false"
                      @submit="fetchBatch" />
  </KioskLayout>
</template>
