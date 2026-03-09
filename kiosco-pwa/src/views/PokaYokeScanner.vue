<script setup>
/**
 * PokaYokeScanner — Validation des matériaux par scan QR (EP3).
 *
 * Design System: thème industriel premium MES.
 * UX sémaphorique: emerald=validé, rose=erreur STOP avec shake.
 * Icônes: lucide-vue-next. Boutons ≥ h-16. rounded-md max.
 */
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas, validarMaterial, reportarConsumo } from '../api/kiosco'
import {
  ArrowLeft,
  Loader2,
  CircleAlert,
  CircleCheckBig,
  TriangleAlert,
  Keyboard,
  ChevronRight,
  X,
  ScanBarcode,
  Check,
  Beaker,
  Scale,
  PackageCheck,
} from 'lucide-vue-next'

const props = defineProps({ workOrder: String })
const router = useRouter()
const store = useOperarioStore()

// ── Tarea data ──
const tarea = ref(null)
const materials = ref([])
const loadingTarea = ref(true)
const loadError = ref(null)

// ── Scanner state ──
const scanState = ref('ready') // ready | scanning | loading | success | error
const lastResult = ref(null)
const recentlyValidated = ref(-1)

// ── Manual entry ──
const manualOpen = ref(false)
const manualInput = ref('')
const manualInputRef = ref(null)

// ── Finalization / EP4 state ──
const finalizePhase = ref('idle') // idle | asking | extras | submitting | success | error
const extras = ref([])           // [{item_name, qty_extra}]
const finalizeResult = ref(null)
const finalizeError = ref('')

// ── Computed ──
const allValidated = computed(() =>
  materials.value.length > 0 && materials.value.every(m => m.status === 'validated')
)
const validatedCount = computed(() =>
  materials.value.filter(m => m.status === 'validated').length
)

// ── Auto-focus manual input ──
watch(manualOpen, (open) => {
  if (open) nextTick(() => manualInputRef.value?.focus())
})

// ── Load tarea from EP2 ──
async function loadTarea() {
  loadingTarea.value = true
  loadError.value = null
  try {
    const data = await getTareas(
      store.operario.company,
      store.operario.default_warehouse
    )
    const found = (data.tareas ?? []).find(t => t.work_order === props.workOrder)
    if (found) {
      tarea.value = found
      materials.value = (found.materiales ?? []).map(m => ({
        ...m,
        status: 'pending',
        scanResult: null,
      }))
    } else {
      loadError.value = "Ordre de fabrication introuvable."
    }
  } catch (err) {
    loadError.value = err?.message_fr ?? 'Erreur de chargement.'
  } finally {
    loadingTarea.value = false
  }
}

// ── USB HID Scanner (same pattern as LoginQR) ──
const SCAN_GAP_MS = 80
let buffer = ''
let lastKeyTime = 0

function onKeyDown(e) {
  if (manualOpen.value) return
  if (scanState.value === 'error') return

  const now = Date.now()
  if (now - lastKeyTime > SCAN_GAP_MS && buffer.length > 0) buffer = ''
  lastKeyTime = now

  if (e.key === 'Enter') {
    e.preventDefault()
    const qr = buffer.trim()
    buffer = ''
    if (qr.length >= 3) handleScan(qr)
    return
  }

  if (e.key.length === 1) {
    buffer += e.key
    if (scanState.value === 'ready' || scanState.value === 'success') {
      scanState.value = 'scanning'
    }
  }
}

// ── Validate scanned material via EP3 ──
async function handleScan(qrData) {
  scanState.value = 'loading'
  lastResult.value = null

  try {
    const data = await validarMaterial(props.workOrder, qrData)
    lastResult.value = data

    if (data.valido) {
      scanState.value = 'success'

      const idx = materials.value.findIndex(
        m => m.item_name === data.item_name && m.status !== 'validated'
      )
      if (idx >= 0) {
        materials.value[idx].status = 'validated'
        materials.value[idx].scanResult = data
        recentlyValidated.value = idx
        setTimeout(() => { recentlyValidated.value = -1 }, 1500)
      }

      setTimeout(() => {
        if (scanState.value === 'success') scanState.value = 'ready'
      }, 2500)
    } else {
      scanState.value = 'error'
    }
  } catch (err) {
    scanState.value = 'error'
    lastResult.value = {
      message_fr: err?.message_fr ?? 'Erreur de communication avec le serveur.',
    }
  }
}

function dismissError() {
  scanState.value = 'ready'
  lastResult.value = null
}

