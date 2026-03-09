<script setup>
/**
 * TareasList — Liste des ordres de fabrication.
 * Stub — sera complété lors de l'implémentation de l'écran EP2.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas } from '../api/kiosco'

const router = useRouter()
const store = useOperarioStore()
const tareas = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await getTareas()
    tareas.value = data.tareas ?? []
  } catch {
    tareas.value = []
  } finally {
    loading.value = false
  }
})

function selectTarea(wo) {
  router.push({ name: 'poka-yoke', params: { workOrder: wo } })
}

function logout() {
  store.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-dvh bg-slate-100 flex flex-col">
    <!-- Header -->
    <header class="bg-sky-800 text-white px-6 py-4 flex items-center justify-between shadow">
      <div>
        <h1 class="text-xl font-bold">Ordres de Fabrication</h1>
        <p class="text-sm text-sky-200">{{ store.fullName }}</p>
      </div>
      <button @click="logout"
              class="rounded-xl bg-sky-700 px-5 py-3 text-base font-semibold active:bg-sky-600 transition">
        Déconnexion
      </button>
    </header>

    <!-- Content -->
    <main class="flex-1 p-4 space-y-4 overflow-y-auto">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <svg class="h-12 w-12 text-sky-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <p v-else-if="tareas.length === 0" class="text-center text-slate-500 text-lg py-20">
        Aucun ordre de fabrication en attente.
      </p>

      <button v-for="t in tareas" :key="t.work_order"
              @click="selectTarea(t.work_order)"
              class="w-full rounded-2xl bg-white shadow p-5 text-left active:bg-slate-50 transition">
        <p class="text-lg font-bold text-slate-800">{{ t.producto }}</p>
        <p class="text-sm text-slate-500 mt-1">
          {{ t.work_order }} · {{ t.cantidad }} {{ t.uom }}
        </p>
        <div class="mt-3 flex items-center gap-2">
          <span class="inline-block rounded-full px-3 py-1 text-xs font-semibold"
                :class="t.estado === 'In Process' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-600'">
            {{ t.estado === 'In Process' ? 'En cours' : 'Non démarré' }}
          </span>
          <span class="text-xs text-slate-400">{{ t.materiales?.length ?? 0 }} matériaux</span>
        </div>
      </button>
    </main>
  </div>
</template>
