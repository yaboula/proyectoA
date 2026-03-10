<script setup>
/**
 * PokaYokeScanner -- Validation des materiaux par scan QR (EP3/EP4).
 *
 * Refactored: useScanner, ScanStation, ManualInputModal, FullScreenOverlay, KioskLayout.
 */
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas, validarMaterial, reportarConsumo } from '../api/kiosco'
import { useScanner } from '../composables/useScanner'
import KioskLayout from '../components/KioskLayout.vue'
import ScanStation from '../components/ScanStation.vue'
import ManualInputModal from '../components/ManualInputModal.vue'
import FullScreenOverlay from '../components/FullScreenOverlay.vue'
import {
  ArrowLeft,
  Loader2,
  CircleAlert,
  CircleCheckBig,
  TriangleAlert,
  Keyboard,
  X,
  Check,
  Beaker,
  Scale,
  PackageCheck,
} from 'lucide-vue-next'

const props = defineProps({ workOrder: String })
const router = useRouter()
const store = useOperarioStore()

// -- Tarea data --
const tarea = ref(null)
const materials = ref([])
const loadingTarea = ref(true)
const loadError = ref(null)

// -- Scanner state --
const scanState = ref('ready')
const lastResult = ref(null)
const recentlyValidated = ref(-1)

// -- Manual entry --
const manualOpen = ref(false)
const manualInput = ref('')

// -- Finalization / EP4 state --
const finalizePhase = ref('idle')
const extras = ref([])
const finalizeResult = ref(null)
const finalizeError = ref('')

// -- Computed --
const allValidated = computed(() =>
  materials.value.length > 0 && materials.value.every(m => m.status === 'validated')
)
const validatedCount = computed(() =>
  materials.value.filter(m => m.status === 'validated').length
)

// -- Scanner composable --
const scanDisabled = computed(() => manualOpen.value || scanState.value === 'error')
const { isScanning } = useScanner(handleScan, { minLength: 3, disabled: scanDisabled })

watch(isScanning, (scanning) => {
  if (scanning && (scanState.value === 'ready' || scanState.value === 'success')) {
    scanState.value = 'scanning'
  }
})

// -- Scan status message --
const scanMessage = computed(() => {
  if (scanState.value === 'ready') return 'Scannez le prochain materiau'
  if (scanState.value === 'scanning') return 'Lecture du code...'
  if (scanState.value === 'loading') return 'Verification en cours...'
  if (scanState.value === 'success') return `${lastResult.value?.item_name} valide`
  return 'Controle bloque'
})

const scanHint = computed(() => {
  if (allValidated.value) return 'Tous les composants requis ont ete confirmes.'
  return 'Le controle QR reste actif en continu tant que la liste n\'est pas complete.'
})

