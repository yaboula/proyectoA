<template>
  <div class="min-h-dvh select-none px-5 py-5 text-zinc-50">
    <section class="mx-auto flex min-h-[calc(100dvh-2.5rem)] flex-col gap-5"
             :class="maxWidthClass">
      <slot />
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  maxWidth: { type: String, default: '7xl' },
})

const maxWidthClass = computed(() => `max-w-${props.maxWidth}`)
</script>
