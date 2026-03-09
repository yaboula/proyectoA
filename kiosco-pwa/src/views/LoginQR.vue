<script setup>
/**
 * LoginQR — Écran de connexion par badge QR.
 *
 * Design System: thème industriel premium (MES avancé).
 * Icônes: lucide-vue-next. Pas de bordures rondes infantiles (rounded-md max).
 * Tout bouton ≥ h-16. Texte en français.
 */
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import {
  ScanBarcode,
  Loader2,
  CircleCheckBig,
  CircleX,
  Keyboard,
  ChevronRight,
  ShieldCheck,
  X,
} from 'lucide-vue-next'

const router = useRouter()
const store = useOperarioStore()

// ── UI state ──
const status = ref('idle') // idle | scanning | loading | success | error
const messageFr = ref('Scannez votre badge pour commencer')
const operarioName = ref('')

// ── Manual modal ──
const manualOpen = ref(false)
const manualToken = ref('')
const manualInputRef = ref(null)

watch(manualOpen, (open) => {
  if (open) nextTick(() => manualInputRef.value?.focus())
})

// ── Scanner buffer ──
const SCAN_GAP_MS = 80
let buffer = ''
let lastKeyTime = 0

function onKeyDown(e) {
  if (manualOpen.value) return

  const now = Date.now()
  if (now - lastKeyTime > SCAN_GAP_MS && buffer.length > 0) buffer = ''
  lastKeyTime = now

  if (e.key === 'Enter') {
    e.preventDefault()
    const token = buffer.trim()
    buffer = ''
    if (token.length >= 5) handleLogin(token)
    return
  }

  if (e.key.length === 1) {
    buffer += e.key
    if (status.value === 'idle' || status.value === 'error') {
      status.value = 'scanning'
      messageFr.value = 'Lecture du badge…'
    }
  }
}

async function handleLogin(qrToken) {
  status.value = 'loading'
  messageFr.value = 'Vérification…'

  try {
    const data = await store.login(qrToken)
    status.value = 'success'
    operarioName.value = data.operario.full_name
    messageFr.value = data.message_fr
    setTimeout(() => router.push({ name: 'tareas' }), 1200)
  } catch (err) {
    status.value = 'error'
    messageFr.value = err?.message_fr ?? 'Erreur inconnue. Réessayez.'
    setTimeout(() => {
      if (status.value === 'error') {
        status.value = 'idle'
        messageFr.value = 'Scannez votre badge pour commencer'
      }
    }, 4000)
  }
}

function openManual() {
  manualToken.value = ''
  manualOpen.value = true
}
function closeManual() {
  manualOpen.value = false
  manualToken.value = ''
}
function submitManual() {
  const token = manualToken.value.trim()
  if (token.length < 5) return
  closeManual()
  handleLogin(token)
}

onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <div class="min-h-dvh flex flex-col bg-slate-900 select-none">

    <!-- ═══ Top bar ═══ -->
    <header class="flex items-center justify-between px-6 py-4 bg-slate-800/60 border-b border-slate-700/50">
      <div class="flex items-center gap-3">
        <ShieldCheck :size="28" class="text-emerald-400" />
        <span class="text-lg font-bold tracking-wide text-slate-200 uppercase">GCMA Kiosque</span>
      </div>
      <span class="text-sm text-slate-500 font-mono">v0.2.0</span>
    </header>

    <!-- ═══ Center zone ═══ -->
    <main class="flex-1 flex flex-col items-center justify-center px-6 gap-8">

      <!-- Scan icon — giant barcode -->
      <div class="relative">
        <div class="w-32 h-32 rounded-md bg-slate-800 border-2 flex items-center justify-center transition-all duration-300"
             :class="{
               'border-slate-600':   status === 'idle',
               'border-emerald-500 animate-pulse-ring': status === 'scanning',
               'border-amber-500':   status === 'loading',
               'border-emerald-400': status === 'success',
               'border-rose-500':    status === 'error',
             }">
          <!-- idle -->
          <ScanBarcode v-if="status === 'idle'"
                       :size="64" :stroke-width="1.5"
                       class="text-slate-400" />
          <!-- scanning -->
          <ScanBarcode v-else-if="status === 'scanning'"
                       :size="64" :stroke-width="1.5"
                       class="text-emerald-400 animate-pulse" />
          <!-- loading -->
          <Loader2 v-else-if="status === 'loading'"
                   :size="64" :stroke-width="2"
                   class="text-amber-400 animate-spin" />
          <!-- success -->
          <CircleCheckBig v-else-if="status === 'success'"
                          :size="64" :stroke-width="1.5"
                          class="text-emerald-400" />
          <!-- error -->
          <CircleX v-else
                   :size="64" :stroke-width="1.5"
                   class="text-rose-400" />
        </div>
      </div>

      <!-- Operator name on success -->
      <p v-if="status === 'success'" class="text-3xl font-black text-emerald-400 tracking-tight">
        {{ operarioName }}
      </p>

      <!-- French message -->
      <p class="text-xl font-semibold text-center leading-relaxed max-w-md transition-colors duration-200"
         :class="{
           'text-slate-400':   status === 'idle',
           'text-emerald-300': status === 'scanning',
           'text-amber-300':   status === 'loading',
           'text-emerald-300': status === 'success',
           'text-rose-400':    status === 'error',
         }">
        {{ messageFr }}
      </p>

      <!-- Instruction -->
      <p v-if="status === 'idle'" class="text-sm text-slate-600 text-center">
        Présentez votre badge devant la douchette
      </p>
    </main>

    <!-- ═══ Bottom zone ═══ -->
    <footer class="px-6 pb-8 pt-4">
      <button @click="openManual"
              class="w-full h-16 flex items-center justify-center gap-3
                     rounded-md border border-slate-700 bg-slate-800
                     text-slate-400 text-base font-semibold
                     active:bg-slate-700 transition">
        <Keyboard :size="22" />
        Saisie manuelle
      </button>
    </footer>

    <!-- ═══ MANUAL MODAL (shadcn Dialog style) ═══ -->
    <Teleport to="body">
      <div v-if="manualOpen"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in"
           @click.self="closeManual">
        <div class="w-full max-w-md mx-6 bg-slate-800 border border-slate-700 rounded-md shadow-2xl p-6">
          <!-- Header -->
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold text-slate-100">Saisie manuelle</h2>
            <button @click="closeManual"
                    class="w-10 h-10 flex items-center justify-center rounded-md
                           text-slate-400 hover:bg-slate-700 transition">
              <X :size="20" />
            </button>
          </div>

          <!-- Description -->
          <p class="text-sm text-slate-400 mb-4">
            Entrez le code de votre badge manuellement si la douchette ne fonctionne pas.
          </p>

          <!-- Input -->
          <input ref="manualInputRef"
                 v-model="manualToken"
                 type="text"
                 inputmode="text"
                 autocomplete="off"
                 class="w-full h-16 px-4 text-xl font-mono text-slate-100
                        bg-slate-900 border border-slate-600 rounded-md
                        focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/50
                        placeholder:text-slate-600"
                 placeholder="OP-2026-BADGE-00042"
                 @keydown.enter.prevent="submitManual" />

          <!-- Actions -->
          <div class="mt-6 flex gap-3">
            <button @click="closeManual"
                    class="flex-1 h-14 rounded-md border border-slate-600 bg-slate-800
                           text-slate-300 text-base font-semibold
                           active:bg-slate-700 transition">
              Annuler
            </button>
            <button @click="submitManual"
                    :disabled="manualToken.trim().length < 5"
                    class="flex-1 h-14 rounded-md bg-emerald-600 text-white text-base font-bold
                           flex items-center justify-center gap-2
                           active:bg-emerald-700 disabled:opacity-40 transition">
              Valider
              <ChevronRight :size="20" />
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
