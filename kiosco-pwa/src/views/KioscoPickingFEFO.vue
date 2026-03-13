<script setup>
import { computed, ref } from 'vue'
import {
  AlertTriangle,
  CheckCircle2,
  PackageSearch,
  ScanLine,
  ShieldAlert,
  Siren,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import { validarScanFefo } from '../api/kiosco'

const salesOrder = ref('')
const itemCode = ref('')
const batchScanned = ref('')

const scanning = ref(false)
const lastOk = ref(null)
const errorMessage = ref('')

const isReady = computed(() => {
  return (
    salesOrder.value.trim().length > 0
    && itemCode.value.trim().length > 0
    && batchScanned.value.trim().length > 0
  )
})

function playErrorBuzz() {
  const audio = new Audio(
    'data:audio/wav;base64,UklGRlQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YTAAAACAgoWEhYSDg4KCgYGBgoKDg4SFhYSEg4OCgoGBgYKCgoODhIWFhISDg4KCgYGBgoKDg4SFhYSEg4OCgoGBgYKCgoODhIWFhIQ='
  )
  audio.volume = 0.9
  audio.play().catch(() => {})
}

function playSuccessBeep() {
  const audio = new Audio(
    'data:audio/wav;base64,UklGRkQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSAAAAB/f39/gICAf39/f4CAgH9/f39/gICAf39/f4CAgH9/f39/gICAf39/f4CAgA=='
  )
  audio.volume = 0.7
  audio.play().catch(() => {})
}

async function onValidateScan() {
  if (!isReady.value || scanning.value) return

  scanning.value = true
  errorMessage.value = ''
  lastOk.value = null

  try {
    const result = await validarScanFefo({
      sales_order: salesOrder.value.trim(),
      item_code: itemCode.value.trim(),
      batch_scanned: batchScanned.value.trim(),
    })

    lastOk.value = result
    playSuccessBeep()
    batchScanned.value = ''
  } catch (error) {
    errorMessage.value =
      error?.message
      || error?.message_fr
      || 'Erreur FEFO: scan refuse par le backend.'
    playErrorBuzz()
  } finally {
    scanning.value = false
  }
}
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-red-700">
            <ShieldAlert :size="14" />
            Poka-Yoke FEFO
          </div>
          <div>
            <div class="gcma-section-label">Kiosco de picking</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">
              Validation de lot en expedicion
            </h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Chaque scan est valide cote serveur. Si un lot plus ancien existe, le backend bloque et le kiosk affiche une alerte rouge immediatement.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-5">
      <div class="grid gap-4 md:grid-cols-3">
        <label class="space-y-2">
          <span class="gcma-section-label">Sales Order</span>
          <input
            v-model="salesOrder"
            type="text"
            autocomplete="off"
            class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
            placeholder="SO-00998"
          />
        </label>

        <label class="space-y-2">
          <span class="gcma-section-label">Item Code</span>
          <input
            v-model="itemCode"
            type="text"
            autocomplete="off"
            class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
            placeholder="PINT-EPOXI-01"
          />
        </label>

        <label class="space-y-2">
          <span class="gcma-section-label">Batch scanne</span>
          <input
            v-model="batchScanned"
            type="text"
            autocomplete="off"
            class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
            placeholder="LOTE-2025-08"
            @keydown.enter.prevent="onValidateScan"
          />
        </label>
      </div>

      <button
        type="button"
        :disabled="!isReady || scanning"
        @click="onValidateScan"
        class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
      >
        <ScanLine :size="18" />
        {{ scanning ? 'Validation en cours...' : 'Valider scan FEFO' }}
      </button>
    </div>

    <div
      v-if="errorMessage"
      class="rounded-md border border-red-200 bg-red-50 p-6 text-red-700"
    >
      <div class="flex items-start gap-3">
        <Siren :size="22" class="mt-0.5 shrink-0" />
        <div>
          <div class="text-lg font-black uppercase tracking-[0.14em]">Blocage FEFO</div>
          <p class="mt-2 text-base font-semibold leading-7">{{ errorMessage }}</p>
        </div>
      </div>
    </div>

    <div
      v-if="lastOk"
      class="rounded-md border border-green-200 bg-green-50 p-6 text-green-700"
    >
      <div class="flex items-start gap-3">
        <CheckCircle2 :size="22" class="mt-0.5 shrink-0" />
        <div>
          <div class="text-lg font-black uppercase tracking-[0.14em]">Scan accepte</div>
          <p class="mt-2 text-base font-semibold leading-7">
            Statut: {{ lastOk.status }} · Quantite restante: {{ lastOk.qty_restante_pedido }}
          </p>
        </div>
      </div>
    </div>

    <div class="kiosk-panel-soft rounded-md p-5 text-sm text-zinc-600">
      <div class="flex items-start gap-3">
        <PackageSearch :size="18" class="mt-0.5 shrink-0 text-zinc-500" />
        <div>
          <p class="font-semibold text-zinc-800">Payload contrato API (2.1)</p>
          <p class="mt-1">sales_order, item_code, batch_scanned</p>
        </div>
      </div>
      <div class="mt-3 flex items-start gap-3">
        <AlertTriangle :size="18" class="mt-0.5 shrink-0 text-red-500" />
        <p>
          Si backend detecta un lote mas antiguo con stock, la vista mantiene alerta roja bloqueante y reproduce Audio() de error.
        </p>
      </div>
    </div>
  </KioskLayout>
</template>