// ── Manual entry ──
function openManual() {
  manualOpen.value = true
  manualInput.value = ''
}
function closeManual() { manualOpen.value = false }
function submitManual() {
  const val = manualInput.value.trim()
  closeManual()
  if (val.length >= 3) handleScan(val)
}

// ── Navigation ──
function goBack() { router.push({ name: 'tareas' }) }

function finalizeMix() {
  finalizePhase.value = 'asking'
}

function confirmStandard() {
  callEP4([])
}

function showExtras() {
  extras.value = materials.value.map(m => ({
    item_name: m.item_name,
    uom: m.uom,
    qty_extra: 0,
  }))
  finalizePhase.value = 'extras'
}

function submitExtras() {
  const withExtra = extras.value.filter(e => e.qty_extra > 0)
  callEP4(withExtra)
}

async function callEP4(extrasList) {
  finalizePhase.value = 'submitting'
  finalizeError.value = ''
  try {
    const data = await reportarConsumo(props.workOrder, extrasList)
    if (data.success) {
      finalizeResult.value = data
      finalizePhase.value = 'success'
      setTimeout(() => router.push({ name: 'tareas' }), 3000)
    } else {
      finalizeError.value = data.message_fr ?? 'Erreur lors de l\'enregistrement.'
      finalizePhase.value = 'error'
    }
  } catch (err) {
    finalizeError.value = err?.message_fr ?? 'Erreur de communication avec le serveur.'
    finalizePhase.value = 'error'
  }
}

function retryFinalize() {
  finalizePhase.value = 'asking'
}

