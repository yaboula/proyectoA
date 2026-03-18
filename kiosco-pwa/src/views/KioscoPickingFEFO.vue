<script setup>
import { computed, ref } from 'vue'
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  Loader2,
  PackageSearch,
  ScanLine,
  ShieldAlert,
  Siren,
  TriangleAlert,
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import FullScreenOverlay from '../components/FullScreenOverlay.vue'
import { getPickList, validarScanFefo } from '../api/kiosco'

const router = useRouter()

// ── Estado de la sesión de picking ────────────────────────────────────────────
const salesOrderInput = ref('')
const pickList = ref(null)        // respuesta de get_pick_list
const loadingList = ref(false)
const listError = ref('')

// Item activo en picking (index dentro de pickList.items)
const activeItemIndex = ref(0)

// Acumulador por item: { [item_code]: qty_escaneada }
const qtyAcumulada = ref({})

// ── Estado del scan ────────────────────────────────────────────────────────────
const batchScanned = ref('')
const scanning = ref(false)
const scanError = ref('')
const lastScanOk = ref(null)

// ── Overlay de error bloqueante ────────────────────────────────────────────────
const fefoOverlay = ref(false)
const fefoOverlayMessage = ref('')

// ── Computed ───────────────────────────────────────────────────────────────────
const items = computed(() => pickList.value?.items ?? [])
const activeItem = computed(() => items.value[activeItemIndex.value] ?? null)

const qtyEscaneadaItem = computed(() => {
  if (!activeItem.value) return 0
  return qtyAcumulada.value[activeItem.value.item_code] ?? 0
})

const pickingCompleto = computed(() => {
  if (!items.value.length) return false
  return items.value.every(item => {
    const done = qtyAcumulada.value[item.item_code] ?? 0
    return done >= item.qty_pendiente
  })
})

const canScan = computed(() =>
  Boolean(activeItem.value)
  && batchScanned.value.trim().length > 0
  && !scanning.value
  && !pickingCompleto.value,
)

// ── Sonidos Poka-Yoke ──────────────────────────────────────────────────────────
function playErrorBuzz() {
  const audio = new Audio(
    'data:audio/wav;base64,UklGRlQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YTAAAACAgoWEhYSDg4KCgYGBgoKDg4SFhYSEg4OCgoGBgYKCgoODhIWFhISDg4KCgYGBgoKDg4SFhYSEg4OCgoGBgYKCgoODhIWFhIQ=',
  )
  audio.volume = 0.9
  audio.play().catch(() => {})
}

function playSuccessBeep() {
  const audio = new Audio(
    'data:audio/wav;base64,UklGRkQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSAAAAB/f39/gICAf39/f4CAgH9/f39/gICAf39/f4CAgH9/f39/gICAf39/f4CAgA==',
  )
  audio.volume = 0.7
  audio.play().catch(() => {})
}

// ── Acciones ───────────────────────────────────────────────────────────────────
async function onLoadPickList() {
  const so = salesOrderInput.value.trim()
  if (!so) return

  loadingList.value = true
  listError.value = ''
  pickList.value = null
  qtyAcumulada.value = {}
  activeItemIndex.value = 0

  try {
    pickList.value = await getPickList(so)
  } catch (error) {
    listError.value = error?.message || error?.message_fr || 'Impossible de charger la liste de picking.'
  } finally {
    loadingList.value = false
  }
}

function selectItem(index) {
  activeItemIndex.value = index
  batchScanned.value = ''
  scanError.value = ''
  lastScanOk.value = null
}

async function onValidateScan() {
  if (!canScan.value) return

  scanning.value = true
  scanError.value = ''
  lastScanOk.value = null

  const item = activeItem.value
  const acumulado = qtyAcumulada.value[item.item_code] ?? 0

  try {
    const result = await validarScanFefo({
      sales_order: pickList.value.sales_order,
      item_code: item.item_code,
      batch_scanned: batchScanned.value.trim(),
      qty_ya_escaneada: acumulado,
    })

    // Actualizar acumulador
    qtyAcumulada.value = {
      ...qtyAcumulada.value,
      [item.item_code]: result.qty_escaneada_total,
    }

    lastScanOk.value = result
    playSuccessBeep()
    batchScanned.value = ''

    // Si el item quedó completo, avanzar al siguiente pendiente
    if (result.cierre_parcial) {
      const siguiente = items.value.findIndex((it, i) => {
        const done = (qtyAcumulada.value[it.item_code] ?? 0)
        return i > activeItemIndex.value && done < it.qty_pendiente
      })
      if (siguiente !== -1) activeItemIndex.value = siguiente
    }
  } catch (error) {
    const msg = error?.message || error?.message_fr || 'Erreur FEFO: scan refuse.'
    scanError.value = msg
    fefoOverlayMessage.value = msg
    fefoOverlay.value = true
    playErrorBuzz()
    batchScanned.value = ''
  } finally {
    scanning.value = false
  }
}

