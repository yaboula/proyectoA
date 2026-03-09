<script setup>
/**
 * PokaYokeScanner â€” Validation des matÃ©riaux par scan QR (EP3).
 * UI industrielle avec PrimeVue + thÃ¨me sombre professionnel.
 */
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas, validarMaterial } from '../api/kiosco'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'

const props = defineProps({ workOrder: String })
const router = useRouter()
const store = useOperarioStore()

// â”€â”€ Tarea data â”€â”€
const tarea = ref(null)
const materials = ref([])
const loadingTarea = ref(true)
const loadError = ref(null)

// â”€â”€ Scanner state â”€â”€
const scanState = ref('ready') // ready | scanning | loading | success | error
const lastResult = ref(null)
const recentlyValidated = ref(-1)

// â”€â”€ Manual entry â”€â”€
const manualOpen = ref(false)
const manualInput = ref('')
const manualInputRef = ref(null)

// â”€â”€ Computed â”€â”€
const allValidated = computed(
  () => materials.value.length > 0 && materials.value.every(m => m.status === 'validated')
)
const validatedCount = computed(
  () => materials.value.filter(m => m.status === 'validated').length
)
const progressPct = computed(
  () => materials.value.length ? (validatedCount.value / materials.value.length) * 100 : 0
)

// â”€â”€ Load tarea via EP2 â”€â”€
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
      loadError.value = 'Ordre de fabrication introuvable.'
    }
  } catch (err) {
    loadError.value = err?.message_fr ?? 'Erreur de chargement.'
  } finally {
    loadingTarea.value = false
  }
}

// â”€â”€ USB HID Scanner â”€â”€
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
    if (scanState.value === 'ready' || scanState.value === 'success') scanState.value = 'scanning'
  }
}

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
      setTimeout(() => { if (scanState.value === 'success') scanState.value = 'ready' }, 2500)
    } else {
      scanState.value = 'error'
    }
  } catch (err) {
    scanState.value = 'error'
    lastResult.value = { message_fr: err?.message_fr ?? 'Erreur de communication avec le serveur.' }
  }
}

function dismissError() {
  scanState.value = 'ready'
  lastResult.value = null
}

function openManual() { manualOpen.value = true; manualInput.value = '' }
function closeManual() { manualOpen.value = false }
function onManualDialogShow() { manualInputRef.value?.$el?.focus() }
function submitManual() {
  const val = manualInput.value.trim()
  closeManual()
  if (val.length >= 3) handleScan(val)
}

function goBack() { router.push({ name: 'tareas' }) }
function finalizeMix() { router.push({ name: 'tareas' }) }

