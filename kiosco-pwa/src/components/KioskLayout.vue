<template>
  <div class="min-h-dvh select-none px-3 py-3 text-zinc-900 sm:px-5 sm:py-5">
    <section class="mx-auto flex min-h-[calc(100dvh-1.5rem)] flex-col gap-4 sm:min-h-[calc(100dvh-2.5rem)] sm:gap-5"
             :class="maxWidthClass">
      <slot />
    </section>
  </div>
</template>

<script setup>
const props = defineProps({
  maxWidth: { type: String, default: '7xl' },
})

const widthMap = {
  '5xl': 'max-w-5xl',
  '6xl': 'max-w-6xl',
  '7xl': 'max-w-7xl',
}

const maxWidthClass = widthMap[props.maxWidth] ?? 'max-w-7xl'
</script>