// ── Lifecycle ──
onMounted(() => {
  loadTarea()
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <!-- ═══ ERROR OVERLAY — full screen rose + shake, tap to dismiss ═══ -->
  <Teleport to="body">
    <div v-if="scanState === 'error'"
         @click="dismissError"
         class="fixed inset-0 z-50 flex flex-col items-center justify-center px-8
                select-none cursor-pointer animate-shake"
         :class="lastResult?.alerta_nivel === 'CRITICO'
           ? 'bg-rose-700'
           : 'bg-rose-600'">
      <TriangleAlert :size="80" :stroke-width="2" class="text-white mb-6" />
      <p class="text-white text-3xl font-black text-center leading-relaxed max-w-lg">
        {{ lastResult?.message_fr ?? 'Erreur inconnue' }}
      </p>
      <p class="mt-10 text-rose-200/70 text-base font-medium tracking-wide">
        Appuyez pour fermer
      </p>
    </div>
  </Teleport>

  <!-- ═══ MANUAL INPUT MODAL — shadcn Dialog style ═══ -->
  <Teleport to="body">
    <div v-if="manualOpen"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-5">
      <div class="w-full max-w-md bg-slate-800 border border-slate-700 rounded-md p-6
                  shadow-2xl animate-fade-in">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold text-slate-100">Saisie Manuelle</h2>
          <button @click="closeManual"
                  class="h-10 w-10 flex items-center justify-center rounded-md
                         text-slate-500 hover:text-slate-300 active:bg-slate-700 transition">
            <X :size="20" />
          </button>
        </div>
        <p class="text-slate-400 mb-5 text-sm">
          Entrez le code QR du matériau (format : CODE|LOT) :
        </p>
        <input ref="manualInputRef"
               v-model="manualInput"
               type="text"
               autocomplete="off"
               class="w-full text-xl font-mono bg-slate-900 border border-slate-600 rounded-md
                      px-4 py-4 text-slate-100 placeholder-slate-600
                      focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/30"
               placeholder="CODE|LOT"
               @keydown.enter="submitManual" />
        <div class="mt-5 flex gap-3">
          <button @click="closeManual"
                  class="flex-1 h-14 rounded-md bg-slate-700 border border-slate-600
                         text-slate-300 text-base font-semibold
                         active:bg-slate-600 transition">
            Annuler
          </button>
          <button @click="submitManual"
                  :disabled="manualInput.trim().length < 3"
                  class="flex-1 h-14 rounded-md bg-emerald-600 text-white text-base font-bold
                         flex items-center justify-center gap-2
                         active:bg-emerald-700 disabled:opacity-30 transition">
            Valider
            <ChevronRight :size="18" />
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ═══ EP4 — "Standard ou Extra ?" DIALOG ═══ -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'asking'"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-5">
      <div class="w-full max-w-md bg-slate-800 border border-slate-700 rounded-md p-6
                  shadow-2xl animate-fade-in">
        <div class="flex items-center gap-3 mb-5">
          <Scale :size="28" class="text-amber-400" />
          <h2 class="text-xl font-bold text-slate-100">Ajustement Consommation</h2>
        </div>
        <p class="text-slate-300 text-base mb-6 leading-relaxed">
          Le mélange est prêt. La consommation correspond-elle aux quantités standard ?
        </p>
        <div class="space-y-3">
          <button @click="confirmStandard"
                  class="w-full h-16 rounded-md bg-emerald-600 text-white text-lg font-bold
                         flex items-center justify-center gap-3
                         active:bg-emerald-700 transition">
            <Check :size="22" :stroke-width="3" />
            NON, consommation standard
          </button>
          <button @click="showExtras"
                  class="w-full h-16 rounded-md bg-amber-600 text-white text-lg font-bold
                         flex items-center justify-center gap-3
                         active:bg-amber-700 transition">
            <Scale :size="22" :stroke-width="2.5" />
            OUI, ajouter un extra
          </button>
        </div>
        <button @click="finalizePhase = 'idle'"
                class="w-full mt-4 h-12 rounded-md bg-slate-700 border border-slate-600
                       text-slate-400 text-sm font-semibold active:bg-slate-600 transition">
          Annuler
        </button>
      </div>
    </div>
  </Teleport>

  <!-- ═══ EP4 — EXTRAS INPUT FORM ═══ -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'extras'"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-5">
      <div class="w-full max-w-md bg-slate-800 border border-slate-700 rounded-md
                  shadow-2xl animate-fade-in max-h-[90dvh] flex flex-col">
        <div class="p-6 pb-3 flex items-center justify-between">
          <h2 class="text-xl font-bold text-slate-100">Quantités Extra</h2>
          <button @click="finalizePhase = 'asking'"
                  class="h-10 w-10 flex items-center justify-center rounded-md
                         text-slate-500 hover:text-slate-300 active:bg-slate-700 transition">
            <X :size="20" />
          </button>
        </div>
        <p class="px-6 text-slate-400 text-sm mb-4">
          Indiquez la quantité supplémentaire (Kg/L) pour chaque ingrédient :
        </p>
        <div class="flex-1 overflow-y-auto px-6 space-y-3 pb-4">
          <div v-for="(ex, i) in extras" :key="i"
               class="rounded-md bg-slate-900 border border-slate-700 p-4">
            <p class="text-base font-bold text-slate-200 mb-2 truncate">
              {{ ex.item_name }}
            </p>
            <div class="flex items-center gap-3">
              <span class="text-sm text-slate-500">Extra :</span>
              <input v-model.number="ex.qty_extra"
                     type="number" min="0" step="0.1"
                     class="flex-1 bg-slate-800 border border-slate-600 rounded-md
                            px-3 py-3 text-lg font-mono text-slate-100
                            focus:border-amber-500 focus:outline-none
                            focus:ring-1 focus:ring-amber-500/30"
                     placeholder="0" />
              <span class="text-sm text-slate-400 font-medium">{{ ex.uom }}</span>
            </div>
          </div>
        </div>
        <div class="p-6 pt-3 space-y-3 border-t border-slate-700">
          <button @click="submitExtras"
                  class="w-full h-16 rounded-md bg-emerald-600 text-white text-lg font-bold
                         flex items-center justify-center gap-3
                         active:bg-emerald-700 transition">
            <PackageCheck :size="22" :stroke-width="2.5" />
            Valider et Enregistrer
          </button>
          <button @click="finalizePhase = 'asking'"
                  class="w-full h-12 rounded-md bg-slate-700 border border-slate-600
                         text-slate-400 text-sm font-semibold active:bg-slate-600 transition">
            Retour
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ═══ EP4 — SUBMITTING OVERLAY ═══ -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'submitting'"
         class="fixed inset-0 z-50 bg-slate-900/95 flex flex-col items-center justify-center">
      <Loader2 :size="64" :stroke-width="2" class="text-emerald-400 animate-spin mb-6" />
      <p class="text-slate-300 text-xl font-bold">Enregistrement en cours…</p>
    </div>
  </Teleport>

  <!-- ═══ EP4 — SUCCESS OVERLAY — "LOT TERMINÉ" with 3s redirect ═══ -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'success'"
         class="fixed inset-0 z-50 bg-emerald-700 flex flex-col items-center justify-center
                px-8 animate-fade-in">
      <PackageCheck :size="80" :stroke-width="1.5" class="text-white mb-6" />
      <p class="text-white text-3xl font-black text-center mb-2">LOT TERMINÉ</p>
      <p class="text-emerald-100 text-xl font-semibold text-center leading-relaxed">
        Placer en zone de Quarantaine
      </p>
      <div v-if="finalizeResult?.alerta"
           class="mt-6 rounded-md bg-amber-900/60 border border-amber-500/50 px-5 py-3 max-w-sm">
        <p class="text-amber-200 text-sm font-bold text-center">
          <TriangleAlert :size="16" class="inline mr-1 -mt-0.5" />
          {{ finalizeResult.message_fr }}
        </p>
      </div>
      <p class="mt-10 text-emerald-200/60 text-sm font-medium tracking-wide">
        Redirection automatique…
      </p>
    </div>
  </Teleport>

  <!-- ═══ EP4 — ERROR OVERLAY with retry ═══ -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'error'"
         class="fixed inset-0 z-50 bg-rose-700 flex flex-col items-center justify-center px-8">
      <CircleAlert :size="80" :stroke-width="1.5" class="text-white mb-6" />
      <p class="text-white text-2xl font-black text-center mb-2">
        Erreur d'enregistrement
      </p>
      <p class="text-rose-100 text-base text-center leading-relaxed max-w-sm">
        {{ finalizeError }}
      </p>
      <button @click="retryFinalize"
              class="mt-8 h-16 px-10 rounded-md bg-white text-rose-700 text-lg font-black
                     active:bg-rose-100 transition">
        Réessayer
      </button>
      <button @click="finalizePhase = 'idle'"
              class="mt-3 text-rose-200/70 text-sm font-medium underline">
        Annuler
      </button>
    </div>
  </Teleport>

  <!-- ═══ MAIN LAYOUT ═══ -->
  <div class="min-h-dvh bg-slate-900 flex flex-col select-none">

    <!-- Header -->
    <header class="bg-slate-800/80 border-b border-slate-700/50 px-5 py-4
                    flex items-center gap-3">
      <button @click="goBack"
              class="shrink-0 h-12 w-12 rounded-md border border-slate-700 bg-slate-800
                     flex items-center justify-center text-slate-400
                     active:bg-slate-700 transition">
        <ArrowLeft :size="20" />
      </button>
      <div class="flex-1 min-w-0">
        <h1 class="text-lg font-bold text-slate-100 truncate">
          {{ tarea?.producto ?? workOrder }}
        </h1>
        <p class="text-xs font-mono text-slate-500 flex items-center gap-1">
          <Beaker :size="11" />
          {{ workOrder }}
        </p>
      </div>
      <div class="shrink-0 text-right">
        <p class="text-3xl font-black"
           :class="allValidated ? 'text-emerald-400' : 'text-slate-200'">
          {{ validatedCount }}/{{ materials.length }}
        </p>
        <p class="text-xs text-slate-500">validés</p>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loadingTarea" class="flex-1 flex items-center justify-center">
      <Loader2 :size="48" :stroke-width="2" class="text-slate-500 animate-spin" />
    </div>

    <!-- Load Error -->
    <div v-else-if="loadError"
         class="flex-1 flex flex-col items-center justify-center px-8 gap-5">
      <CircleAlert :size="56" :stroke-width="1.5" class="text-rose-500" />
      <p class="text-rose-400 text-lg font-bold text-center">{{ loadError }}</p>
      <button @click="goBack"
              class="h-14 px-8 rounded-md bg-slate-800 border border-slate-700
                     text-slate-200 text-base font-semibold flex items-center gap-2
                     active:bg-slate-700 transition">
        <ArrowLeft :size="18" />
        Retour aux ordres
      </button>
    </div>

    <!-- ═══ Main Content ═══ -->
    <template v-else>

      <!-- Materials checklist (scrollable) -->
      <section class="flex-1 overflow-y-auto px-4 pt-4 pb-3 space-y-2.5">
        <div v-for="(mat, i) in materials" :key="i"
             class="rounded-md p-4 border transition-all duration-500"
             :class="{
               'bg-emerald-900/40 border-emerald-500/70 scale-[1.01] shadow-lg shadow-emerald-500/20':
                 i === recentlyValidated,
               'bg-emerald-900/20 border-emerald-700/50':
                 mat.status === 'validated' && i !== recentlyValidated,
               'bg-slate-800 border-slate-700/60':
                 mat.status === 'pending',
             }">
          <div class="flex items-center gap-3.5">
            <!-- Status icon -->
            <div v-if="mat.status === 'validated'"
                 class="shrink-0 w-12 h-12 rounded-md bg-emerald-600 flex items-center justify-center">
              <CircleCheckBig :size="24" :stroke-width="2.5" class="text-white" />
            </div>
            <div v-else
                 class="shrink-0 w-12 h-12 rounded-md border-2 border-slate-600
                        flex items-center justify-center">
              <span class="text-slate-500 text-lg font-bold">{{ i + 1 }}</span>
            </div>

            <!-- Material info -->
            <div class="flex-1 min-w-0">
              <p class="text-lg font-bold truncate"
                 :class="mat.status === 'validated' ? 'text-emerald-300' : 'text-slate-200'">
                {{ mat.item_name }}
              </p>
              <p class="text-sm mt-0.5"
                 :class="mat.status === 'validated' ? 'text-emerald-500/70' : 'text-slate-500'">
                {{ mat.qty_requerida }} {{ mat.uom }}
                <template v-if="mat.scanResult?.batch_no">
                  · Lot {{ mat.scanResult.batch_no }}
                </template>
              </p>
            </div>

            <!-- Stock badge (pending only) -->
            <span v-if="mat.status === 'pending'"
                  class="shrink-0 rounded-md px-2.5 py-1 text-xs font-bold border"
                  :class="mat.suficiente
                    ? 'bg-emerald-900/30 text-emerald-400 border-emerald-700/50'
                    : 'bg-rose-900/30 text-rose-400 border-rose-700/50'">
              {{ mat.suficiente ? 'Stock OK' : 'Stock ✗' }}
            </span>
          </div>
        </div>
      </section>

      <!-- Bottom zone: scan status + actions (always visible) -->
      <section class="px-4 pb-5 pt-3 space-y-3 border-t border-slate-800">

        <!-- Scan status indicator -->
        <div v-if="!allValidated"
             class="rounded-md px-5 py-4 flex items-center justify-center gap-3
                    transition-all duration-300"
             :class="{
               'bg-slate-800 border border-slate-700/50':  scanState === 'ready',
               'bg-slate-800 border border-slate-600':     scanState === 'scanning',
               'bg-amber-900/40 border border-amber-700/50': scanState === 'loading',
               'bg-emerald-900/40 border border-emerald-700/50': scanState === 'success',
             }">
          <template v-if="scanState === 'ready'">
            <ScanBarcode :size="22" class="text-slate-400" />
            <p class="text-slate-400 text-base font-semibold">Scannez le prochain matériau</p>
          </template>
          <template v-else-if="scanState === 'scanning'">
            <Loader2 :size="20" class="text-slate-300 animate-spin" />
            <p class="text-slate-300 text-base font-semibold">Lecture du code…</p>
          </template>
          <template v-else-if="scanState === 'loading'">
            <Loader2 :size="20" class="text-amber-400 animate-spin" />
            <p class="text-amber-400 text-base font-semibold">Vérification en cours…</p>
          </template>
          <template v-else-if="scanState === 'success'">
            <CircleCheckBig :size="20" class="text-emerald-400" />
            <p class="text-emerald-400 text-base font-bold">
              {{ lastResult?.item_name }} — validé
            </p>
          </template>
        </div>

        <!-- All validated banner -->
        <div v-if="allValidated"
             class="rounded-md bg-emerald-900/40 border border-emerald-600/50 px-5 py-4
                    flex items-center justify-center gap-3">
          <CircleCheckBig :size="24" class="text-emerald-400" />
          <p class="text-emerald-300 text-xl font-black">
            Tous les matériaux sont validés !
          </p>
        </div>

        <!-- Manual entry button -->
        <button v-if="!allValidated"
                @click="openManual"
                class="w-full h-14 rounded-md bg-slate-800 border border-slate-700
                       text-slate-400 text-base font-semibold
                       flex items-center justify-center gap-2
                       active:bg-slate-700 transition">
          <Keyboard :size="18" />
          Saisie Manuelle
        </button>

        <!-- Finalize button -->
        <button v-if="allValidated"
                @click="finalizeMix"
                class="w-full h-16 rounded-md bg-emerald-600 text-white text-xl font-black
                       flex items-center justify-center gap-3
                       active:bg-emerald-700 transition animate-pulse-ring
                       shadow-lg shadow-emerald-500/20">
          <Check :size="24" :stroke-width="3" />
          FINALISER LE MÉLANGE
        </button>
      </section>
    </template>
  </div>
</template>
