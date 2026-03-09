<script setup>
/**
 * PokaYokeScanner — Validation des matériaux par scan QR.
 * Stub — sera complété lors de l'implémentation de l'écran EP3.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { validarMaterial } from '../api/kiosco'

const props = defineProps({ workOrder: String })
const router = useRouter()

const status = ref('idle')    // idle | scanning | loading | valid | error
const messageFr = ref('Scannez un matériau pour valider')
const materialName = ref('')

const SCAN_GAP_MS = 80
let buffer = ''
let lastKeyTime = 0

function onKeyDown(e) {
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
    if (status.value === 'idle' || status.value === 'valid' || status.value === 'error') {
      status.value = 'scanning'
      messageFr.value = 'Lecture…'
    }
  }
}

async function handleScan(qrData) {
  status.value = 'loading'
  messageFr.value = 'Vérification du matériau…'
  try {
    const data = await validarMaterial(props.workOrder, qrData)
    if (data.valido) {
      status.value = 'valid'
      materialName.value = data.item_name
      messageFr.value = data.message_fr ?? 'Matériau validé ✓'
    } else {
      status.value = 'error'
      messageFr.value = data.message_fr ?? 'Matériau non valide'
    }
  } catch (err) {
    status.value = 'error'
    messageFr.value = err?.message_fr ?? 'Erreur de communication'
  }
}

onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <div class="min-h-dvh bg-slate-100 flex flex-col">
    <!-- Header -->
    <header class="bg-sky-800 text-white px-6 py-4 flex items-center justify-between shadow">
      <div>
        <h1 class="text-xl font-bold">Validation Matériaux</h1>
        <p class="text-sm text-sky-200">{{ workOrder }}</p>
      </div>
      <button @click="router.push({ name: 'tareas' })"
              class="rounded-xl bg-sky-700 px-5 py-3 text-base font-semibold active:bg-sky-600 transition">
        ← Retour
      </button>
    </header>

    <!-- Scan area -->
    <main class="flex-1 flex flex-col items-center justify-center px-6">
      <div class="w-full max-w-md rounded-2xl bg-white shadow-xl p-8 text-center transition-all duration-300"
           :class="{
             'ring-4 ring-sky-300':   status === 'scanning',
             'ring-4 ring-amber-300': status === 'loading',
             'ring-4 ring-green-400': status === 'valid',
             'ring-4 ring-red-400':   status === 'error',
           }">
        <p v-if="materialName && status === 'valid'" class="mb-2 text-2xl font-bold text-green-700">
          {{ materialName }}
        </p>
        <p class="text-xl font-medium"
           :class="{
             'text-slate-600': status === 'idle',
             'text-sky-700':   status === 'scanning',
             'text-amber-700': status === 'loading',
             'text-green-700': status === 'valid',
             'text-red-700':   status === 'error',
           }">
          {{ messageFr }}
        </p>
      </div>
    </main>
  </div>
</template>
