<script setup>
/**
 * TareasList — Liste des ordres de fabrication (EP2).
 *
 * Affiche les Work Orders pendantes sous forme de cartes géantes
 * optimisées pour écran tactile industriel (gants, pas de clavier).
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas } from '../api/kiosco'

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
  <div class="min-h-dvh bg-slate-100 flex flex-col">
    <!-- ═══ Header ═══ -->
    <header class="bg-blue-900 text-white px-6 py-5 flex items-center justify-between shadow-lg">
      <div class="min-w-0">
        <h1 class="text-2xl font-bold tracking-tight truncate">Ordres de Fabrication</h1>
        <p class="text-blue-300 text-base mt-0.5">
          {{ store.fullName }} · {{ store.operario?.company_abbr }}
        </p>
      </div>
      <div class="flex gap-3 shrink-0">
        <button @click="fetchTareas"
                :disabled="loading"
                class="rounded-xl bg-blue-800 px-5 py-3 text-lg font-bold
                       active:bg-blue-700 disabled:opacity-40 transition">
          ↻
        </button>
        <button @click="logout"
                class="rounded-xl bg-blue-800 px-5 py-3 text-base font-semibold
                       active:bg-blue-700 transition">
          Déconnexion
        </button>
      </div>
    </header>

    <!-- ═══ Content ═══ -->
    <main class="flex-1 p-5 space-y-5 overflow-y-auto">

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-24 gap-4">
        <svg class="h-14 w-14 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10"
                  stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="text-slate-500 text-lg">Chargement…</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="flex flex-col items-center justify-center py-24 gap-5">
        <p class="text-red-600 text-xl font-bold text-center">{{ error }}</p>
        <button @click="fetchTareas"
                class="rounded-2xl bg-blue-700 text-white px-8 py-4 text-lg font-bold
                       active:bg-blue-800 transition">
          Réessayer
        </button>
      </div>

      <!-- Empty -->
      <div v-else-if="tareas.length === 0"
           class="flex flex-col items-center justify-center py-24 gap-4">
        <p class="text-slate-400 text-6xl">📋</p>
        <p class="text-slate-500 text-xl font-semibold text-center">
          Aucun ordre de fabrication en attente.
        </p>
      </div>

      <!-- ═══ Cards ═══ -->
      <div v-for="t in tareas" :key="t.work_order"
           class="rounded-3xl bg-white shadow-lg overflow-hidden">

        <div class="p-6">
          <!-- Title + status badge -->
          <div class="flex items-start justify-between gap-3">
            <h2 class="text-2xl font-bold text-slate-900 leading-tight">
              {{ t.producto }}
            </h2>
            <span class="shrink-0 rounded-full px-4 py-1.5 text-sm font-bold whitespace-nowrap"
                  :class="t.estado === 'In Process'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-slate-100 text-slate-600'">
              {{ t.estado === 'In Process' ? 'En cours' : 'Non démarré' }}
            </span>
          </div>

          <!-- Quantity -->
          <div class="mt-4 flex items-baseline gap-2">
            <span class="text-5xl font-black text-blue-800">
              {{ t.cantidad_pendiente }}
            </span>
            <span class="text-xl text-slate-500">{{ t.uom }}</span>
            <span class="text-base text-slate-400 ml-1">à produire</span>
          </div>

          <!-- Materials summary bar -->
          <div class="mt-4 flex items-center gap-3 flex-wrap">
            <span class="text-base text-slate-600 font-medium">
              {{ t.materiales?.length ?? 0 }} matériaux
            </span>
            <span v-if="materialsReady(t)"
                  class="rounded-full bg-green-100 text-green-700 px-3 py-1 text-sm font-bold">
              ✓ Stock complet
            </span>
            <span v-else
                  class="rounded-full bg-amber-100 text-amber-700 px-3 py-1 text-sm font-bold">
              ⚠ Stock insuffisant
            </span>
          </div>
        </div>

        <!-- Big action button -->
        <button @click="startProduction(t.work_order)"
                class="w-full py-5 bg-green-600 text-white text-xl font-black tracking-wide
                       active:bg-green-700 transition-colors">
          DÉMARRER LA PRODUCTION ▶
        </button>
      </div>
    </main>
  </div>
</template>
