<script setup>
import { computed, onMounted, ref } from 'vue'
import { Camera, CheckCircle2, PenSquare, RefreshCcw, Truck } from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import { getEntregasPendientesChofer, registrarPod } from '../api/kiosco'

// getEntregasPendientesChofer ahora llama al endpoint custom /api/method/maroc_b2b.api.logistica.get_entregas_pendientes_chofer
// que devuelve { total, entregas: [...] } con customer_name y estado_entrega_pwa incluidos

const loading = ref(false)
const submitting = ref(false)
const entregas = ref([])
const selectedEntrega = ref(null)
const fotoFile = ref(null)
const successMessage = ref('')
const errorMessage = ref('')

const canvasRef = ref(null)
const drawing = ref(false)

const hasEntrega = computed(() => Boolean(selectedEntrega.value))

async function loadEntregas() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await getEntregasPendientesChofer()
    // El endpoint custom devuelve { total, entregas: [...] }
    entregas.value = response?.entregas ?? response?.data ?? []
  } catch (error) {
    errorMessage.value = error?.message_fr || error?.message || 'Impossible de charger les livraisons en attente.'
    entregas.value = []
  } finally {
    loading.value = false
  }
}

function pickEntrega(row) {
  selectedEntrega.value = row
  successMessage.value = ''
  errorMessage.value = ''
  clearCanvas()
  fotoFile.value = null
}

function clearCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
}

function getPointerPosition(event) {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()
  const source = event.touches ? event.touches[0] : event
  return {
    x: source.clientX - rect.left,
    y: source.clientY - rect.top,
  }
}

function startDraw(event) {
  if (!canvasRef.value) return
  drawing.value = true
  const ctx = canvasRef.value.getContext('2d')
  const pos = getPointerPosition(event)
  ctx.beginPath()
  ctx.moveTo(pos.x, pos.y)
}

function moveDraw(event) {
  if (!drawing.value || !canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  const pos = getPointerPosition(event)
  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  ctx.strokeStyle = '#18181b'
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
}

function endDraw() {
  drawing.value = false
}

function onPickPhoto(event) {
  const file = event.target.files?.[0]
  fotoFile.value = file || null
}

function canvasToB64() {
  const canvas = canvasRef.value
  if (!canvas) return ''
  return canvas.toDataURL('image/png')
}

function fileToB64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('PHOTO_READ_ERROR'))
    reader.readAsDataURL(file)
  })
}

async function submitPod() {
  if (!selectedEntrega.value || !fotoFile.value || submitting.value) return

  submitting.value = true
  successMessage.value = ''
  errorMessage.value = ''

  try {
    const b64_signature = canvasToB64()
    const b64_photo = await fileToB64(fotoFile.value)

    await registrarPod({
      delivery_note_id: selectedEntrega.value.name,
      b64_signature,
      b64_photo,
    })

    successMessage.value = `POD enregistre pour ${selectedEntrega.value.name}.`
    selectedEntrega.value = null
    fotoFile.value = null
    await loadEntregas()
  } catch (error) {
    errorMessage.value = error?.message || error?.message_fr || 'Echec lors de lenregistrement du POD.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadEntregas()
  clearCanvas()
})
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <Truck :size="14" />
            App Chofer POD
          </div>
          <div>
            <div class="gcma-section-label">Proof Of Delivery</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">
              Entregas del turno
            </h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Selecciona un Delivery Note, captura firma digital en pantalla y toma foto del sello con camara trasera obligatoria.
            </p>
          </div>
        </div>

        <button
          type="button"
          @click="loadEntregas"
          :disabled="loading"
          class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 disabled:opacity-40 transition flex items-center justify-center gap-2"
        >
          <RefreshCcw :size="18" />
          Actualiser
        </button>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      {{ errorMessage }}
    </div>

    <div v-if="successMessage" class="rounded-md border border-green-200 bg-green-50 p-5 text-sm text-green-700 flex items-start gap-2">
      <CheckCircle2 :size="18" class="mt-0.5 shrink-0" />
      <span>{{ successMessage }}</span>
    </div>

    <div v-if="loading" class="kiosk-panel rounded-md p-5">
      <div class="animate-pulse space-y-3">
        <div class="h-5 w-56 rounded-md bg-zinc-200"></div>
        <div class="h-4 w-40 rounded-md bg-zinc-200"></div>
        <div class="h-16 rounded-md bg-zinc-200"></div>
      </div>
    </div>

    <EmptyState
      v-else-if="!entregas.length"
      :icon="Truck"
      title="Aucune livraison en attente"
      message="Le camion est vide ou toutes les livraisons sont deja cloturees."
    />

    <div v-else class="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
      <div class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="gcma-section-label">Delivery Notes</div>
        <div class="mt-4 space-y-3">
          <button
            v-for="row in entregas"
            :key="row.name"
            type="button"
            @click="pickEntrega(row)"
            :class="selectedEntrega?.name === row.name ? 'border-blue-600 bg-blue-50' : 'border-zinc-200 bg-white'"
            class="gcma-data-row w-full rounded-md border p-4 text-left transition"
          >
            <div class="text-lg font-black text-zinc-900">{{ row.name }}</div>
            <div class="mt-1 text-sm text-zinc-500">{{ row.customer }}</div>
            <div class="mt-1 text-xs text-zinc-400">{{ row.posting_date }} · {{ row.status }}</div>
          </button>
        </div>
      </div>

      <div class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div>
          <div class="gcma-section-label">Capture POD</div>
          <div class="mt-1 text-lg font-bold text-zinc-900">
            {{ hasEntrega ? selectedEntrega.name : 'Selecciona una entrega' }}
          </div>
        </div>

        <div class="space-y-2">
          <label class="gcma-section-label">Firma digital (canvas)</label>
          <canvas
            ref="canvasRef"
            width="640"
            height="220"
            class="w-full rounded-md border border-zinc-300 bg-white touch-none"
            @mousedown="startDraw"
            @mousemove="moveDraw"
            @mouseup="endDraw"
            @mouseleave="endDraw"
            @touchstart.prevent="startDraw"
            @touchmove.prevent="moveDraw"
            @touchend.prevent="endDraw"
          />
          <button
            type="button"
            class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-600 active:bg-zinc-50"
            @click="clearCanvas"
          >
            Nettoyer signature
          </button>
        </div>

        <div class="space-y-2">
          <label class="gcma-section-label">Photo sello/fachada</label>
          <label class="flex h-16 cursor-pointer items-center justify-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100">
            <Camera :size="18" />
            Prendre photo
            <input
              type="file"
              class="hidden"
              accept="image/jpeg, image/png"
              capture="environment"
              @change="onPickPhoto"
            />
          </label>
          <p class="text-xs text-zinc-500">
            {{ fotoFile ? `Fichier: ${fotoFile.name}` : 'Aucune photo capturee.' }}
          </p>
        </div>

        <button
          type="button"
          :disabled="!hasEntrega || !fotoFile || submitting"
          @click="submitPod"
          class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
        >
          <PenSquare :size="18" />
          {{ submitting ? 'Enregistrement...' : 'Valider POD' }}
        </button>
      </div>
    </div>
  </KioskLayout>
</template>
