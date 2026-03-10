<template>
  <Teleport to="body">
    <div v-if="visible"
         class="fixed inset-0 z-50 flex flex-col items-center justify-center px-8 select-none"
         :class="[bgClass, clickable ? 'cursor-pointer' : '']"
         @click="clickable ? $emit('dismiss') : null">
      <!-- Icon -->
      <component :is="iconComponent" :size="80" :stroke-width="iconStroke" class="mb-6"
                 :class="[variant === 'loading' ? 'text-blue-600' : 'text-white',
                          { 'animate-spin': variant === 'loading', 'animate-shake': variant === 'error' && shake }]" />

      <!-- Title -->
      <p class="text-3xl font-black text-center leading-relaxed max-w-lg"
         :class="variant === 'loading' ? 'text-zinc-900' : 'text-white'">
        {{ title }}
      </p>

      <!-- Subtitle -->
      <p v-if="subtitle" class="mt-2 text-xl font-semibold text-center leading-relaxed"
         :class="subtitleClass">
        {{ subtitle }}
      </p>

      <!-- Alert slot (e.g. EP4 warning banner) -->
      <slot name="alert" />

      <!-- Footer hint -->
      <p v-if="hint" class="mt-10 text-sm font-medium tracking-wide" :class="hintClass">
        {{ hint }}
      </p>

      <!-- Action slot (e.g. retry button) -->
      <slot name="action" />
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { TriangleAlert, PackageCheck, CircleAlert, Loader2, CircleCheckBig } from 'lucide-vue-next'

const props = defineProps({
  visible: { type: Boolean, default: false },
  variant: { type: String, default: 'error', validator: v => ['error', 'success', 'loading', 'info'].includes(v) },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  hint: { type: String, default: '' },
  shake: { type: Boolean, default: true },
  clickable: { type: Boolean, default: false },
})

defineEmits(['dismiss'])

const iconComponent = computed(() => ({
  error: props.shake ? TriangleAlert : CircleAlert,
  success: PackageCheck,
  loading: Loader2,
  info: CircleCheckBig,
})[props.variant])

const iconStroke = computed(() => props.variant === 'loading' ? 2 : 1.5)

const bgClass = computed(() => ({
  error: 'bg-red-600',
  success: 'bg-green-600',
  loading: 'bg-white/95',
  info: 'bg-green-600',
})[props.variant])

const subtitleClass = computed(() => ({
  error: 'text-red-100',
  success: 'text-green-100',
  loading: 'text-zinc-500',
  info: 'text-green-100',
})[props.variant])

const hintClass = computed(() => ({
  error: 'text-red-200/70',
  success: 'text-green-200/60',
  loading: 'text-zinc-400',
  info: 'text-green-200/60',
})[props.variant])
</script>
