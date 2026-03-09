<script setup>
/**
 * PokaYokeScanner — Validation des matériaux par scan QR (EP3).
 *
 * Affiche la checklist d'ingrédients de la Work Order.
 * Le scanner USB HID capture les QR de bidons de matière première.
 * UX sémaphorique : vert = validé, rouge plein écran = erreur STOP.
 * Quand tout est vert → bouton "FINALISER LE MÉLANGE".
 */
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas, validarMaterial } from '../api/kiosco'

const props = defineProps({ workOrder: String })
const router = useRouter()
const store = useOperarioStore()

// ── Tarea data ──
const tarea = ref(null)
const materials = ref([])
// Each entry: { item_name, qty_requerida, uom, qty_disponible, suficiente, status, scanResult }
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

      // Mark the first unvalidated matching material
      const idx = materials.value.findIndex(
        m => m.item_name === data.item_name && m.status !== 'validated'
      )
      if (idx >= 0) {
        materials.value[idx].status = 'validated'
        materials.value[idx].scanResult = data
        recentlyValidated.value = idx
        setTimeout(() => { recentlyValidated.value = -1 }, 1500)
      }

      // Auto-clear success after 2.5s
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
  // EP4 TODO — for now, navigate back to task list
  router.push({ name: 'tareas' })
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
  <!-- ═══ ERROR OVERLAY — full screen red (Teleported) ═══ -->
  <Teleport to="body">
    <div v-if="scanState === 'error'"
         class="fixed inset-0 z-50 flex flex-col items-center justify-center px-8"
         :class="lastResult?.alerta_nivel === 'CRITICO'
           ? 'bg-red-700 animate-pulse'
           : 'bg-red-600'">
      <p class="text-white text-7xl font-black mb-8">✗</p>
      <p class="text-white text-3xl font-bold text-center leading-relaxed max-w-lg">
        {{ lastResult?.message_fr ?? 'Erreur inconnue' }}
      </p>
      <button @click="dismissError"
              class="mt-12 px-12 py-5 bg-white text-red-700 rounded-2xl text-xl font-black
                     active:bg-red-100 transition shadow-lg">
        FERMER
      </button>
    </div>
  </Teleport>

  <!-- ═══ MANUAL INPUT MODAL (Teleported) ═══ -->
  <Teleport to="body">
    <div v-if="manualOpen"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-6">
      <div class="w-full max-w-md bg-white rounded-3xl p-8 shadow-2xl">
        <h2 class="text-2xl font-bold text-slate-800 mb-4">Saisie Manuelle</h2>
        <p class="text-slate-500 mb-5 text-base">
          Entrez le code QR du matériau (format : CODE|LOT) :
        </p>
        <input ref="manualInputRef"
               v-model="manualInput"
               type="text"
               autocomplete="off"
               class="w-full text-2xl border-2 border-slate-300 rounded-xl px-4 py-4
                      focus:border-blue-500 focus:outline-none"
               placeholder="CODE|LOT"
               @keydown.enter="submitManual" />
        <div class="mt-6 flex gap-4">
          <button @click="closeManual"
                  class="flex-1 py-4 rounded-xl bg-slate-200 text-slate-700 text-lg font-bold
                         active:bg-slate-300 transition">
            Annuler
          </button>
          <button @click="submitManual"
                  :disabled="manualInput.trim().length < 3"
                  class="flex-1 py-4 rounded-xl bg-blue-700 text-white text-lg font-bold
                         active:bg-blue-800 disabled:opacity-40 transition">
            Valider
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ═══ MAIN LAYOUT ═══ -->
  <div class="min-h-dvh bg-slate-900 flex flex-col">

    <!-- Header -->
    <header class="bg-blue-900 text-white px-5 py-4 flex items-center gap-4 shadow-lg">
      <button @click="goBack"
              class="shrink-0 rounded-xl bg-blue-800 px-4 py-3 text-lg font-bold
                     active:bg-blue-700 transition">
        ←
      </button>
      <div class="flex-1 min-w-0">
        <h1 class="text-xl font-bold truncate">{{ tarea?.producto ?? workOrder }}</h1>
        <p class="text-blue-300 text-sm">{{ workOrder }}</p>
      </div>
      <div class="shrink-0 text-right">
        <p class="text-3xl font-black">{{ validatedCount }}/{{ materials.length }}</p>
        <p class="text-blue-300 text-xs">validés</p>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loadingTarea" class="flex-1 flex items-center justify-center">
      <svg class="h-14 w-14 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Load Error -->
    <div v-else-if="loadError"
         class="flex-1 flex flex-col items-center justify-center px-8 gap-5">
      <p class="text-red-400 text-xl font-bold text-center">{{ loadError }}</p>
      <button @click="goBack"
              class="rounded-2xl bg-blue-700 text-white px-8 py-4 text-lg font-bold
                     active:bg-blue-800 transition">
        ← Retour aux ordres
      </button>
    </div>

    <!-- ═══ Main Content ═══ -->
    <template v-else>

      <!-- Materials checklist (scrollable) -->
      <section class="flex-1 overflow-y-auto px-5 pt-5 pb-3 space-y-3">
        <div v-for="(mat, i) in materials" :key="i"
             class="rounded-2xl p-5 border-2 transition-all duration-500"
             :class="{
               'bg-green-200 border-green-500 scale-[1.02] shadow-lg shadow-green-400/30':
                 i === recentlyValidated,
               'bg-green-50 border-green-400':
                 mat.status === 'validated' && i !== recentlyValidated,
               'bg-white border-slate-700':
                 mat.status === 'pending',
             }">
          <div class="flex items-center gap-4">
            <!-- Status icon -->
            <div v-if="mat.status === 'validated'"
                 class="shrink-0 w-14 h-14 rounded-full bg-green-500 flex items-center justify-center">
              <span class="text-white text-3xl font-black">✓</span>
            </div>
            <div v-else
                 class="shrink-0 w-14 h-14 rounded-full border-3 border-slate-500
                        flex items-center justify-center">
              <span class="text-slate-400 text-xl font-bold">{{ i + 1 }}</span>
            </div>

            <!-- Material info -->
            <div class="flex-1 min-w-0">
              <p class="text-xl font-bold truncate"
                 :class="mat.status === 'validated' ? 'text-green-800' : 'text-slate-800'">
                {{ mat.item_name }}
              </p>
              <p class="text-sm mt-0.5"
                 :class="mat.status === 'validated' ? 'text-green-600' : 'text-slate-500'">
                {{ mat.qty_requerida }} {{ mat.uom }}
                <template v-if="mat.scanResult?.batch_no">
                  · Lot {{ mat.scanResult.batch_no }}
                </template>
              </p>
            </div>

            <!-- Stock badge (pending only) -->
            <span v-if="mat.status === 'pending'"
                  class="shrink-0 rounded-full px-3 py-1 text-xs font-bold"
                  :class="mat.suficiente
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'">
              {{ mat.suficiente ? 'Stock OK' : 'Stock ✗' }}
            </span>
          </div>
        </div>
      </section>

      <!-- Bottom zone: scan status + actions (always visible) -->
      <section class="px-5 pb-5 pt-3 space-y-3">

        <!-- Scan status indicator -->
        <div v-if="!allValidated"
             class="rounded-2xl px-6 py-5 text-center transition-all duration-300"
             :class="{
               'bg-slate-800':  scanState === 'ready',
               'bg-blue-800':   scanState === 'scanning',
               'bg-amber-700':  scanState === 'loading',
               'bg-green-700':  scanState === 'success',
             }">
          <p class="text-white text-xl font-semibold">
            <template v-if="scanState === 'ready'">
              📷 Scannez le prochain matériau
            </template>
            <template v-else-if="scanState === 'scanning'">
              Lecture du code…
            </template>
            <template v-else-if="scanState === 'loading'">
              Vérification en cours…
            </template>
            <template v-else-if="scanState === 'success'">
              ✓ {{ lastResult?.item_name }} — validé
            </template>
          </p>
        </div>

        <!-- All validated banner -->
        <div v-if="allValidated" class="rounded-2xl bg-green-700 px-6 py-5 text-center">
          <p class="text-white text-2xl font-black">
            ✓ Tous les matériaux sont validés !
          </p>
        </div>

        <!-- Manual entry button -->
        <button v-if="!allValidated"
                @click="openManual"
                class="w-full py-4 rounded-2xl bg-slate-700 text-slate-300 text-base font-semibold
                       active:bg-slate-600 transition">
          ⌨ Saisie Manuelle
        </button>

        <!-- Finalize button (pulsing) -->
        <button v-if="allValidated"
                @click="finalizeMix"
                class="w-full py-6 rounded-2xl bg-green-600 text-white text-2xl font-black
                       active:bg-green-700 transition animate-pulse
                       shadow-lg shadow-green-500/30">
          FINALISER LE MÉLANGE ✓
        </button>
      </section>
    </template>
  </div>
</template>