onMounted(() => { loadTarea(); window.addEventListener('keydown', onKeyDown) })
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <!-- â•® Full-screen STOP error overlay â•¯ -->
  <Teleport to="body">
    <div v-if="scanState === 'error'"
         class="fixed inset-0 z-50 flex flex-col items-center justify-center px-8
                bg-red-900"
         :class="lastResult?.alerta_nivel === 'CRITICO' ? 'animate-pulse' : ''">

      <div class="w-24 h-24 rounded-full bg-red-700/60 flex items-center justify-center mb-8">
        <i class="pi pi-ban text-white" style="font-size: 3.5rem"></i>
      </div>

      <p class="text-white font-black text-3xl text-center leading-snug max-w-lg">
        {{ lastResult?.message_fr ?? 'Erreur inconnue' }}
      </p>

      <div v-if="lastResult?.alerta_nivel === 'CRITICO'"
           class="mt-4 px-4 py-1.5 rounded-full bg-red-700/60 border border-red-500">
        <span class="text-red-200 text-sm font-bold tracking-widest uppercase">âš ï¸ Alertre critique</span>
      </div>

      <Button label="FERMER"
              severity="secondary"
              outlined
              size="large"
              class="mt-10 !px-12 !py-5 !text-xl !font-black !text-white !border-white/60
                     hover:!bg-white/10"
              @click="dismissError" />
    </div>
  </Teleport>

  <!-- â•® Manual entry Dialog â•¯ -->
  <Dialog v-model:visible="manualOpen"
          modal
          :closable="false"
          header="Saisie Manuelle"
          :style="{ width: '92vw', maxWidth: '420px' }"
          @show="onManualDialogShow">
    <div class="flex flex-col gap-5 pt-1">
      <p class="text-sm text-slate-400">
        Entrez le code QR du matÃ©riau (formatÂ : CODE|LOT) :
      </p>
      <InputText ref="manualInputRef"
                 v-model="manualInput"
                 size="large"
                 placeholder="CODE|LOT"
                 autocomplete="off"
                 @keydown.enter="submitManual" />
      <div class="flex gap-3">
        <Button label="Annuler" severity="secondary" outlined class="flex-1 !py-4" @click="closeManual" />
        <Button label="Valider" severity="primary" class="flex-1 !py-4"
                :disabled="manualInput.trim().length < 3"
                @click="submitManual" />
      </div>
    </div>
  </Dialog>

  <!-- â•® Main layout â•¯ -->
  <div class="min-h-dvh bg-[#080d1a] flex flex-col">

    <!-- Top accent -->
    <div class="h-[3px] bg-gradient-to-r from-transparent via-blue-500 to-transparent shrink-0"></div>

    <!-- Header -->
    <header class="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/40
                   px-4 py-4 flex items-center gap-4 shrink-0">
      <Button icon="pi pi-arrow-left"
              severity="secondary"
              text
              rounded
              aria-label="Retour"
              @click="goBack" />
      <div class="flex-1 min-w-0">
        <h1 class="text-lg font-bold text-white truncate">
          {{ tarea?.producto ?? 'Validation MatÃ©riaux' }}
        </h1>
        <p class="text-slate-500 text-xs font-mono">{{ workOrder }}</p>
      </div>
      <!-- Progress counter badge -->
      <div class="shrink-0 text-center bg-slate-800 border border-slate-700
                  rounded-xl px-4 py-2">
        <span class="text-2xl font-black"
              :class="allValidated ? 'text-green-400' : 'text-white'">
          {{ validatedCount }}/{{ materials.length }}
        </span>
        <p class="text-slate-500 text-[0.6rem] uppercase tracking-wide">validÃ©s</p>
      </div>
    </header>

    <!-- Progress bar -->
    <ProgressBar :value="progressPct"
                 :showValue="false"
                 :pt="{ root: { class: '!rounded-none !h-[3px] !bg-slate-800/50' },
                        value: { class: allValidated ? '!bg-green-500' : '!bg-blue-500' } }" />

    <!-- Loading -->
    <div v-if="loadingTarea" class="flex-1 flex items-center justify-center">
      <i class="pi pi-spin pi-spinner text-slate-600" style="font-size: 3.5rem"></i>
    </div>

    <!-- Load error -->
    <div v-else-if="loadError"
         class="flex-1 flex flex-col items-center justify-center px-8 gap-5">
      <p class="text-red-400 text-xl font-bold text-center">{{ loadError }}</p>
      <Button label="â† Retour aux ordres" severity="secondary" @click="goBack" />
    </div>

    <template v-else>

      <!-- â•® Ingredients checklist â•¯ -->
      <section class="flex-1 overflow-y-auto px-4 pt-4 pb-2 space-y-3">
        <div v-for="(mat, i) in materials" :key="i"
             class="rounded-xl border transition-all duration-500"
             :class="{
               'bg-green-500/10 border-green-500/50 shadow shadow-green-900/30':  i === recentlyValidated,
               'bg-green-900/10 border-green-800/30':  mat.status === 'validated' && i !== recentlyValidated,
               'bg-slate-900/60 border-slate-700/30':  mat.status === 'pending',
             }">
          <div class="flex items-center gap-4 p-5">

            <!-- Status indicator -->
            <div v-if="mat.status === 'validated'"
                 class="shrink-0 w-12 h-12 rounded-full bg-green-500/20
                        border-2 border-green-500 flex items-center justify-center">
              <i class="pi pi-check text-green-400 text-xl"></i>
            </div>
            <div v-else
                 class="shrink-0 w-12 h-12 rounded-full bg-slate-800
                        border border-slate-600 flex items-center justify-center">
              <span class="text-slate-500 font-bold">{{ i + 1 }}</span>
            </div>

            <!-- Material info -->
            <div class="flex-1 min-w-0">
              <p class="text-lg font-semibold leading-tight"
                 :class="mat.status === 'validated' ? 'text-green-300' : 'text-white'">
                {{ mat.item_name }}
              </p>
              <p class="text-sm text-slate-500 mt-0.5">
                {{ mat.qty_requerida }}Â {{ mat.uom }}
                <span v-if="mat.scanResult?.batch_no" class="text-slate-600">
                  Â· LotÂ {{ mat.scanResult.batch_no }}
                </span>
              </p>
            </div>

            <!-- Stock badge (pending items only) -->
            <Tag v-if="mat.status === 'pending'"
                 :severity="mat.suficiente ? 'success' : 'danger'"
                 :value="mat.suficiente ? 'Stock OK' : 'Stock âœ—'"
                 class="shrink-0" />
          </div>
        </div>
      </section>

      <!-- â•® Bottom action zone â•¯ -->
      <section class="px-4 pb-5 pt-3 space-y-3 shrink-0">

        <!-- Scan status indicator -->
        <div v-if="!allValidated"
             class="rounded-xl px-5 py-4 flex items-center gap-3 border
                    transition-all duration-300"
             :class="{
               'bg-slate-900/60 border-slate-700/30':   scanState === 'ready',
               'bg-blue-500/10  border-blue-500/30':    scanState === 'scanning',
               'bg-amber-500/10 border-amber-500/30':   scanState === 'loading',
               'bg-green-500/10 border-green-500/30':   scanState === 'success',
             }">
          <i class="text-2xl shrink-0 transition-colors"
             :class="{
               'pi pi-qrcode text-slate-500':            scanState === 'ready',
               'pi pi-barcode text-blue-400':            scanState === 'scanning',
               'pi pi-spin pi-spinner text-amber-400':   scanState === 'loading',
               'pi pi-check-circle text-green-400':      scanState === 'success',
             }"></i>
          <p class="text-base font-medium transition-colors"
             :class="{
               'text-slate-400': scanState === 'ready',
               'text-blue-300':  scanState === 'scanning',
               'text-amber-300': scanState === 'loading',
               'text-green-300': scanState === 'success',
             }">
            <template v-if="scanState === 'ready'">Scannez le prochain matÃ©riau</template>
            <template v-else-if="scanState === 'scanning'">Lecture du codeâ€¦</template>
            <template v-else-if="scanState === 'loading'">VÃ©rification en coursâ€¦</template>
            <template v-else-if="scanState === 'success'">{{ lastResult?.item_name }}Â â€” validÃ©</template>
          </p>
        </div>

        <!-- All validated banner -->
        <div v-if="allValidated"
             class="rounded-xl border border-green-600/30 bg-green-900/20
                    px-5 py-4 flex items-center gap-3">
          <i class="pi pi-check-circle text-green-400 text-2xl"></i>
          <p class="text-green-300 text-lg font-bold">
            Tous les matÃ©riaux sont validÃ©s !
          </p>
        </div>

        <!-- Manual button -->
        <Button v-if="!allValidated"
                label="Saisie Manuelle"
                icon="pi pi-keyboard"
                severity="secondary"
                outlined
                fluid
                class="!py-4 !text-sm"
                @click="openManual" />

        <!-- Finalize button -->
        <Button v-if="allValidated"
                label="FINALISER LE MÃ‰LANGE"
                icon="pi pi-check-circle"
                icon-pos="right"
                severity="success"
                size="large"
                fluid
                class="!py-6 !text-xl !font-black !tracking-wider animate-pulse"
                @click="finalizeMix" />
      </section>
    </template>
  </div>
</template>
