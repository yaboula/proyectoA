<template>
  <Teleport to="body">
    <div v-if="open"
         class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fade-in"
         @click.self="$emit('close')">
      <div class="w-full max-w-md mx-6 bg-white border border-zinc-200 rounded-md shadow-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-zinc-900">{{ title }}</h2>
          <button @click="$emit('close')"
                  class="w-10 h-10 flex items-center justify-center rounded-md
                         text-zinc-400 hover:bg-zinc-100 transition">
            <X :size="20" />
          </button>
        </div>

        <p v-if="description" class="text-sm text-zinc-500 mb-4">{{ description }}</p>

        <input ref="inputRef"
               :value="modelValue"
               @input="$emit('update:modelValue', $event.target.value)"
               type="text"
               inputmode="text"
               autocomplete="off"
               class="w-full h-16 px-4 text-xl font-mono text-zinc-900
                      bg-zinc-50 border border-zinc-300 rounded-md
                      focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20
                      placeholder:text-zinc-400"
               :placeholder="placeholder"
               @keydown.enter.prevent="submit" />

        <div class="mt-6 flex gap-3">
          <button @click="$emit('close')"
                  class="flex-1 h-14 rounded-md border border-zinc-300 bg-white
                         text-zinc-600 text-base font-semibold
                         active:bg-zinc-50 transition">
            Annuler
          </button>
          <button @click="submit"
                  :disabled="!isValid"
                  class="flex-1 h-14 rounded-md bg-blue-600 text-white text-base font-bold
                         flex items-center justify-center gap-2
                         active:bg-blue-700 disabled:opacity-40 transition">
            Valider
            <ChevronRight :size="20" />
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { X, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },
  title: { type: String, default: 'Saisie manuelle' },
  description: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  minLength: { type: Number, default: 5 },
})

const emit = defineEmits(['update:modelValue', 'close', 'submit'])

const inputRef = ref(null)
const isValid = computed(() => (props.modelValue ?? '').trim().length >= props.minLength)

watch(() => props.open, (open) => {
  if (open) nextTick(() => inputRef.value?.focus())
})

function submit() {
  if (!isValid.value) return
  emit('submit', props.modelValue.trim())
}
</script>
