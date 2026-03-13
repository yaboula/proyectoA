<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-5"
      @click.self="emit('close')"
    >
      <div class="w-full max-w-md rounded-md border border-zinc-200 bg-white shadow-xl animate-fade-in">
        <div class="flex items-center justify-between border-b border-zinc-200 px-6 py-5">
          <div>
            <div class="gcma-section-label">Visite client</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900">Check-In GPS</h2>
          </div>
          <button
            type="button"
            @click="emit('close')"
            class="flex h-12 w-12 items-center justify-center rounded-md border border-zinc-300 bg-white text-zinc-500 active:bg-zinc-50"
          >
            <X :size="20" />
          </button>
        </div>

        <div class="space-y-4 px-6 py-6">
          <div class="gcma-data-row p-4">
            <div class="gcma-section-label">Client</div>
            <div class="mt-1 text-lg font-bold text-zinc-900">{{ clientName }}</div>
          </div>

          <div class="kiosk-panel-soft rounded-md p-4 text-sm text-zinc-600">
            <p class="font-semibold text-zinc-800">Autorisation GPS obligatoire</p>
            <p class="mt-1">Sans geolocalisation, le check-in n'est pas autorise.</p>
          </div>

          <div class="space-y-2">
            <button
              type="button"
              @click="resolvePosition"
              :disabled="resolving"
              class="h-16 w-full rounded-md border border-blue-200 bg-blue-50 text-sm font-black uppercase tracking-[0.16em] text-blue-700 active:bg-blue-100 disabled:opacity-40"
            >
              {{ resolving ? 'Lecture GPS...' : 'Autoriser et localiser' }}
            </button>

            <div v-if="positionLabel" class="rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-500">
              {{ positionLabel }}
            </div>
          </div>

          <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {{ errorMessage }}
          </p>
        </div>

        <div class="flex gap-3 border-t border-zinc-200 px-6 py-5">
          <button
            type="button"
            @click="emit('close')"
            class="h-12 flex-1 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-600 active:bg-zinc-50"
          >
            Annuler
          </button>
          <button
            type="button"
            @click="submit"
            :disabled="submitting || !coords"
            class="h-16 flex-1 rounded-md bg-blue-600 px-4 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40"
          >
            {{ submitting ? 'Envoi...' : 'Valider Check-In' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  clientName: { type: String, default: '' },
  submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])

const resolving = ref(false)
const coords = ref(null)
const errorMessage = ref('')

const positionLabel = computed(() => {
  if (!coords.value) return ''
  return `Lat: ${coords.value.lat.toFixed(6)} · Lng: ${coords.value.lng.toFixed(6)}`
})

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      coords.value = null
      errorMessage.value = ''
      resolving.value = false
    }
  },
  { immediate: true },
)

function resolvePosition() {
  errorMessage.value = ''

  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    errorMessage.value = 'Geolocalisation indisponible sur cet appareil.'
    return
  }

  resolving.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      resolving.value = false
      coords.value = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      }
    },
    (error) => {
      resolving.value = false
      if (error?.code === 1) {
        errorMessage.value = 'Permission GPS refusee. Check-In bloque.'
        return
      }
      errorMessage.value = 'Impossible d\'obtenir la position GPS actuelle.'
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    },
  )
}

function submit() {
  if (!coords.value || props.submitting) return

  emit('submit', {
    gps_lat_capturada: coords.value.lat,
    gps_lng_capturada: coords.value.lng,
    timestamp: new Date().toISOString(),
  })
}
</script>
