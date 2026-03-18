<script setup>
import { ref } from 'vue'
import { KeyRound, Loader2, ShieldCheck, TriangleAlert } from 'lucide-vue-next'

const props = defineProps({
  itemCode: { type: String, required: true },
  batchFefo: { type: String, default: null },       // lote que debería usarse
  batchRequested: { type: String, required: true }, // lote que el operario escaneó
})

const emit = defineEmits(['confirm', 'cancel'])

const pin = ref('')
const justificacion = ref('')
const loading = ref(false)
const pinError = ref('')

function onCancel() {
  pin.value = ''
  justificacion.value = ''
  pinError.value = ''
  emit('cancel')
}

async function onConfirm() {
  if (!pin.value.trim()) {
    pinError.value = 'Le PIN encadrant est obligatoire.'
    return
  }
  loading.value = true
  pinError.value = ''
  try {
    emit('confirm', {
      pin_manager: pin.value.trim(),
      justificacion: justificacion.value.trim(),
    })
  } finally {
    loading.value = false
    pin.value = ''
    justificacion.value = ''
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 flex items-end justify-center bg-black/50 px-4 pb-6 sm:items-center">
      <div class="w-full max-w-md animate-fade-in rounded-md border border-zinc-200 bg-white shadow-xl">

        <!-- Cabecera -->
        <div class="flex items-start gap-3 rounded-t-md border-b border-amber-200 bg-amber-50 px-5 py-4">
          <TriangleAlert :size="22" class="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <div class="text-sm font-black uppercase tracking-[0.18em] text-amber-700">
              Override FEFO requis
            </div>
            <p class="mt-1 text-xs leading-5 text-amber-700">
              Le lot <span class="font-mono font-bold">{{ batchRequested }}</span>
              n'est pas le plus ancien.
              <template v-if="batchFefo">
                Le lot attendu est <span class="font-mono font-bold">{{ batchFefo }}</span>.
              </template>
              Un encadrant doit autoriser ce remplacement.
            </p>
          </div>
        </div>

        <!-- Cuerpo -->
        <div class="space-y-4 p-5">
          <!-- Item info -->
          <div class="gcma-data-row p-3 text-sm">
            <div class="gcma-section-label">Article concerné</div>
            <div class="mt-1 font-mono font-bold text-zinc-800">{{ itemCode }}</div>
          </div>

          <!-- PIN -->
          <label class="block space-y-2">
            <span class="gcma-section-label flex items-center gap-1.5">
              <KeyRound :size="12" />
              PIN encadrant
            </span>
            <input
              v-model="pin"
              type="password"
              inputmode="numeric"
              autocomplete="off"
              maxlength="8"
              class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-center text-2xl font-mono tracking-[0.4em] text-zinc-900 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/25"
              placeholder="••••"
              @keydown.enter.prevent="onConfirm"
            />
            <p v-if="pinError" class="text-xs font-semibold text-red-600">{{ pinError }}</p>
          </label>

          <!-- Justificación opcional -->
          <label class="block space-y-2">
            <span class="gcma-section-label">Justification (optionnel)</span>
            <input
              v-model="justificacion"
              type="text"
              autocomplete="off"
              maxlength="120"
              class="w-full rounded-md border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/25"
              placeholder="Ex: lot FEFO introuvable en rayon"
            />
          </label>
        </div>

        <!-- Acciones -->
        <div class="flex gap-3 border-t border-zinc-200 px-5 py-4">
          <button
            type="button"
            class="h-12 flex-1 rounded-md border border-zinc-300 bg-white text-sm font-bold text-zinc-500 active:bg-zinc-50"
            @click="onCancel"
          >
            Annuler
          </button>
          <button
            type="button"
            :disabled="!pin.trim() || loading"
            class="h-16 flex-[2] rounded-md bg-amber-500 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-amber-600 disabled:opacity-40 transition flex items-center justify-center gap-2"
            @click="onConfirm"
          >
            <Loader2 v-if="loading" :size="18" class="animate-spin" />
            <ShieldCheck v-else :size="18" />
            {{ loading ? 'Validation...' : 'Autoriser override' }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>
