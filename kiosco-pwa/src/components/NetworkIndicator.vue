<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { WifiOff } from 'lucide-vue-next'

const isOffline = ref(!navigator.onLine)

function updateOnlineStatus() {
  isOffline.value = !navigator.onLine
}

onMounted(() => {
  window.addEventListener('online', updateOnlineStatus)
  window.addEventListener('offline', updateOnlineStatus)
})

onUnmounted(() => {
  window.removeEventListener('online', updateOnlineStatus)
  window.removeEventListener('offline', updateOnlineStatus)
})
</script>

<template>
  <div v-if="isOffline" class="fixed top-0 left-0 right-0 z-[100] bg-red-600 text-white shadow-md animate-fade-in-down">
    <div class="mx-auto flex max-w-7xl items-center justify-center gap-3 px-4 py-2 text-sm font-bold tracking-wide sm:text-base">
      <WifiOff :size="18" class="animate-pulse" />
      <span>HORS LIGNE — Connexion reseau perdue</span>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-down {
  animation: fadeInDown 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeInDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
</style>
