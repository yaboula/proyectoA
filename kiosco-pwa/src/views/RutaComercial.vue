<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Boxes,
  CheckCircle2,
  CircleAlert,
  CloudOff,
  MapPinned,
  Navigation,
  RefreshCcw,
  Route,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import CheckInModal from '../components/CheckInModal.vue'
import { useOperarioStore } from '../stores/operario'
import { useSyncQueueStore } from '../stores/syncQueue'
import { getRutaDia, postCheckin } from '../api/kiosco'

const router = useRouter()
const operarioStore = useOperarioStore()
const syncQueueStore = useSyncQueueStore()

const loading = ref(false)
const checkingIn = ref(false)
const errorMessage = ref('')
const routeData = ref({ id_ruta: '', estado: '', clientes: [] })
const selectedClient = ref(null)
const checkinOpen = ref(false)
const visitStatusByClient = ref({})

let syncInterval = null

function handleOnlineSync() {
  if (syncQueueStore.hasPending) {
    syncQueueStore.syncAll()
  }
}

const clientes = computed(() => routeData.value?.clientes ?? [])
const totalClientes = computed(() => clientes.value.length)
const visitados = computed(() => {
  return clientes.value.reduce((acc, cliente) => {
    const local = visitStatusByClient.value[cliente.id_cliente]
    if (local?.done || cliente.visitado) return acc + 1
    return acc
  }, 0)
})

const pendingSync = computed(() => syncQueueStore.pendingCount)

function setLocalStatus(idCliente, status) {
  visitStatusByClient.value = {
    ...visitStatusByClient.value,
    [idCliente]: {
      ...(visitStatusByClient.value[idCliente] ?? {}),
      ...status,
    },
  }
}

function openCheckin(cliente) {
  selectedClient.value = cliente
  checkinOpen.value = true
}

function closeCheckin() {
  if (checkingIn.value) return
  checkinOpen.value = false
  selectedClient.value = null
}

async function loadRuta() {
  loading.value = true
  errorMessage.value = ''

  try {
    const data = await getRutaDia()
    routeData.value = {
      id_ruta: data?.id_ruta ?? '',
      estado: data?.estado ?? 'Planificada',
      clientes: data?.clientes ?? [],
    }
  } catch (error) {
    errorMessage.value = error?.message_fr ?? 'Impossible de charger la feuille de route.'
    routeData.value = { id_ruta: '', estado: '', clientes: [] }
  } finally {
    loading.value = false
  }
}

async function submitCheckin(payload) {
  if (!selectedClient.value || checkingIn.value) return

  checkingIn.value = true
  errorMessage.value = ''

  const requestPayload = {
    id_cliente: selectedClient.value.id_cliente,
    gps_lat_capturada: payload.gps_lat_capturada,
    gps_lng_capturada: payload.gps_lng_capturada,
    timestamp: payload.timestamp,
  }

  try {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      throw new Error('NETWORK_OFFLINE')
    }

    const response = await postCheckin(requestPayload)
    const isFraude = Boolean(response?.es_fraude)

    setLocalStatus(selectedClient.value.id_cliente, {
      done: true,
      queued: false,
      fraude: isFraude,
      distancia_metros: response?.distancia_metros,
      message: isFraude
        ? `Visite observee (${response?.distancia_metros ?? '-'} m)`
        : `Check-In valide (${response?.distancia_metros ?? '-'} m)`,
    })

    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate(200)
    }

    closeCheckin()
  } catch (error) {
    const message = error?.message_fr ?? error?.message ?? ''
    const isOffline = message.includes('Network Error') || message.includes('NETWORK_OFFLINE')

    if (isOffline) {
      syncQueueStore.enqueueOperation('B2B_POST_CHECKIN', requestPayload, {
        id_cliente: selectedClient.value.id_cliente,
        nombre: selectedClient.value.nombre,
      })

      setLocalStatus(selectedClient.value.id_cliente, {
        done: true,
        queued: true,
        fraude: false,
        message: 'Check-In sauvegarde localement. En attente de synchronisation.',
      })

      closeCheckin()
    } else {
      errorMessage.value = error?.message_fr ?? 'Le check-in n\'a pas pu etre enregistre.'
    }
  } finally {
    checkingIn.value = false
  }
}

async function syncPendingQueue() {
  if (!navigator.onLine || pendingSync.value === 0) return
  await syncQueueStore.syncAll()
}

function statusFor(cliente) {
  return visitStatusByClient.value[cliente.id_cliente] ?? null
}

onMounted(async () => {
  const hasSession = await operarioStore.ensureSession()
  if (!hasSession) {
    router.replace({ name: 'login' })
    return
  }

  await loadRuta()
  window.addEventListener('online', handleOnlineSync)

  syncInterval = setInterval(() => {
    if (navigator.onLine && syncQueueStore.hasPending) {
      syncQueueStore.syncAll()
    }
  }, 30000)
})

