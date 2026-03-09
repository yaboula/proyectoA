<script setup>
/**
 * LoginQR â€” Ã‰cran de connexion par badge QR.
 *
 * Le kiosque n'a PAS de clavier. L'opÃ©rateur scanne son badge
 * avec une douchette USB-HID qui envoie des frappes clavier
 * terminÃ©es par Â« Enter Â».
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Divider from 'primevue/divider'

const router = useRouter()
const store = useOperarioStore()

// â”€â”€ UI state â”€â”€
const status = ref('idle')        // idle | scanning | loading | success | error
const messageFr = ref('Scannez votre badge pour commencer')
const operarioName = ref('')

// â”€â”€ Manual fallback modal â”€â”€
const manualOpen = ref(false)
const manualToken = ref('')
const manualInput = ref(null)   // template ref â†’ PrimeVue InputText

// â”€â”€ Scanner buffer â”€â”€
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
      messageFr.value = 'Lecture du badge en coursâ€¦'
    }
  }
}

async function handleLogin(qrToken) {
  status.value = 'loading'
  messageFr.value = 'VÃ©rificationâ€¦'
  try {
    const data = await store.login(qrToken)
    status.value = 'success'
    operarioName.value = data.operario.full_name
    messageFr.value = data.message_fr
    setTimeout(() => router.push({ name: 'tareas' }), 1200)
  } catch (err) {
    status.value = 'error'
    messageFr.value = err?.message_fr ?? 'Erreur inconnue. RÃ©essayez.'
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
function onDialogShow() {
  manualInput.value?.$el?.focus()
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
  <!-- â•â•â• Full-screen dark canvas â•â•â• -->
  <div class="min-h-dvh bg-[#080d1a] flex flex-col items-center justify-center p-6 relative overflow-hidden select-none">

    <!-- Subtle grid pattern (industrial aesthetic) -->
    <div class="pointer-events-none absolute inset-0"
         style="background-image: radial-gradient(circle, rgba(59,130,246,0.06) 1px, transparent 1px);
                background-size: 36px 36px"></div>

    <!-- Top brand accent line -->
    <div class="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-transparent via-blue-500 to-transparent"></div>
    <!-- Bottom accent -->
    <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>

    <div class="relative z-10 w-full max-w-[360px] flex flex-col gap-7">

      <!-- â•â• Brand â•â• -->
      <div class="text-center space-y-1">
        <p class="text-[0.65rem] font-semibold text-slate-600 uppercase tracking-[0.35em]">
          SystÃ¨me de Production
        </p>
        <h1 class="text-5xl font-black text-white tracking-tight leading-none">GCMA</h1>
        <p class="text-slate-500 text-sm tracking-widest uppercase">Kiosque OpÃ©rateur</p>
      </div>

      <!-- â•â• Status Card â•â• -->
      <Card class="overflow-hidden">
        <template #content>
          <div class="flex flex-col items-center gap-6">

            <!-- Icon area â€” animated by state -->
            <div class="w-28 h-28 rounded-2xl flex items-center justify-center
                        border-2 transition-all duration-500"
                 :class="{
                   'bg-slate-800/60 border-slate-700':      status === 'idle',
                   'bg-blue-500/10  border-blue-400':       status === 'scanning',
                   'bg-amber-500/10 border-amber-400':      status === 'loading',
                   'bg-green-500/10 border-green-400':      status === 'success',
                   'bg-red-500/10   border-red-400':        status === 'error',
                 }">
              <i class="text-[3.2rem] transition-all duration-300"
                 :class="{
                   'pi pi-id-card text-slate-500':              status === 'idle',
                   'pi pi-qrcode  text-blue-400 animate-pulse': status === 'scanning',
                   'pi pi-spin pi-spinner text-amber-400':      status === 'loading',
                   'pi pi-check-circle text-green-400':         status === 'success',
                   'pi pi-times-circle text-red-400':           status === 'error',
                 }"></i>
            </div>

            <!-- Operator name (success only) -->
            <p v-if="status === 'success'"
               class="text-2xl font-bold text-white tracking-tight text-center">
              {{ operarioName }}
            </p>

            <!-- Status message -->
            <p class="text-center text-base font-medium leading-snug transition-colors duration-300"
               :class="{
                 'text-slate-400': status === 'idle',
                 'text-blue-300':  status === 'scanning',
                 'text-amber-300': status === 'loading',
                 'text-green-300': status === 'success',
                 'text-red-300':   status === 'error',
               }">
              {{ messageFr }}
            </p>

            <Divider />

            <!-- Manual entry fallback -->
            <Button label="Saisie Manuelle"
                    icon="pi pi-keyboard"
                    severity="secondary"
                    outlined
                    fluid
                    class="!py-4 !text-sm !font-semibold"
                    @click="openManual" />
          </div>
        </template>
      </Card>

      <!-- Date -->
      <p class="text-center text-slate-700 text-xs">
        {{ new Date().toLocaleDateString('fr-MA', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }}
      </p>
    </div>

    <!-- â•â• Manual Entry Dialog â•â• -->
    <Dialog v-model:visible="manualOpen"
            modal
            :closable="false"
            header="Saisie Manuelle du Badge"
            :style="{ width: '92vw', maxWidth: '400px' }"
            @show="onDialogShow">
      <div class="flex flex-col gap-5 pt-1">
        <p class="text-sm text-slate-400">
          Entrez le numÃ©ro inscrit sur votre badge d'opÃ©rateur :
        </p>
        <InputText ref="manualInput"
                   v-model="manualToken"
                   size="large"
                   placeholder="Ex : OP-2026-BADGE-00042"
                   autocomplete="off"
                   :invalid="manualToken.length > 0 && manualToken.trim().length < 5"
                   @keydown.enter.prevent="submitManual" />
        <div class="flex gap-3 pt-1">
          <Button label="Annuler"
                  severity="secondary"
                  outlined
                  class="flex-1 !py-4"
                  @click="closeManual" />
          <Button label="Valider"
                  severity="primary"
                  class="flex-1 !py-4"
                  :disabled="manualToken.trim().length < 5"
                  @click="submitManual" />
        </div>
      </div>
    </Dialog>
  </div>
</template>
