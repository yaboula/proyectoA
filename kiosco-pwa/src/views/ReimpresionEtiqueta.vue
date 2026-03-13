<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Printer,
  QrCode,
  RefreshCcw,
  ScanLine,
  Tag,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import ManualInputModal from '../components/ManualInputModal.vue'
import { useOperarioStore } from '../stores/operario'
import { useScanner } from '../composables/useScanner'
import { getLoteParaImpresion } from '../api/kiosco'
import { printSingleKioscoLabel } from '../utils/printer'

const router = useRouter()
const store = useOperarioStore()

const loading = ref(false)
const printing = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const manualBatch = ref('')
const manualOpen = ref(false)
const labelPayload = ref(null)
const scannedBatch = ref('')

const operatorName = computed(() => store.operario?.full_name || store.operario?.badge_id || 'Operateur kiosque')
const qrPayload = computed(() => {
  const etiqueta = labelPayload.value?.etiqueta
  return etiqueta ? `${etiqueta.item_code}|${etiqueta.batch_no}` : ''
})

function normalizeBatchInput(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return ''
  const parts = value.split('|').map(part => part.trim()).filter(Boolean)
  return parts.length >= 2 ? parts[1] : value
}

function getPrintErrorMessage(error) {
  const message = String(error?.message ?? '')

  if (message.startsWith('PRINT_HTTP_')) {
    const status = message.replace('PRINT_HTTP_', '')
    return `Bridge Zebra indisponible (HTTP ${status}). Verifier le service local.`
  }

  if (message.includes('AbortError')) {
    return "Delai depasse vers le bridge Zebra. Verifier le service d'impression local."
  }

  if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
    return "Bridge Zebra indisponible. Verifier le service d'impression local (localhost:9000)."
  }

  return "L'impression de l'etiquette a echoue."
}

async function fetchLabel(batchInput) {
  const batchNo = normalizeBatchInput(batchInput)
  if (!batchNo) return

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  labelPayload.value = null
  scannedBatch.value = batchNo

  try {
    labelPayload.value = await getLoteParaImpresion(batchNo)
  } catch (error) {
    errorMessage.value = error?.message_fr || "Impossible de preparer l'etiquette."
  } finally {
    loading.value = false
    manualOpen.value = false
  }
}

async function printLabel() {
  if (!labelPayload.value || printing.value) return

  printing.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const lote = labelPayload.value.etiqueta
    await printSingleKioscoLabel({
      item_code: lote.item_code,
      item_name: lote.item_name,
      batch_no: lote.batch_no,
      expiry_date: lote.expiry_date,
      qr_payload: qrPayload.value,
    })
    successMessage.value = `Etiquette reimprimee pour ${lote.batch_no}.`
  } catch (error) {
    errorMessage.value = getPrintErrorMessage(error)
  } finally {
    printing.value = false
  }
}

const { isScanning } = useScanner(fetchLabel, { disabled: printing })
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <Printer :size="14" />
            Re-etiquetage
          </div>
          <div>
            <div class="gcma-section-label">Impression Zebra</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Re-impression etiquette lot</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Scanner un lot existant, verifier ses metadonnees puis relancer une impression locale pour l'etiquette magasin.
            </p>
          </div>
        </div>

        <div class="w-full max-w-md space-y-3">
          <div class="gcma-stat">
            <div class="gcma-section-label">Operateur</div>
            <div class="mt-1 text-sm font-bold text-zinc-900">{{ operatorName }}</div>
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
          <QrCode v-else :size="22" />
        </div>
        <div>
          <div class="gcma-section-label">Lecture</div>
          <div class="text-lg font-bold text-zinc-900">{{ loading ? 'Preparation etiquette...' : 'Scanner HID ou saisir un batch_no' }}</div>
          <div v-if="scannedBatch" class="mt-1 text-sm text-zinc-500">Dernier lot: {{ scannedBatch }}</div>
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

    <EmptyState v-if="!labelPayload && !loading"
                :icon="Tag"
                title="Aucune etiquette chargee"
                message="Scanner un lot pour reconstituer le contenu Zebra et reimprimer." />

    <div v-else-if="labelPayload" class="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Donnees lot</div>
          <h2 class="mt-1 text-2xl font-black text-zinc-900">{{ labelPayload.etiqueta.item_name }}</h2>
          <p class="mt-2 text-sm text-zinc-500">{{ labelPayload.etiqueta.item_code }} · {{ labelPayload.etiqueta.batch_no }}</p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="gcma-stat">
            <div class="gcma-section-label">Batch</div>
            <div class="mt-1 text-sm font-bold text-zinc-900">{{ labelPayload.etiqueta.batch_no }}</div>
          </div>
          <div class="gcma-stat">
            <div class="gcma-section-label">Expiration</div>
            <div class="mt-1 text-sm font-bold text-zinc-900">{{ labelPayload.etiqueta.expiry_date || '-' }}</div>
          </div>
        </div>

        <div class="space-y-3">
          <div class="gcma-data-row p-4 text-sm text-zinc-600">
            <div><span class="text-zinc-400">Article:</span> {{ labelPayload.etiqueta.item_code }}</div>
            <div class="mt-1"><span class="text-zinc-400">Nom:</span> {{ labelPayload.etiqueta.item_name }}</div>
            <div class="mt-1"><span class="text-zinc-400">QR payload:</span> {{ qrPayload }}</div>
          </div>
        </div>
      </div>

      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Action</div>
          <div class="mt-1 text-lg font-bold text-zinc-900">Re-imprimer etiquette</div>
          <p class="mt-2 text-sm text-zinc-500">Utilise le bridge Zebra local configure sur le kiosque. L'etiquette contient les memes informations que la reception.</p>
        </div>

        <button @click="printLabel"
                :disabled="printing"
                class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-blue-700 disabled:opacity-40 transition">
          {{ printing ? 'Impression en cours...' : 'Imprimer etiquette' }}
        </button>
      </div>
    </div>

    <ManualInputModal v-model="manualBatch"
                      :open="manualOpen"
                      title="Saisir un lot"
                      description="Entrer un batch_no ou scanner un QR complet item|lot."
                      placeholder="LOT-2026-0001"
                      :min-length="4"
                      @close="manualOpen = false"
                      @submit="fetchLabel" />
  </KioskLayout>
</template>