onUnmounted(() => {
  window.removeEventListener('online', handleOnlineSync)
  if (syncInterval) clearInterval(syncInterval)
})
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <Route :size="14" />
            Force de vente B2B
          </div>
          <div>
            <div class="gcma-section-label">Feuille du jour</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Tournee commerciale du jour</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Check-In GPS auditable pour chaque droguerie. Sans reseau, l'evenement est sauvegarde localement et synchronise au retour de couverture.
            </p>
          </div>
        </div>

        <div class="w-full max-w-md space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="gcma-stat">
              <div class="gcma-section-label">Route</div>
              <div class="mt-1 text-lg font-black text-zinc-900">{{ routeData.id_ruta || 'N/A' }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Etat</div>
              <div class="mt-1 text-lg font-black text-zinc-900">{{ routeData.estado || 'Planifiee' }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Clients</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ totalClientes }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Visites</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ visitados }}</div>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <button
              @click="router.push({ name: 'hub' })"
              class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 active:bg-zinc-50 transition flex items-center justify-center gap-2"
            >
              <ArrowLeft :size="18" />
              Retour hub
            </button>
            <button
              @click="router.push({ name: 'catalogo-stock' })"
              class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 active:bg-blue-100 transition flex items-center justify-center gap-2"
            >
              <Boxes :size="18" />
              Catalogue
            </button>
            <button
              @click="loadRuta"
              :disabled="loading"
              class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 transition flex items-center justify-center gap-2 disabled:opacity-40"
            >
              <RefreshCcw :size="18" />
              Actualiser
            </button>
          </div>

          <button
            @click="syncPendingQueue"
            :disabled="pendingSync === 0"
            class="h-12 w-full rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 transition flex items-center justify-center gap-2 disabled:opacity-40"
          >
            <CloudOff :size="18" />
            Sync differee ({{ pendingSync }})
          </button>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="grid gap-4 md:grid-cols-2">
      <div v-for="index in 4" :key="index" class="kiosk-panel rounded-md p-5">
        <div class="animate-pulse space-y-3">
          <div class="h-5 w-40 rounded-md bg-zinc-200"></div>
          <div class="h-4 w-32 rounded-md bg-zinc-200"></div>
          <div class="h-16 rounded-md bg-zinc-200"></div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="!clientes.length"
      :icon="MapPinned"
      title="Aucune visite programmee"
      message="Aucune droguerie assignee pour aujourd'hui." />

    <div v-else class="grid gap-4 lg:grid-cols-2">
      <article v-for="cliente in clientes" :key="cliente.id_cliente" class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="flex items-start justify-between gap-4">
          <div class="space-y-2">
            <div class="gcma-section-label">Client</div>
            <h2 class="text-xl font-black text-zinc-900">{{ cliente.nombre }}</h2>
            <p class="text-sm text-zinc-500">{{ cliente.id_cliente }}</p>
          </div>
          <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-blue-700">
            <Navigation :size="22" />
          </div>
        </div>

        <div class="mt-4 gcma-data-row p-4 text-sm text-zinc-600">
          <div>Lat: {{ cliente.gps_lat }}</div>
          <div class="mt-1">Lng: {{ cliente.gps_lng }}</div>
        </div>

        <div class="mt-4">
          <div
            v-if="statusFor(cliente)"
            class="rounded-md border p-3 text-sm"
            :class="statusFor(cliente).fraude
              ? 'border-red-200 bg-red-50 text-red-700'
              : statusFor(cliente).queued
                ? 'border-amber-200 bg-amber-50 text-amber-700'
                : 'border-green-200 bg-green-50 text-green-700'"
          >
            <div class="flex items-start gap-2">
              <CircleAlert v-if="statusFor(cliente).fraude" :size="16" class="mt-0.5 shrink-0" />
              <CloudOff v-else-if="statusFor(cliente).queued" :size="16" class="mt-0.5 shrink-0" />
              <CheckCircle2 v-else :size="16" class="mt-0.5 shrink-0" />
              <span>{{ statusFor(cliente).message }}</span>
            </div>
          </div>
          <div v-else-if="cliente.visitado" class="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            Check-In deja enregistre pour aujourd'hui.
          </div>
        </div>

        <button
          @click="openCheckin(cliente)"
          class="mt-4 h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 transition"
        >
          Faire Check-In
        </button>
      </article>
    </div>

    <CheckInModal
      :open="checkinOpen"
      :client-name="selectedClient?.nombre ?? ''"
      :submitting="checkingIn"
      @close="closeCheckin"
      @submit="submitCheckin"
    />
  </KioskLayout>
</template>