// -- Load tarea from EP2 --
async function loadTarea() {
  loadingTarea.value = true
  loadError.value = null
  try {
    const data = await getTareas(store.operario.company, store.operario.default_warehouse)
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

// -- Validate scanned material via EP3 --
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

// -- Manual entry --
function openManual() { manualOpen.value = true; manualInput.value = '' }
function closeManual() { manualOpen.value = false }
function submitManual(val) { closeManual(); if (val.length >= 3) handleScan(val) }

// -- Navigation --
function goBack() { router.push({ name: 'tareas' }) }

// -- EP4 finalization --
function finalizeMix() { finalizePhase.value = 'asking' }

function confirmStandard() { callEP4({}) }

function showExtras() {
  extras.value = materials.value.map(m => ({
    item_name: m.item_name,
    uom: m.uom,
    qty_extra: 0,
  }))
  finalizePhase.value = 'extras'
}

function submitExtras() {
  const withExtra = Object.fromEntries(
    extras.value.filter(e => e.qty_extra > 0).map(e => [e.item_name, e.qty_extra])
  )
  callEP4(withExtra)
}

function buildLotesUsados() {
  return Object.fromEntries(
    materials.value.map(material => [
      material.item_name,
      material.scanResult?.batch_no ?? 'SIN-LOTE',
    ])
  )
}

async function callEP4(extrasMap) {
  finalizePhase.value = 'submitting'
  finalizeError.value = ''
  try {
    const data = await reportarConsumo(props.workOrder, buildLotesUsados(), extrasMap)
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

function retryFinalize() { finalizePhase.value = 'asking' }

onMounted(loadTarea)
</script>

<template>
  <!-- === ERROR OVERLAY -- tap to dismiss === -->
  <FullScreenOverlay
    :visible="scanState === 'error'"
    variant="error"
    :title="lastResult?.message_fr ?? 'Erreur inconnue'"
    hint="Appuyez pour fermer"
    :clickable="true"
    @dismiss="dismissError"
  />

  <!-- === EP4 -- SUBMITTING OVERLAY === -->
  <FullScreenOverlay
    :visible="finalizePhase === 'submitting'"
    variant="loading"
    title="Enregistrement en cours..."
  />

  <!-- === EP4 -- SUCCESS OVERLAY === -->
  <FullScreenOverlay
    :visible="finalizePhase === 'success'"
    variant="success"
    title="LOT TERMINE"
    subtitle="Placer en zone de Quarantaine"
    hint="Redirection automatique..."
  >
    <template #alert>
      <div v-if="finalizeResult?.alerta"
           class="mt-6 rounded-md bg-amber-900/60 border border-amber-500/50 px-5 py-3 max-w-sm">
        <p class="text-amber-200 text-sm font-bold text-center">
          <TriangleAlert :size="16" class="inline mr-1 -mt-0.5" />
          {{ finalizeResult.message_fr }}
        </p>
      </div>
    </template>
  </FullScreenOverlay>

  <!-- === EP4 -- ERROR OVERLAY with retry === -->
  <FullScreenOverlay
    :visible="finalizePhase === 'error'"
    variant="error"
    title="Erreur d'enregistrement"
    :subtitle="finalizeError"
    :shake="false"
  >
    <template #action>
      <button @click="retryFinalize"
              class="mt-8 h-16 px-10 rounded-md bg-slate-900 border border-rose-300/30 text-rose-100 text-lg font-black active:bg-slate-800 transition">
        Reessayer
      </button>
      <button @click="finalizePhase = 'idle'"
              class="mt-3 text-rose-200/70 text-sm font-medium underline">
        Annuler
      </button>
    </template>
  </FullScreenOverlay>

  <!-- === MANUAL INPUT MODAL === -->
  <ManualInputModal
    :open="manualOpen"
    v-model="manualInput"
    title="Saisie Manuelle"
    description="Entrez le code QR du materiau (format : CODE|LOT) :"
    placeholder="CODE|LOT"
    :min-length="3"
    @close="closeManual"
    @submit="submitManual"
  />

  <!-- === EP4 -- "Standard ou Extra ?" DIALOG === -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'asking'"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-5">
      <div class="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-md p-6 shadow-2xl animate-fade-in">
        <div class="flex items-center gap-3 mb-5">
          <Scale :size="28" class="text-amber-400" />
          <h2 class="text-xl font-bold text-zinc-50">Ajustement Consommation</h2>
        </div>
        <p class="text-zinc-400 text-base mb-6 leading-relaxed">
          Le melange est pret. La consommation correspond-elle aux quantites standard ?
        </p>
        <div class="space-y-3">
          <button @click="confirmStandard"
                  class="w-full h-16 rounded-md bg-zinc-50 text-zinc-900 text-lg font-bold flex items-center justify-center gap-3 active:bg-zinc-200 transition">
            <Check :size="22" :stroke-width="3" />
            NON, consommation standard
          </button>
          <button @click="showExtras"
                  class="w-full h-16 rounded-md bg-amber-600 text-white text-lg font-bold flex items-center justify-center gap-3 active:bg-amber-700 transition">
            <Scale :size="22" :stroke-width="2.5" />
            OUI, ajouter un extra
          </button>
        </div>
        <button @click="finalizePhase = 'idle'"
                class="w-full mt-4 h-12 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 text-sm font-semibold active:bg-zinc-800 transition">
          Annuler
        </button>
      </div>
    </div>
  </Teleport>

  <!-- === EP4 -- EXTRAS INPUT FORM === -->
  <Teleport to="body">
    <div v-if="finalizePhase === 'extras'"
         class="fixed inset-0 z-40 bg-black/70 flex items-center justify-center px-5">
      <div class="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-md shadow-2xl animate-fade-in max-h-[90dvh] flex flex-col">
        <div class="p-6 pb-3 flex items-center justify-between">
          <h2 class="text-xl font-bold text-zinc-50">Quantites Extra</h2>
          <button @click="finalizePhase = 'asking'"
                  class="h-10 w-10 flex items-center justify-center rounded-md text-zinc-500 hover:text-zinc-300 active:bg-zinc-800 transition">
            <X :size="20" />
          </button>
        </div>
        <p class="px-6 text-zinc-400 text-sm mb-4">
          Indiquez la quantite supplementaire (Kg/L) pour chaque ingredient :
        </p>
        <div class="flex-1 overflow-y-auto px-6 space-y-3 pb-4">
          <div v-for="(ex, i) in extras" :key="i"
               class="rounded-md bg-zinc-950 border border-zinc-800 p-4">
            <p class="text-base font-bold text-zinc-50 mb-2 truncate">{{ ex.item_name }}</p>
            <div class="flex items-center gap-3">
              <span class="text-sm text-zinc-500">Extra :</span>
              <input v-model.number="ex.qty_extra"
                     type="number" min="0" step="0.1"
                     class="flex-1 bg-zinc-900 border border-zinc-800 rounded-md px-3 py-3 text-lg font-mono text-zinc-50 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500/30"
                     placeholder="0" />
              <span class="text-sm text-zinc-400 font-medium">{{ ex.uom }}</span>
            </div>
          </div>
        </div>
        <div class="p-6 pt-3 space-y-3 border-t border-zinc-800">
          <button @click="submitExtras"
                  class="w-full h-16 rounded-md bg-zinc-50 text-zinc-900 text-lg font-bold flex items-center justify-center gap-3 active:bg-zinc-200 transition">
            <PackageCheck :size="22" :stroke-width="2.5" />
            Valider et Enregistrer
          </button>
          <button @click="finalizePhase = 'asking'"
                  class="w-full h-12 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 text-sm font-semibold active:bg-zinc-800 transition">
            Retour
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- === MAIN LAYOUT === -->
  <KioskLayout>
    <header class="glass-panel kiosk-panel rounded-md p-5">
      <div class="gcma-toolbar">
        <div class="flex min-w-0 items-start gap-3">
          <button @click="goBack"
                  class="shrink-0 h-12 w-12 rounded-md border border-zinc-800 bg-zinc-950 flex items-center justify-center text-zinc-400 active:bg-zinc-900 transition">
            <ArrowLeft :size="20" />
          </button>
          <div class="min-w-0">
            <div class="gcma-section-label">Poka-yoke matiere</div>
            <h1 class="mt-2 text-3xl font-black tracking-tight text-white truncate">{{ tarea?.producto ?? workOrder }}</h1>
            <p class="mt-2 flex items-center gap-2 text-sm font-mono text-zinc-500">
              <Beaker :size="12" />
              {{ workOrder }}
            </p>
          </div>
        </div>

        <div class="grid gap-3 md:grid-cols-3 text-sm text-zinc-400">
          <div class="gcma-stat min-w-[8rem]">
            <div class="gcma-section-label">Valides</div>
            <div class="mt-1 text-2xl font-black text-zinc-50">{{ validatedCount }}/{{ materials.length }}</div>
          </div>
          <div class="gcma-stat min-w-[8rem]">
            <div class="gcma-section-label">Restants</div>
            <div class="mt-1 text-2xl font-black text-white">{{ Math.max(materials.length - validatedCount, 0) }}</div>
          </div>
          <div class="gcma-stat min-w-[10rem]">
            <div class="gcma-section-label">Etat</div>
            <div class="mt-1 text-sm font-bold" :class="allValidated ? 'text-zinc-50' : 'text-zinc-300'">
              {{ allValidated ? 'Pret a cloturer' : 'Controle en cours' }}
            </div>
          </div>
        </div>
      </div>
    </header>

    <div v-if="loadingTarea" class="kiosk-panel flex flex-1 items-center justify-center rounded-md">
      <Loader2 :size="48" :stroke-width="2" class="text-zinc-500 animate-spin" />
    </div>

    <div v-else-if="loadError" class="kiosk-panel flex flex-1 flex-col items-center justify-center rounded-md px-8 gap-5">
      <CircleAlert :size="56" :stroke-width="1.5" class="text-rose-500" />
      <p class="text-rose-400 text-lg font-bold text-center">{{ loadError }}</p>
      <button @click="goBack"
              class="h-14 px-8 rounded-md bg-zinc-50 border border-zinc-50 text-zinc-900 text-base font-semibold flex items-center gap-2 active:bg-zinc-200 transition">
        <ArrowLeft :size="18" />
        Retour aux ordres
      </button>
    </div>

    <template v-else>
      <div class="grid flex-1 gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <!-- Material checklist -->
        <section class="kiosk-panel flex min-h-0 flex-col rounded-md">
          <div class="gcma-toolbar border-b border-zinc-800 px-5 py-4">
            <div>
              <div class="gcma-section-label">Checklist matiere</div>
              <div class="mt-1 text-xl font-black text-white">Sequence de validation</div>
            </div>
            <div class="kiosk-chip rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em]">
              {{ materials.length }} lignes BOM
            </div>
          </div>

          <div class="flex-1 space-y-3 overflow-y-auto px-5 py-4">
            <div v-for="(mat, i) in materials" :key="i"
                 class="gcma-data-row p-4 transition-all duration-500"
                 :class="{
                   'border-zinc-700 bg-zinc-900': i === recentlyValidated,
                   'border-zinc-800 bg-zinc-900/80': mat.status === 'validated' && i !== recentlyValidated,
                 }">
              <div class="grid gap-4 xl:grid-cols-[auto_1fr_auto] xl:items-center">
                <div v-if="mat.status === 'validated'"
                     class="flex h-12 w-12 items-center justify-center rounded-md bg-zinc-50 text-zinc-900">
                  <CircleCheckBig :size="24" :stroke-width="2.5" />
                </div>
                <div v-else class="flex h-12 w-12 items-center justify-center rounded-md border-2 border-zinc-700 text-lg font-bold text-zinc-500">
                  {{ i + 1 }}
                </div>

                <div class="min-w-0">
                  <p class="text-lg font-bold truncate text-zinc-50">{{ mat.item_name }}</p>
                  <p class="mt-1 text-sm" :class="mat.status === 'validated' ? 'text-zinc-400' : 'text-zinc-500'">
                    {{ mat.qty_requerida }} {{ mat.uom }}
                    <template v-if="mat.scanResult?.batch_no"> &middot; Lot {{ mat.scanResult.batch_no }}</template>
                  </p>
                </div>

                <div class="flex flex-wrap gap-2 xl:justify-end">
                  <span class="rounded-md px-2.5 py-1 text-xs font-bold border"
                        :class="mat.suficiente
                          ? 'bg-zinc-950 text-zinc-50 border-zinc-800'
                          : 'bg-rose-900/30 text-rose-400 border-rose-700/50'">
                    {{ mat.suficiente ? 'Stock OK' : 'Stock insuffisant' }}
                  </span>
                  <span class="rounded-md px-2.5 py-1 text-xs font-bold border"
                        :class="mat.status === 'validated'
                          ? 'bg-zinc-950 text-zinc-50 border-zinc-800'
                          : 'bg-zinc-950 text-zinc-400 border-zinc-800'">
                    {{ mat.status === 'validated' ? 'Valide' : 'En attente' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Scan station + actions -->
        <section class="flex flex-col gap-5">
          <div class="kiosk-panel rounded-md p-5">
            <div class="gcma-section-label">Station de scan</div>
            <div class="mt-2 text-2xl font-black text-white">Lecture en direct</div>
            <div class="mt-5">
              <ScanStation
                :status="scanState === 'ready' ? 'idle' : scanState"
                :message="scanMessage"
                :hint="scanHint"
                size="md"
              />
            </div>
          </div>

          <div class="kiosk-panel rounded-md p-5">
            <div class="gcma-section-label">Actions</div>
            <div class="mt-2 text-2xl font-black text-white">Decision operateur</div>

            <div v-if="allValidated" class="mt-5 gcma-data-row flex items-center gap-3 px-4 py-4">
              <CircleCheckBig :size="24" class="text-emerald-400" />
              <p class="text-base font-bold text-zinc-50">Tous les materiaux sont valides.</p>
            </div>

            <div class="mt-5 space-y-3">
              <button v-if="!allValidated"
                      @click="openManual"
                      class="w-full h-14 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 text-base font-semibold active:bg-zinc-900 transition">
                <span class="inline-flex items-center gap-2">
                  <Keyboard :size="18" />
                  Saisie manuelle
                </span>
              </button>

              <button v-if="allValidated"
                      @click="finalizeMix"
                      class="w-full h-16 rounded-md bg-zinc-50 text-zinc-900 text-base font-black tracking-[0.12em] active:bg-zinc-200 transition animate-pulse-ring">
                <span class="inline-flex items-center justify-center gap-3">
                  <Check :size="24" :stroke-width="3" />
                  FINALISER LE MELANGE
                </span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </template>
  </KioskLayout>
</template>
