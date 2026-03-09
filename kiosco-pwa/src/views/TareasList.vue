<script setup>
/**
 * TareasList — Liste des ordres de fabrication (EP2).
 *
 * Design System: thème industriel premium. Cards shadcn-style.
 * Icônes: lucide-vue-next. Boutons ≥ h-16. rounded-md max.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas } from '../api/kiosco'
import {
  Play,
  RefreshCw,
  LogOut,
  Loader2,
  PackageCheck,
  TriangleAlert,
  ClipboardList,
  Beaker,
  Clock,
  CircleAlert,
} from 'lucide-vue-next'

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
  <div class="min-h-dvh bg-slate-900 flex flex-col select-none">

    <!-- ═══ Header ═══ -->
    <header class="bg-slate-800/80 border-b border-slate-700/50 px-5 py-4
                    flex items-center justify-between">
      <div class="min-w-0">
        <h1 class="text-xl font-bold tracking-wide text-slate-100 uppercase truncate">
          Ordres de Fabrication
        </h1>
        <p class="text-sm text-slate-500 mt-0.5 truncate">
          {{ store.fullName }} · {{ store.operario?.company_abbr }}
        </p>
      </div>
      <div class="flex gap-2 shrink-0">
        <button @click="fetchTareas"
                :disabled="loading"
                class="h-12 w-12 flex items-center justify-center rounded-md
                       border border-slate-700 bg-slate-800
                       text-slate-400 active:bg-slate-700 disabled:opacity-30 transition">
          <RefreshCw :size="20" :class="{ 'animate-spin': loading }" />
        </button>
        <button @click="logout"
                class="h-12 px-4 flex items-center gap-2 rounded-md
                       border border-slate-700 bg-slate-800
                       text-slate-400 text-sm font-semibold
                       active:bg-slate-700 transition">
          <LogOut :size="18" />
          Quitter
        </button>
      </div>
    </header>

    <!-- ═══ Content ═══ -->
    <main class="flex-1 p-4 space-y-4 overflow-y-auto">

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-28 gap-4">
        <Loader2 :size="48" :stroke-width="2" class="text-slate-500 animate-spin" />
        <p class="text-slate-500 text-base">Chargement des ordres…</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="flex flex-col items-center justify-center py-28 gap-5">
        <CircleAlert :size="56" :stroke-width="1.5" class="text-rose-500" />
        <p class="text-rose-400 text-lg font-bold text-center">{{ error }}</p>
        <button @click="fetchTareas"
                class="h-14 px-8 rounded-md bg-slate-800 border border-slate-700
                       text-slate-200 text-base font-semibold
                       active:bg-slate-700 transition">
          Réessayer
        </button>
      </div>

      <!-- Empty -->
      <div v-else-if="tareas.length === 0"
           class="flex flex-col items-center justify-center py-28 gap-4">
        <ClipboardList :size="56" :stroke-width="1.5" class="text-slate-600" />
        <p class="text-slate-500 text-lg font-semibold text-center">
          Aucun ordre de fabrication en attente.
        </p>
      </div>

      <!-- ═══ Cards ═══ -->
      <div v-for="t in tareas" :key="t.work_order"
           class="bg-slate-800 border border-slate-700/60 rounded-md overflow-hidden">

        <div class="p-5">
          <!-- Top row: status + WO id -->
          <div class="flex items-center justify-between gap-3 mb-3">
            <span class="flex items-center gap-1.5 text-xs font-mono text-slate-500 uppercase">
              <Beaker :size="14" />
              {{ t.work_order }}
            </span>
            <span class="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold"
                  :class="t.estado === 'In Process'
                    ? 'bg-amber-900/40 text-amber-400 border border-amber-700/50'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/50'">
              <Clock :size="12" />
              {{ t.estado === 'In Process' ? 'En cours' : 'Non démarré' }}
            </span>
          </div>

          <!-- Product name -->
          <h2 class="text-2xl font-bold text-slate-100 leading-tight">
            {{ t.producto }}
          </h2>

          <!-- Quantity -->
          <div class="mt-3 flex items-baseline gap-2">
            <span class="text-4xl font-black text-emerald-400">
              {{ t.cantidad_pendiente }}
            </span>
            <span class="text-lg text-slate-400">{{ t.uom }}</span>
            <span class="text-sm text-slate-600 ml-1">à produire</span>
          </div>

          <!-- Materials pills -->
          <div class="mt-4 flex items-center gap-2 flex-wrap">
            <span class="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold
                         bg-slate-700/60 text-slate-300 border border-slate-600/50">
              {{ t.materiales?.length ?? 0 }} matériaux
            </span>
            <span v-if="materialsReady(t)"
                  class="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold
                         bg-emerald-900/30 text-emerald-400 border border-emerald-700/50">
              <PackageCheck :size="13" />
              Stock complet
            </span>
            <span v-else
                  class="flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold
                         bg-amber-900/30 text-amber-400 border border-amber-700/50">
              <TriangleAlert :size="13" />
              Stock insuffisant
            </span>
          </div>
        </div>

        <!-- Big action button — masive touch area -->
        <button @click="startProduction(t.work_order)"
                class="w-full h-16 flex items-center justify-center gap-3
                       bg-emerald-600 text-white text-lg font-black tracking-wide
                       active:bg-emerald-700 transition-colors border-t border-emerald-500/30">
          <Play :size="24" :stroke-width="2.5" />
          DÉMARRER LA PRODUCTION
        </button>
      </div>
    </main>
  </div>
</template>