function onDismissOverlay() {
  fefoOverlay.value = false
}

function resetSession() {
  salesOrderInput.value = ''
  pickList.value = null
  qtyAcumulada.value = {}
  activeItemIndex.value = 0
  batchScanned.value = ''
  scanError.value = ''
  lastScanOk.value = null
}
</script>

<template>
  <KioskLayout maxWidth="6xl">
    <!-- FullScreen overlay FEFO bloqueante -->
    <FullScreenOverlay
      v-if="fefoOverlay"
      variant="error"
      title="Blocage FEFO"
      :subtitle="fefoOverlayMessage"
      hint="Appuyez pour fermer"
      :clickable="true"
      @click="onDismissOverlay"
    />

    <!-- Header -->
    <div class="kiosk-panel p-5 md:p-6">
      <div class="gcma-toolbar">
        <div class="flex items-start gap-4">
          <button
            type="button"
            class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md"
            @click="router.back()"
          >
            <ArrowLeft :size="20" class="text-zinc-600" />
          </button>
          <div>
            <div class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-red-700">
              <ShieldAlert :size="13" />
              Poka-Yoke FEFO
            </div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">
              Kiosco de Picking
            </h1>
            <p class="mt-1 text-sm text-zinc-500">
              Chaque scan validé côté serveur selon la règle FEFO stricte.
            </p>
          </div>
        </div>

        <!-- Stat: progreso global -->
        <div v-if="pickList" class="gcma-stat min-w-[120px] text-center">
          <div class="text-2xl font-black text-zinc-900">
            {{ items.filter(it => (qtyAcumulada[it.item_code] ?? 0) >= it.qty_pendiente).length }}
            <span class="text-zinc-400">/{{ items.length }}</span>
          </div>
          <div class="gcma-section-label mt-1">articles finis</div>
        </div>
      </div>
    </div>

    <!-- Paso 1: Entrada del Sales Order -->
    <div v-if="!pickList" class="kiosk-panel p-5 md:p-6 space-y-4">
      <div class="gcma-section-label">Étape 1 — Scanner le bon de commande</div>
      <div class="flex gap-3">
        <input
          v-model="salesOrderInput"
          type="text"
          autocomplete="off"
          class="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          placeholder="SO-00998"
          @keydown.enter.prevent="onLoadPickList"
        />
        <button
          type="button"
          :disabled="!salesOrderInput.trim() || loadingList"
          class="h-16 rounded-md bg-blue-600 px-6 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center gap-2 shrink-0"
          @click="onLoadPickList"
        >
          <Loader2 v-if="loadingList" :size="18" class="animate-spin" />
          <ClipboardList v-else :size="18" />
          {{ loadingList ? 'Chargement...' : 'Charger' }}
        </button>
      </div>

      <div
        v-if="listError"
        class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex items-start gap-2"
      >
        <TriangleAlert :size="16" class="mt-0.5 shrink-0" />
        {{ listError }}
      </div>
    </div>

    <!-- Paso 2: Pick List cargada -->
    <template v-if="pickList">
      <!-- Lista de items -->
      <div class="kiosk-panel p-5 md:p-6 space-y-3">
        <div class="gcma-toolbar">
          <div class="gcma-section-label">Articles à préparer — {{ pickList.customer }}</div>
          <button
            type="button"
            class="text-xs font-semibold text-zinc-500 underline underline-offset-2"
            @click="resetSession"
          >
            Nouveau bon
          </button>
        </div>

        <EmptyState
          v-if="!items.length"
          :icon="PackageSearch"
          title="Bon de commande complet"
          message="Tous les articles ont déjà été livrés."
        />

        <div
          v-for="(item, index) in items"
          :key="item.item_code"
          class="gcma-data-row cursor-pointer p-4 transition-all"
          :class="{
            'border-blue-500 ring-2 ring-blue-500/30': index === activeItemIndex,
            'opacity-50': (qtyAcumulada[item.item_code] ?? 0) >= item.qty_pendiente,
          }"
          @click="selectItem(index)"
        >
          <div class="flex items-center justify-between gap-4">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <CheckCircle2
                  v-if="(qtyAcumulada[item.item_code] ?? 0) >= item.qty_pendiente"
                  :size="16"
                  class="shrink-0 text-green-600"
                />
                <span class="font-mono text-sm font-bold text-zinc-700">{{ item.item_code }}</span>
              </div>
              <div class="mt-0.5 truncate text-sm text-zinc-500">{{ item.item_name }}</div>
              <div v-if="item.lote_fefo_sugerido" class="mt-1 text-xs text-zinc-400">
                Lot FEFO: <span class="font-mono font-semibold text-zinc-600">{{ item.lote_fefo_sugerido }}</span>
                <span v-if="item.lote_expiry" class="ml-2">· Exp: {{ item.lote_expiry }}</span>
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-xl font-black text-zinc-900">
                {{ qtyAcumulada[item.item_code] ?? 0 }}
                <span class="text-sm font-normal text-zinc-400">/ {{ item.qty_pendiente }}</span>
              </div>
              <div class="text-xs text-zinc-400">{{ item.warehouse || '—' }}</div>
            </div>
          </div>

          <!-- Barra de progreso -->
          <div class="mt-3 h-2 w-full overflow-hidden rounded-full bg-zinc-200">
            <div
              class="h-2 rounded-full bg-blue-600 transition-all"
              :class="{ 'bg-green-600': (qtyAcumulada[item.item_code] ?? 0) >= item.qty_pendiente }"
              :style="{
                width: `${Math.min(100, (((qtyAcumulada[item.item_code] ?? 0) / item.qty_pendiente) * 100))}%`
              }"
            />
          </div>
        </div>
      </div>

      <!-- Paso 3: Scan del batch (item activo) -->
      <div v-if="activeItem && !pickingCompleto" class="kiosk-panel p-5 md:p-6 space-y-4">
        <div class="gcma-section-label">
          Scanner le lot — <span class="font-mono text-zinc-600">{{ activeItem.item_code }}</span>
        </div>

        <div class="flex gap-3">
          <input
            v-model="batchScanned"
            type="text"
            autocomplete="off"
            class="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
            :placeholder="activeItem.lote_fefo_sugerido || 'LOTE-XXXX'"
            @keydown.enter.prevent="onValidateScan"
          />
          <button
            type="button"
            :disabled="!canScan"
            class="h-16 rounded-md bg-blue-600 px-6 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center gap-2 shrink-0"
            @click="onValidateScan"
          >
            <Loader2 v-if="scanning" :size="18" class="animate-spin" />
            <ScanLine v-else :size="18" />
            {{ scanning ? 'Validation...' : 'Valider' }}
          </button>
        </div>

        <!-- Feedback éxito inline -->
        <div
          v-if="lastScanOk && !scanError"
          class="rounded-md border border-green-200 bg-green-50 p-4 text-green-700 flex items-start gap-3"
        >
          <CheckCircle2 :size="20" class="mt-0.5 shrink-0" />
          <div>
            <div class="font-black uppercase tracking-[0.12em] text-sm">Scan accepté</div>
            <p class="mt-1 text-sm">
              Lot <span class="font-mono font-bold">{{ lastScanOk.batch_validado }}</span> ·
              {{ lastScanOk.qty_escaneada_total }}/{{ lastScanOk.qty_pendiente }} préparés ·
              <span v-if="lastScanOk.qty_restante > 0">{{ lastScanOk.qty_restante }} restants</span>
              <span v-else class="font-bold">Article complet ✓</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Picking completado -->
      <div
        v-if="pickingCompleto"
        class="kiosk-panel p-6 text-center space-y-4"
      >
        <CheckCircle2 :size="48" class="mx-auto text-green-600" />
        <div class="text-xl font-black text-zinc-900">Préparation terminée !</div>
        <p class="text-sm text-zinc-500">
          Tous les articles du bon <span class="font-mono font-bold">{{ pickList.sales_order }}</span> ont été préparés.
        </p>
        <button
          type="button"
          class="h-16 w-full rounded-md bg-blue-600 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 transition"
          @click="resetSession"
        >
          Nouveau picking
        </button>
      </div>
    </template>

    <!-- Bloque informativo contrato API -->
    <div class="kiosk-panel-soft rounded-md p-5 text-sm text-zinc-600 flex items-start gap-3">
      <Siren :size="16" class="mt-0.5 shrink-0 text-red-500" />
      <p>
        Toute violation FEFO déclenche un overlay rouge plein écran avec audio.
        Les quantités sont contrôlées côté serveur à chaque scan.
      </p>
    </div>
  </KioskLayout>
</template>
