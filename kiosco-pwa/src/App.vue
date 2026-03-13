<template>
  <div class="app-shell gcma-theme-light min-h-dvh text-zinc-900">
    <NetworkIndicator />
    <RouterView />
    <Toast position="top-right" />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import NetworkIndicator from './components/NetworkIndicator.vue'
</script>
