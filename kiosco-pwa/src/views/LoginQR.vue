<script setup>
/**
 * LoginQR — Écran de connexion par badge QR.
 *
 * Le kiosque n'a PAS de clavier. L'opérateur scanne son badge
 * avec une douchette USB-HID qui envoie des frappes clavier
 * terminées par « Enter ».
 *
 * Stratégie :
 *  - Écouter keydown sur document
 *  - Accumuler les caractères rapides (< 80 ms entre chaque)
 *  - Déclencher le login au « Enter »
 */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'

const router = useRouter()
const store = useOperarioStore()

// ── UI state ──
const status = ref('idle')        // idle | scanning | loading | success | error
const messageFr = ref('Scannez votre badge pour commencer')
const operarioName = ref('')

// ── Manual fallback modal ──
const manualOpen = ref(false)
const manualToken = ref('')
const manualInput = ref(null)   // template ref

// ── Scanner buffer ──
const SCAN_GAP_MS = 80
let buffer = ''
let lastKeyTime = 0

function onKeyDown(e) {
  // Ignore scanner events while the manual modal is open
  if (manualOpen.value) return

  const now = Date.now()

  // Reset buffer if too much time between keystrokes (human typing)
  if (now - lastKeyTime > SCAN_GAP_MS && buffer.length > 0) {
    buffer = ''
  }
  lastKeyTime = now

  if (e.key === 'Enter') {
    e.preventDefault()
    const token = buffer.trim()
    buffer = ''
    if (token.length >= 5) {
      handleLogin(token)
    }
    return
  }

  // Only accept printable chars
  if (e.key.length === 1) {
    buffer += e.key
    if (status.value === 'idle' || status.value === 'error') {
      status.value = 'scanning'
      messageFr.value = 'Lecture du badge en cours…'
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

    // Navigate to tasks after brief success feedback
    setTimeout(() => router.push({ name: 'tareas' }), 1200)
  } catch (err) {
    status.value = 'error'
    messageFr.value = err?.message_fr ?? 'Erreur inconnue. Réessayez.'
    // Auto-reset to idle after 4 seconds
    setTimeout(() => {
      if (status.value === 'error') {
        status.value = 'idle'
        messageFr.value = 'Scannez votre badge pour commencer'
      }
    }, 4000)
  }
}

async function openManual() {
  manualToken.value = ''
  manualOpen.value = true
  await nextTick()
  manualInput.value?.focus()
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
  <div class="min-h-dvh flex flex-col items-center justify-center bg-slate-100 px-6 py-10">

    <!-- Logo / Title -->
    <div class="mb-10 text-center">
      <div class="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-sky-800 shadow-lg">
        <svg class="h-14 w-14 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M13.5 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
        </svg>
      </div>
      <h1 class="text-3xl font-bold tracking-tight text-slate-800">Kiosque Opérateur</h1>
      <p class="mt-1 text-lg text-slate-500">GCMA — Contrôle de Production</p>
    </div>

    <!-- Status card -->
    <div class="w-full max-w-md rounded-2xl bg-white shadow-xl p-8 text-center transition-all duration-300"
         :class="{
           'ring-4 ring-sky-300':    status === 'scanning',
           'ring-4 ring-amber-300':  status === 'loading',
           'ring-4 ring-green-400':  status === 'success',
           'ring-4 ring-red-400':    status === 'error',
         }">

      <!-- Icon per status -->
      <div class="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full transition-colors duration-300"
           :class="{
             'bg-slate-200':  status === 'idle',
             'bg-sky-100':    status === 'scanning',
             'bg-amber-100':  status === 'loading',
             'bg-green-100':  status === 'success',
             'bg-red-100':    status === 'error',
           }">

        <!-- Idle: badge icon -->
        <svg v-if="status === 'idle'" class="h-10 w-10 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15A2.25 2.25 0 002.25 6.75v10.5A2.25 2.25 0 004.5 19.5zm6-10.125a1.875 1.875 0 11-3.75 0 1.875 1.875 0 013.75 0zm1.294 6.336a6.721 6.721 0 01-3.17.789 6.721 6.721 0 01-3.168-.789 3.376 3.376 0 016.338 0z" />
        </svg>

        <!-- Scanning: barcode lines -->
        <svg v-else-if="status === 'scanning'" class="h-10 w-10 text-sky-600 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M13.5 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
        </svg>

        <!-- Loading: spinner -->
        <svg v-else-if="status === 'loading'" class="h-10 w-10 text-amber-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>

        <!-- Success: checkmark -->
        <svg v-else-if="status === 'success'" class="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>

        <!-- Error: X -->
        <svg v-else class="h-10 w-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <!-- Operator name on success -->
      <p v-if="status === 'success'" class="mb-2 text-2xl font-bold text-green-700">
        {{ operarioName }}
      </p>

      <!-- French message -->
      <p class="text-xl font-medium leading-relaxed"
         :class="{
           'text-slate-600':  status === 'idle',
           'text-sky-700':    status === 'scanning',
           'text-amber-700':  status === 'loading',
           'text-green-700':  status === 'success',
           'text-red-700':    status === 'error',
         }">
        {{ messageFr }}
      </p>
    </div>

    <!-- Manual fallback button -->
    <button @click="openManual"
            class="mt-8 rounded-xl border-2 border-slate-300 bg-white px-6 py-4 text-base font-semibold text-slate-500 shadow-sm active:bg-slate-100 transition">
      ⌨ Saisie manuelle du code
    </button>

    <!-- Subtle help text -->
    <p class="mt-4 text-sm text-slate-400">
      Utilisez la douchette pour scanner le code QR de votre badge
    </p>

    <!-- ── Manual input modal (Plan B) ── -->
    <Teleport to="body">
      <div v-if="manualOpen"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
           @click.self="closeManual">
        <div class="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
          <h2 class="mb-6 text-center text-2xl font-bold text-slate-800">
            Saisie manuelle
          </h2>

          <label for="manual-code" class="mb-2 block text-base font-medium text-slate-600">
            Code du badge
          </label>
          <input id="manual-code"
                 ref="manualInput"
                 v-model="manualToken"
                 type="text"
                 inputmode="text"
                 autocomplete="off"
                 class="w-full rounded-xl border-2 border-slate-300 px-5 py-4 text-xl text-slate-800
                        focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                 placeholder="Ex : OP-2026-BADGE-00042"
                 @keydown.enter.prevent="submitManual" />

          <div class="mt-6 flex gap-4">
            <button @click="closeManual"
                    class="flex-1 rounded-xl border-2 border-slate-300 py-4 text-lg font-semibold text-slate-500 active:bg-slate-100 transition">
              Annuler
            </button>
            <button @click="submitManual"
                    :disabled="manualToken.trim().length < 5"
                    class="flex-1 rounded-xl bg-sky-700 py-4 text-lg font-semibold text-white
                           active:bg-sky-600 transition disabled:opacity-40">
              Valider
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
