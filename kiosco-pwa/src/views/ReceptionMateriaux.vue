<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Boxes,
  ClipboardList,
  CircleAlert,
  MoveRight,
  PackagePlus,
  Printer,
  RefreshCcw,
  Truck,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import ReceptionCaptureModal from '../components/ReceptionCaptureModal.vue'
import { getComprasPendientes, registrarRecepcion } from '../api/kiosco'
import { printReceptionLabels } from '../utils/printer'
import { useOperarioStore } from '../stores/operario'

const router = useRouter()
const store = useOperarioStore()

const loading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const orders = ref([])
const selectedOrder = ref(null)
const selectedItem = ref(null)
const modalOpen = ref(false)
const lastResult = ref(null)
const printWarning = ref('')

const company = computed(() => store.operario?.company ?? '')
const pendingItemsCount = computed(() => orders.value.reduce((acc, order) => acc + order.items.length, 0))

async function loadOrders() {
  if (!company.value) return

  loading.value = true
  errorMessage.value = ''
  try {
    const result = await getComprasPendientes(company.value)
    orders.value = result.ordenes ?? []
  } catch (error) {
    errorMessage.value = error?.message_fr || 'Erreur lors du chargement des commandes a recevoir.'
    orders.value = []
  } finally {
    loading.value = false
  }
}

function openItemModal(order, item) {
  selectedOrder.value = order
  selectedItem.value = item
  modalOpen.value = true
}

function resetModalState() {
  modalOpen.value = false
  selectedOrder.value = null
  selectedItem.value = null
}

function closeModal() {
  if (submitting.value) return
  resetModalState()
}

async function submitReception(payload) {
  if (!selectedOrder.value || !selectedItem.value) return

  submitting.value = true
  errorMessage.value = ''
  printWarning.value = ''

  try {
    const result = await registrarRecepcion(selectedOrder.value.po_name, [
      {
        item_code: selectedItem.value.item_code,
        qty: payload.qty,
        supplier_batch: payload.supplierBatch,
        expiry_date: payload.expiryDate,
      },
    ])

    lastResult.value = result
  resetModalState()
    await loadOrders()

    try {
      await printReceptionLabels(result.lotes_generados ?? [])
    } catch {
      printWarning.value = 'Reception enregistree dans ERP, mais impression Zebra locale indisponible.'
    }
  } catch (error) {
    errorMessage.value = error?.message_fr || 'Impossible d\'enregistrer la reception.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const hasSession = await store.ensureSession()
  if (!hasSession || !store.hasModule('reception')) {
    router.replace({ name: 'hub' })
    return
  }

  await loadOrders()
})
</script>

