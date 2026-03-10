<template>
  <div class="kiosk-panel flex flex-col items-center justify-center rounded-md py-28 gap-4"
       :class="containerClass">
    <component :is="icon" :size="56" :stroke-width="1.5" :class="iconClass" />
    <p class="text-lg font-semibold text-center" :class="titleClass">{{ title }}</p>
    <p v-if="message" class="text-sm text-zinc-500 text-center max-w-xl">{{ message }}</p>
    <slot name="action" />
  </div>
</template>

<script setup>
import { ClipboardList } from 'lucide-vue-next'

defineProps({
  icon: { type: [Object, Function], default: () => ClipboardList },
  title: { type: String, default: 'Aucun élément.' },
  message: { type: String, default: '' },
  iconClass: { type: String, default: 'text-zinc-400' },
  titleClass: { type: String, default: 'text-zinc-600' },
  containerClass: { type: String, default: '' },
})
</script>
