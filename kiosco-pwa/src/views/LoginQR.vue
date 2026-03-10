<script setup>
/**
 * LoginQR  Ecran de connexion par badge QR.
 *
 * Refactored: useScanner composable, ScanStation, ManualInputModal, KioskLayout.
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { useScanner } from '../composables/useScanner'
import KioskLayout from '../components/KioskLayout.vue'
import ScanStation from '../components/ScanStation.vue'
import ManualInputModal from '../components/ManualInputModal.vue'
import { Keyboard, ShieldCheck } from 'lucide-vue-next'

const router = useRouter()
const store = useOperarioStore()

// -- UI state --
const status = ref('idle')
const messageFr = ref('Scannez votre badge pour commencer')
const operarioName = ref('')

// -- Manual modal --
const manualOpen = ref(false)
const manualToken = ref('')

// -- Scanner composable --
const scanDisabled = computed(() => manualOpen.value)
const { isScanning } = useScanner(handleLogin, { minLength: 5, disabled: scanDisabled })

watch(isScanning, (scanning) => {
  if (scanning && (status.value === 'idle' || status.value === 'error')) {
    status.value = 'scanning'
    messageFr.value = 'Lecture du badge...'
  }
})

async function handleLogin(qrToken) {
  const normalizedToken = String(qrToken ?? '').trim()
  if (normalizedToken.length < 5) {
    status.value = 'error'
    messageFr.value = 'Code QR manquant. Veuillez scanner votre badge.'
    setTimeout(() => {
      if (status.value === 'error') {
        status.value = 'idle'
        messageFr.value = 'Scannez votre badge pour commencer'
      }
    }, 2500)
    return
  }

  status.value = 'loading'
  messageFr.value = 'Verification...'

  try {
    const data = await store.login(normalizedToken)
    status.value = 'success'
    operarioName.value = data.operario.full_name
    messageFr.value = data.message_fr
    const nextRoute = data.operario.allowed_modules?.length === 1
      ? data.operario.default_route
      : '/hub'
    setTimeout(() => router.push(nextRoute), 1200)
  } catch (err) {
    status.value = 'error'
    messageFr.value = err?.message_fr ?? 'Erreur inconnue. Reessayez.'
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
function submitManual(token) {
  closeManual()
  handleLogin(token)
}

onMounted(async () => {
  const hasSession = await store.ensureSession()
  if (hasSession) {
    const nextRoute = store.allowedModules.length === 1
      ? (store.operario?.default_route ?? '/hub')
      : '/hub'
    router.replace(nextRoute)
  }
})
</script>

<template>
  <KioskLayout max-width="6xl">
    <header class="glass-panel kiosk-panel gcma-toolbar rounded-md px-6 py-5">
      <div class="flex items-center gap-3">
        <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-emerald-300">
          <ShieldCheck :size="24" />
        </div>
        <div>
          <div class="gcma-section-label">Acces atelier</div>
          <div class="text-xl font-black tracking-[0.08em] text-white uppercase">GCMA Kiosque</div>
        </div>
      </div>
      <div class="text-sm font-mono text-zinc-500">v0.5.0</div>
    </header>

    <main class="grid flex-1 gap-5 xl:grid-cols-[0.9fr_1.1fr]">
      <section class="glass-panel kiosk-panel flex flex-col justify-between rounded-md p-6">
        <div class="space-y-6">
          <div>
            <div class="gcma-section-label">Poste d'identification</div>
            <h1 class="mt-2 text-4xl font-black tracking-tight text-white md:text-5xl">Connexion badge</h1>
            <p class="mt-4 max-w-xl text-base leading-7 text-zinc-400">
              Authentification directe par douchette QR pour l'acces aux modules autorises du kiosque.
              Le poste reste utilisable avec gants et sans clavier permanent.
            </p>
          </div>

          <div class="grid gap-3 md:grid-cols-3 text-zinc-400">
            <div class="gcma-stat">
              <div class="gcma-section-label">Etape 01</div>
              <div class="mt-2 text-base font-bold text-zinc-50">Scanner le badge</div>
              <div class="mt-1 text-sm leading-6 text-zinc-400">Lecture HID automatique au retour chariot.</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Etape 02</div>
              <div class="mt-2 text-base font-bold text-zinc-50">Valider le profil</div>
              <div class="mt-1 text-sm leading-6 text-zinc-400">Controle du profil ERPNext et des modules autorises.</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Etape 03</div>
              <div class="mt-2 text-base font-bold text-zinc-50">Acceder au poste</div>
              <div class="mt-1 text-sm leading-6 text-zinc-400">Redirection immediate vers le flux production ou qualite.</div>
            </div>
          </div>
        </div>

        <div class="gcma-data-row mt-6 grid gap-3 p-4 md:grid-cols-2">
          <div>
            <div class="gcma-section-label">Mode</div>
            <div class="mt-1 text-sm font-semibold text-zinc-50">Scanner QR prioritaire</div>
          </div>
          <div>
            <div class="gcma-section-label">Secours</div>
            <div class="mt-1 text-sm font-semibold text-zinc-50">Saisie manuelle controlee</div>
          </div>
        </div>
      </section>

      <section class="glass-panel kiosk-panel flex flex-col rounded-md p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="gcma-section-label">Etat du lecteur</div>
            <div class="mt-2 text-2xl font-black text-white">Station de scan</div>
          </div>
          <div class="kiosk-chip rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em]">
            Badge QR
          </div>
        </div>

        <div class="mt-6 flex flex-1 flex-col items-center justify-center gap-6">
          <ScanStation
            :status="status"
            :message="messageFr"
            :success-label="operarioName"
            :hint="status === 'idle' ? 'Presentez le badge devant la douchette pour lancer la session.' : ''"
            size="lg"
          />
        </div>

        <div class="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
          <div class="gcma-data-row flex items-center px-4 py-3 text-sm text-zinc-400">
            Secours operateur en cas de lecture impossible ou badge endommage.
          </div>
          <button @click="openManual"
                  class="h-16 min-w-[15rem] rounded-md border border-zinc-800 bg-zinc-950 px-6 text-base font-semibold text-zinc-50 active:bg-zinc-900 transition">
            <span class="inline-flex items-center gap-3">
              <Keyboard :size="22" />
              Saisie manuelle
            </span>
          </button>
        </div>
      </section>
    </main>

    <ManualInputModal
      :open="manualOpen"
      v-model="manualToken"
      title="Saisie manuelle"
      description="Entrez le code de votre badge manuellement si la douchette ne fonctionne pas."
      placeholder="OP-2026-BADGE-00042"
      :min-length="5"
      @close="closeManual"
      @submit="submitManual"
    />
  </KioskLayout>
</template>
