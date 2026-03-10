<template>
  <div class="gcma-theme-dark min-h-dvh bg-[radial-gradient(circle_at_top_left,_rgba(13,148,136,0.12),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(249,115,22,0.14),_transparent_26%),linear-gradient(180deg,_#061318_0%,_#091922_52%,_#050b10_100%)] text-slate-100">
    <RouterView />
    <Toast position="top-right" />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
</script>
