<script setup>
/**
 * TareasList â€” Liste des ordres de fabrication (EP2).
 * UI industrielle avec PrimeVue + thÃ¨me sombre professionnel.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas } from '../api/kiosco'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Skeleton from 'primevue/skeleton'
import Message from 'primevue/message'

const router = useRouter()
const store = useOperarioStore()
const tareas = ref([])
const loading = ref(true)
const error = ref(null)

async function fetchTareas() {
  loading.value = true
  error.value = null
  try {
    const data = await getTareas(
      store.operario.company,
      store.operario.default_warehouse
    )
    tareas.value = data.tareas ?? []
  } catch (err) {
    error.value = err?.message_fr ?? 'Erreur de chargement des ordres.'
    tareas.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchTareas)

function materialsReady(t) {
  return t.materiales?.length > 0 && t.materiales.every(m => m.suficiente)
}

function startProduction(workOrder) {
  router.push({ name: 'poka-yoke', params: { workOrder } })
}

function logout() {
  store.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-dvh bg-[#080d1a] flex flex-col">

    <!-- â•® Top accent â•¯ -->
    <div class="h-[3px] bg-gradient-to-r from-transparent via-blue-500 to-transparent shrink-0"></div>

    <!-- â•® Header â•¯ -->
    <header class="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/40
                   px-5 py-4 flex items-center justify-between shrink-0">
      <div class="min-w-0">
        <h1 class="text-xl font-bold text-white tracking-tight truncate">Ordres de Fabrication</h1>
        <p class="text-slate-500 text-sm">
          {{ store.fullName }} Â·
          <span class="text-blue-400 font-medium">{{ store.operario?.company_abbr }}</span>
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <Button icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="loading"
                aria-label="RafraÃ®chir"
                @click="fetchTareas" />
        <Button label="DÃ©connexion"
                icon="pi pi-sign-out"
                severity="secondary"
                text
                class="!text-sm"
                @click="logout" />
      </div>
    </header>

    <!-- â•® Content â•¯ -->
    <main class="flex-1 overflow-y-auto p-4 space-y-4">

      <!-- Loading skeletons -->
      <template v-if="loading">
        <div v-for="n in 2" :key="n"
             class="rounded-2xl bg-slate-900/60 border border-slate-700/30 p-6 space-y-5">
          <div class="flex justify-between items-start">
            <Skeleton height="1.6rem" width="65%" />
            <Skeleton height="1.6rem" width="5rem" border-radius="9999px" />
          </div>
          <Skeleton height="4rem" width="45%" />
          <Skeleton height="1rem" width="55%" />
          <Skeleton height="3.5rem" border-radius="12px" />
        </div>
      </template>

      <!-- Error -->
      <Message v-else-if="error" severity="error" :closable="false" class="w-full">
        {{ error }}
      </Message>

      <!-- Empty -->
      <div v-else-if="tareas.length === 0"
           class="flex flex-col items-center justify-center py-24 gap-4">
        <i class="pi pi-inbox text-slate-700" style="font-size: 5rem"></i>
        <p class="text-slate-500 text-lg font-medium text-center leading-relaxed">
          Aucun ordre de fabrication<br>en attente.
        </p>
      </div>

      <!-- â•® Work Order Cards â•¯ -->
      <div v-for="t in tareas" :key="t.work_order"
           class="rounded-2xl bg-slate-900/60 border border-slate-700/30
                  overflow-hidden transition-shadow hover:shadow-lg hover:shadow-blue-900/20">

        <div class="p-6 space-y-5">

          <!-- Row 1: Product + status badge -->
          <div class="flex items-start gap-3">
            <h2 class="flex-1 text-xl font-bold text-white leading-tight min-w-0">
              {{ t.producto }}
            </h2>
            <Tag :severity="t.estado === 'In Process' ? 'warn' : 'secondary'"
                 :value="t.estado === 'In Process' ? 'â³ En cours' : 'â¸ En attente'"
                 class="shrink-0" />
          </div>

          <!-- Row 2: Giant quantity -->
          <div class="flex items-baseline gap-2">
            <span class="text-[3.5rem] leading-none font-black text-blue-400">
              {{ t.cantidad_pendiente }}
            </span>
            <span class="text-2xl text-slate-500 font-medium">{{ t.uom }}</span>
            <span class="text-slate-600 text-sm ml-1">Ã  produire</span>
          </div>

          <!-- Row 3: Materials readiness -->
          <div class="flex items-center gap-3 flex-wrap">
            <span class="text-slate-500 text-sm">
              <i class="pi pi-box mr-1.5"></i>{{ t.materiales?.length ?? 0 }} matÃ©riaux
            </span>
            <Tag v-if="materialsReady(t)"
                 severity="success"
                 value="âœ“ Stock complet"
                 class="text-xs" />
            <Tag v-else
                 severity="warn"
                 value="âš  Stock insuffisant"
                 class="text-xs" />
          </div>

          <!-- Work order ID -->
          <p class="text-slate-700 text-xs font-mono">{{ t.work_order }}</p>
        </div>

        <!-- â•® Action button (full-width footer) â•¯ -->
        <div class="border-t border-slate-700/30 p-4">
          <Button label="DÃ‰MARRER LA PRODUCTION"
                  icon="pi pi-play-circle"
                  icon-pos="right"
                  severity="success"
                  fluid
                  class="!py-5 !text-base !font-black !tracking-wider"
                  @click="startProduction(t.work_order)" />
        </div>
      </div>
    </main>
  </div>
</template>