<template>
  <KioskLayout>
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">
            <Truck :size="14" />
            Quai & quarantaine MP
          </div>
          <div>
            <div class="gcma-section-label">Reception materiaux</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Reception des matieres premieres</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Selectionner une commande d'achat, saisir la quantite recue et declencher l'entree ERP avec etiquette Zebra locale.
            </p>
          </div>
        </div>

        <div class="w-full max-w-md space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="gcma-stat">
              <div class="gcma-section-label">Commandes</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ orders.length }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Lignes ouvertes</div>
              <div class="mt-1 text-2xl font-black text-zinc-900">{{ pendingItemsCount }}</div>
            </div>
          </div>

          <div class="flex gap-3">
            <button @click="router.push({ name: 'hub' })"
                    class="h-12 flex-1 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 active:bg-zinc-50 transition flex items-center justify-center gap-2">
              <ArrowLeft :size="18" />
              Retour hub
            </button>
            <button @click="loadOrders"
                    :disabled="loading"
                    class="h-12 flex-1 rounded-md border border-indigo-200 bg-indigo-50 px-4 text-sm font-bold text-indigo-700 active:bg-indigo-100 transition flex items-center justify-center gap-2 disabled:opacity-40">
              <RefreshCcw :size="18" />
              Actualiser
            </button>
          </div>

          <div class="grid gap-3 sm:grid-cols-3">
                <button @click="router.push({ name: 'traslado-cuarentena' })"
                  class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 transition flex items-center justify-center gap-2">
              <MoveRight :size="18" />
              Gerer quarantaine
            </button>
            <button @click="router.push({ name: 'reimpresion' })"
                    class="h-12 rounded-md border border-indigo-200 bg-indigo-50 px-4 text-sm font-bold text-indigo-700 active:bg-indigo-100 transition flex items-center justify-center gap-2">
              <Printer :size="18" />
              Re-imprimer QR
            </button>
            <button @click="router.push({ name: 'inventario-ciego' })"
                    class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-bold text-zinc-700 active:bg-zinc-50 transition flex items-center justify-center gap-2 sm:col-span-3 lg:col-span-1">
              <ClipboardList :size="18" />
              Inventaire rapide
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      {{ errorMessage }}
    </div>

    <div v-if="printWarning" class="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-700 flex items-start gap-3">
      <CircleAlert :size="18" class="mt-0.5 shrink-0" />
      <span>{{ printWarning }}</span>
    </div>

    <div v-if="lastResult" class="rounded-md border border-green-200 bg-green-50 p-5 text-sm text-green-700">
      <div class="font-bold">Reception enregistree: {{ lastResult.purchase_receipt }}</div>
      <div class="mt-2">Lots generes: {{ (lastResult.lotes_generados ?? []).map(row => row.batch_no).filter(Boolean).join(', ') || 'Aucun lot retourne' }}</div>
    </div>

    <div v-if="loading" class="grid gap-4 md:grid-cols-2">
      <div v-for="index in 4" :key="index" class="kiosk-panel rounded-md p-5">
        <div class="animate-pulse space-y-3">
          <div class="h-5 w-40 rounded-md bg-zinc-200"></div>
          <div class="h-4 w-24 rounded-md bg-zinc-200"></div>
          <div class="h-20 rounded-md bg-zinc-200"></div>
        </div>
      </div>
    </div>

    <EmptyState v-else-if="!orders.length"
                :icon="Boxes"
                title="Aucune commande d'achat ouverte"
                message="Aucune reception en attente pour cette entreprise." />

    <div v-else class="grid gap-4 lg:grid-cols-2">
      <article v-for="order in orders" :key="order.po_name" class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="gcma-section-label">Commande d'achat</div>
            <h2 class="mt-1 text-2xl font-black text-zinc-900">{{ order.po_name }}</h2>
            <p class="mt-2 text-sm text-zinc-500">{{ order.supplier_name || order.supplier }}</p>
          </div>
          <div class="flex h-12 w-12 items-center justify-center rounded-md border border-indigo-200 bg-indigo-50 text-indigo-700">
            <PackagePlus :size="24" />
          </div>
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
          <div class="gcma-stat">
            <div class="gcma-section-label">Date PO</div>
            <div class="mt-1 font-semibold text-zinc-900">{{ order.transaction_date || 'N/A' }}</div>
          </div>
          <div class="gcma-stat">
            <div class="gcma-section-label">Lignes</div>
            <div class="mt-1 font-semibold text-zinc-900">{{ order.items.length }}</div>
          </div>
        </div>

        <div class="mt-5 space-y-3">
          <div v-for="item in order.items" :key="item.po_item_name" class="gcma-data-row p-4">
            <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div class="space-y-2">
                <div class="text-lg font-bold text-zinc-900">{{ item.item_name }}</div>
                <div class="text-sm text-zinc-500">{{ item.item_code }}</div>
                <div class="inline-flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold text-zinc-600">
                  Reliquat {{ item.qty_pending }} {{ item.uom }}
                </div>
              </div>

              <button @click="openItemModal(order, item)"
                      class="h-16 rounded-md bg-indigo-600 px-5 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-indigo-700 transition md:min-w-56">
                Receptionner
              </button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <ReceptionCaptureModal :open="modalOpen"
                           :item="selectedItem"
                           :submitting="submitting"
                           @close="closeModal"
                           @submit="submitReception" />
  </KioskLayout>
</template>
