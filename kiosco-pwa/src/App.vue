<template>
  <div class="app-shell gcma-theme-light min-h-dvh text-zinc-900">
    <RouterView />
    <Toast position="top-right" />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
</script>
