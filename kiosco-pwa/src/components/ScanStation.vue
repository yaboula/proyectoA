<template>
  <div class="flex flex-col items-center gap-5 rounded-md border bg-zinc-950/72 px-5 text-center transition-all duration-300"
       :class="[sizeClasses, borderClass]">
    <div class="flex items-center justify-center rounded-md border-2 bg-zinc-900 transition-all duration-300"
         :class="[iconBoxClass, borderClass]">
      <ScanBarcode v-if="status === 'idle'" :size="iconSize" :stroke-width="1.5" class="text-zinc-400" />
      <ScanBarcode v-else-if="status === 'scanning'" :size="iconSize" :stroke-width="1.5" class="text-emerald-400 animate-pulse" />
      <Loader2 v-else-if="status === 'loading'" :size="iconSize" :stroke-width="2" class="text-amber-400 animate-spin" />
      <CircleCheckBig v-else-if="status === 'success'" :size="iconSize" :stroke-width="1.5" class="text-emerald-400" />
      <CircleX v-else :size="iconSize" :stroke-width="1.5" class="text-rose-400" />
    </div>

    <div class="space-y-2">
      <div v-if="status === 'success' && successLabel" class="text-3xl font-black tracking-tight text-emerald-400">
        {{ successLabel }}
      </div>
      <p class="max-w-lg text-xl font-semibold leading-relaxed transition-colors duration-200"
         :class="messageColorClass">
        {{ message }}
      </p>
      <p v-if="hint" class="text-sm text-zinc-500">{{ hint }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ScanBarcode, Loader2, CircleCheckBig, CircleX } from 'lucide-vue-next'

const props = defineProps({
  status: { type: String, default: 'idle', validator: v => ['idle', 'scanning', 'loading', 'success', 'error'].includes(v) },
  message: { type: String, default: '' },
  hint: { type: String, default: '' },
  successLabel: { type: String, default: '' },
  size: { type: String, default: 'lg', validator: v => ['md', 'lg'].includes(v) },
})

const iconSize = computed(() => props.size === 'lg' ? 64 : 44)
const iconBoxClass = computed(() => props.size === 'lg' ? 'h-32 w-32' : 'h-28 w-28')
const sizeClasses = computed(() => props.size === 'lg' ? 'px-6 py-10 border-zinc-800' : 'px-5 py-8 border-zinc-800')

const borderClass = computed(() => ({
  'border-zinc-800': props.status === 'idle',
  'border-emerald-500 animate-pulse-ring': props.status === 'scanning',
  'border-amber-500': props.status === 'loading',
  'border-emerald-400': props.status === 'success',
  'border-rose-500': props.status === 'error',
}))

const messageColorClass = computed(() => ({
  'text-zinc-400': props.status === 'idle',
  'text-emerald-300': props.status === 'scanning' || props.status === 'success',
  'text-amber-300': props.status === 'loading',
  'text-rose-400': props.status === 'error',
}))
</script>
