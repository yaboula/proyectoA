<script setup>
/**
 * TareasList -- Liste des ordres de fabrication (EP2).
 *
 * Refactored: KioskLayout, EmptyState.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import { getTareas } from '../api/kiosco'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
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
  FlaskConical,
  LayoutDashboard,
} from 'lucide-vue-next'

const router = useRouter()
const store = useOperarioStore()
const tareas = ref([])
const loading = ref(true)
const error = ref(null)

async function fetchTareas() {
  const hasSession = await store.ensureSession()
  if (!hasSession || !store.operario?.company) {
    router.push({ name: 'login' })
    return
  }

  loading.value = true
  error.value = null
  try {
    const data = await getTareas(store.operario.company, store.operario.default_warehouse)
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
  store.logout().finally(() => { router.push({ name: 'login' }) })
}
</script>

<template>
  <KioskLayout>
    <header class="kiosk-panel rounded-md px-6 py-5">
      <div class="gcma-toolbar">
        <div class="min-w-0">
          <div class="gcma-section-label">Pilotage atelier</div>
          <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Ordres de fabrication</h1>
          <p class="mt-2 text-sm text-zinc-500 truncate">
            {{ store.fullName }} &middot; {{ store.operario?.company_abbr }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2 shrink-0">
          <button @click="router.push({ name: 'hub' })"
                  class="h-12 px-4 flex items-center gap-2 rounded-md border border-zinc-300 bg-white text-zinc-700 text-sm font-semibold active:bg-zinc-50 transition">
            <LayoutDashboard :size="18" />
            Modules
          </button>
          <button v-if="store.hasModule('quality')" @click="router.push({ name: 'laboratoire' })"
                  class="h-12 px-4 flex items-center gap-2 rounded-md border border-zinc-300 bg-white text-zinc-600 text-sm font-semibold active:bg-zinc-50 transition">
            <FlaskConical :size="18" />
            Laboratoire
          </button>
          <button @click="fetchTareas"
                  :disabled="loading"
                  class="h-12 w-12 flex items-center justify-center rounded-md border border-zinc-300 bg-white text-zinc-500 active:bg-zinc-50 disabled:opacity-30 transition">
            <RefreshCw :size="20" :class="{ 'animate-spin': loading }" />
          </button>
          <button @click="logout"
                  class="h-12 px-4 flex items-center gap-2 rounded-md border border-zinc-300 bg-white text-zinc-500 text-sm font-semibold active:bg-zinc-50 transition">
            <LogOut :size="18" />
            Quitter
          </button>
        </div>
      </div>

      <div class="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-3 text-sm text-zinc-500">
        <div class="gcma-stat">
          <div class="gcma-section-label">Site</div>
          <div class="mt-1 font-semibold text-zinc-900">{{ store.operario?.company }}</div>
        </div>
        <div class="gcma-stat">
          <div class="gcma-section-label">Profil</div>
          <div class="mt-1 font-semibold text-zinc-900">{{ store.profileLabel }}</div>
        </div>
        <div class="gcma-stat">
          <div class="gcma-section-label">Ordres visibles</div>
          <div class="mt-1 font-semibold text-zinc-900">{{ tareas.length }}</div>
        </div>
      </div>
    </header>

    <main class="flex-1 space-y-4 overflow-y-auto">
      <!-- Loading -->
      <div v-if="loading" class="kiosk-panel flex flex-col items-center justify-center rounded-md py-28 gap-4">
        <Loader2 :size="48" :stroke-width="2" class="text-blue-600 animate-spin" />
        <p class="text-zinc-500 text-base">Chargement des ordres...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="kiosk-panel flex flex-col items-center justify-center rounded-md py-28 gap-5">
        <CircleAlert :size="56" :stroke-width="1.5" class="text-red-500" />
        <p class="text-red-600 text-lg font-bold text-center">{{ error }}</p>
        <button @click="fetchTareas"
                class="h-16 px-8 rounded-md bg-blue-600 text-white text-base font-semibold active:bg-blue-700 transition">
          Reessayer
        </button>
      </div>

      <!-- Empty -->
      <EmptyState
        v-else-if="tareas.length === 0"
        :icon="ClipboardList"
        title="Aucun ordre de fabrication en attente."
      />

      <!-- Cards -->
      <div v-else class="grid gap-4">
        <article v-for="t in tareas" :key="t.work_order" class="kiosk-panel overflow-hidden rounded-md">
          <div class="grid gap-4 p-4 sm:p-5 lg:grid-cols-[1.2fr_0.9fr_auto] lg:items-center">
            <div class="space-y-4">
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-1.5 text-xs font-mono uppercase tracking-[0.18em] text-zinc-500">
                  <Beaker :size="14" />
                  {{ t.work_order }}
                </span>
                <span class="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold"
                      :class="t.estado === 'In Process'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-zinc-100 text-zinc-500 border border-zinc-200'">
                  <Clock :size="12" />
                  {{ t.estado === 'In Process' ? 'En cours' : 'Non demarre' }}
                </span>
              </div>

              <div>
                <h2 class="text-2xl font-black leading-tight text-zinc-900">{{ t.producto }}</h2>
                <div class="mt-3 flex items-baseline gap-2">
                  <span class="text-3xl font-black text-zinc-900 sm:text-4xl">{{ t.cantidad_pendiente }}</span>
                  <span class="text-lg text-zinc-500">{{ t.uom }}</span>
                  <span class="text-sm text-zinc-400 ml-1">a produire</span>
                </div>
              </div>
            </div>

            <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
              <div class="gcma-stat">
                <div class="gcma-section-label">Disponibilite matiere</div>
                <div class="mt-2 flex items-center gap-2 text-sm font-bold"
                     :class="materialsReady(t) ? 'text-green-700' : 'text-amber-600'">
                  <PackageCheck v-if="materialsReady(t)" :size="16" />
                  <TriangleAlert v-else :size="16" />
                  {{ materialsReady(t) ? 'Stock complet' : 'Stock insuffisant' }}
                </div>
              </div>
              <div class="gcma-stat">
                <div class="gcma-section-label">Composition</div>
                <div class="mt-2 text-sm font-semibold text-zinc-900">{{ t.materiales?.length ?? 0 }} materiaux</div>
                <div class="mt-2 text-sm leading-6 text-zinc-500">
                  {{ (t.materiales ?? []).slice(0, 3).map((m) => m.item_name).join(' &middot; ') || 'N/A' }}
                </div>
              </div>
            </div>

            <div class="flex lg:justify-end">
              <button @click="startProduction(t.work_order)"
                      class="w-full h-16 rounded-md bg-blue-600 px-6 text-base font-black tracking-[0.12em] text-white active:bg-blue-700 transition-colors lg:w-auto lg:min-w-[16rem]">
                <span class="inline-flex items-center justify-center gap-3">
                  <Play :size="22" :stroke-width="2.5" />
                  DEMARRER LA PRODUCTION
                </span>
              </button>
            </div>
          </div>
        </article>
      </div>
    </main>
  </KioskLayout>
</template>
