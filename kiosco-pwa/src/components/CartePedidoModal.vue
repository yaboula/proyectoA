<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangle,
  BadgeCheck,
  Loader2,
  ShoppingCart,
  Trash2,
  TriangleAlert,
} from 'lucide-vue-next'
import { getEstadoCuenta, syncPedidosOffline } from '../api/customerPortal'
import { useSyncQueueStore } from '../stores/syncQueue'

const props = defineProps({
  idCliente: { type: String, default: '' },
  cartItems: { type: Array, default: () => [] }, // [{ item_code, item_name, qty, precio }]
})

const emit = defineEmits(['close', 'submitted'])

const syncStore = useSyncQueueStore()

const loadingEstado = ref(false)
const submitting = ref(false)
const estadoCuenta = ref(null)
const errorMsg = ref('')
const successMsg = ref('')

// Allow editing client when not pre-filled (comercial selecting which customer)
const clienteManual = ref(props.idCliente || '')
const clienteActivo = computed(() => clienteManual.value.trim())

// Carrito editable local
const localCart = ref(props.cartItems.map(it => ({ ...it })))

const totalMad = computed(() =>
  localCart.value.reduce((s, it) => s + (it.precio || 0) * it.qty, 0),
)
const bloqueado = computed(() => estadoCuenta.value?.bloqueado_para_venta ?? false)
const canSubmit = computed(() =>
  !bloqueado.value &&
  localCart.value.length > 0 &&
  clienteActivo.value.length > 0 &&
  !submitting.value
)

async function loadEstado() {
  if (!clienteActivo.value) return
  loadingEstado.value = true
  try {
    estadoCuenta.value = await getEstadoCuenta(clienteActivo.value)
  } catch {
    estadoCuenta.value = null
  } finally {
    loadingEstado.value = false
  }
}

onMounted(() => {
  if (clienteActivo.value) loadEstado()
})

function changeQty(index, delta) {
  const newQty = localCart.value[index].qty + delta
  if (newQty <= 0) {
    localCart.value.splice(index, 1)
  } else {
    localCart.value[index] = { ...localCart.value[index], qty: newQty }
  }
}

async function onSubmit() {
  if (!canSubmit.value) return

  submitting.value = true
  errorMsg.value = ''

  const pedido = {
    id_cliente: clienteActivo.value,
    items: localCart.value.map(it => ({ item_code: it.item_code, qty: it.qty })),
  }

  try {
    const result = await syncPedidosOffline([pedido])
    if (result?.synced > 0) {
      successMsg.value = `Commande ${result.ids_creados[0]} enregistrée avec succès.`
      emit('submitted', result)
    } else {
      throw new Error('La commande n\'a pas pu être traitée.')
    }
  } catch (error) {
    // Guardar offline si hay error de red
    syncStore.enqueue({ type: 'pedido', payload: pedido })
    errorMsg.value = 'Hors ligne: commande sauvegardée localement et sera synchronisée automatiquement.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 flex items-end justify-center bg-black/50 sm:items-center">
      <div class="w-full max-w-lg animate-fade-in rounded-t-md rounded-b-none border border-zinc-200 bg-white shadow-xl sm:rounded-md sm:mx-4">

        <!-- Header -->
        <div class="flex items-center gap-3 border-b border-zinc-200 px-5 py-4">
          <ShoppingCart :size="20" class="text-blue-600" />
          <div class="flex-1">
            <div class="text-sm font-black uppercase tracking-[0.16em] text-zinc-900">Panier de commande</div>
            <div v-if="props.idCliente" class="text-xs text-zinc-500">Client: {{ clienteActivo }}</div>
          </div>
          <button type="button" class="h-10 w-10 rounded-md border border-zinc-200 text-zinc-500 active:bg-zinc-50 flex items-center justify-center" @click="emit('close')">
            ✕
          </button>
        </div>

        <!-- Sélection client (só si no viene pre-filled desde la ruta) -->
        <div v-if="!props.idCliente" class="px-5 pt-4">
          <div class="gcma-section-label mb-1.5">Client (ID ERPNext)</div>
          <div class="flex gap-2">
            <input
              v-model="clienteManual"
              type="text"
              autocomplete="off"
              class="flex-1 rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none"
              placeholder="ex: Droguerie Atlas Test"
              @keyup.enter="loadEstado"
            />
            <button
              type="button"
              class="h-16 w-16 rounded-md bg-blue-600 text-white flex items-center justify-center"
              @click="loadEstado"
            >
              <BadgeCheck :size="20" />
            </button>
          </div>
          <div v-if="!clienteActivo" class="mt-1.5 text-xs text-amber-600">
            Saisissez l'ID client pour valider la commande.
          </div>
        </div>

        <!-- Estado de cuenta -->
        <div class="px-5 pt-4">
          <div v-if="loadingEstado" class="flex items-center gap-2 text-sm text-zinc-500">
            <Loader2 :size="14" class="animate-spin" /> Vérification du compte...
          </div>
          <div
            v-else-if="bloqueado"
            class="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-start gap-2"
          >
            <TriangleAlert :size="16" class="mt-0.5 shrink-0" />
            <div>
              <div class="font-bold">Compte bloqué — commande interdite</div>
              <div class="mt-0.5 text-xs">
                Dépassement du délai de paiement.
                Débit vencido: <strong>{{ estadoCuenta?.deuda_vencida?.toFixed(2) }} MAD</strong>
                · {{ estadoCuenta?.dias_peor_mora }} jours
              </div>
            </div>
          </div>
          <div
            v-else-if="estadoCuenta"
            class="rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600 flex items-center gap-4"
          >
            <div>Crédit dispo: <strong>{{ (estadoCuenta.limite_credito - estadoCuenta.deuda_total).toFixed(2) }} MAD</strong></div>
            <div>Débit vencido: <strong>{{ estadoCuenta.deuda_vencida?.toFixed(2) }} MAD</strong></div>
          </div>
        </div>

        <!-- Lista del carrito -->
        <div class="max-h-72 overflow-y-auto px-5 py-4 space-y-2">
          <div
            v-for="(item, idx) in localCart"
            :key="item.item_code"
            class="gcma-data-row flex items-center gap-3 p-3"
          >
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-bold text-zinc-800">{{ item.item_name }}</div>
              <div class="text-xs text-zinc-500 font-mono">{{ item.item_code }}</div>
              <div v-if="item.precio" class="text-xs text-zinc-400">{{ item.precio }} MAD / u.</div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button type="button" class="h-10 w-10 rounded-md border border-zinc-300 bg-white text-lg font-bold text-zinc-600 active:bg-zinc-50 flex items-center justify-center" @click="changeQty(idx, -1)">
                <span v-if="item.qty === 1"><Trash2 :size="14" /></span>
                <span v-else>−</span>
              </button>
              <span class="w-8 text-center text-lg font-black text-zinc-900">{{ item.qty }}</span>
              <button type="button" class="h-10 w-10 rounded-md border border-zinc-300 bg-white text-lg font-bold text-zinc-600 active:bg-zinc-50 flex items-center justify-center" @click="changeQty(idx, 1)">
                +
              </button>
            </div>
            <div class="text-right shrink-0 min-w-[64px]">
              <div class="text-sm font-black text-zinc-900">{{ ((item.precio || 0) * item.qty).toFixed(2) }}</div>
              <div class="text-xs text-zinc-400">MAD</div>
            </div>
          </div>

          <div v-if="!localCart.length" class="py-8 text-center text-sm text-zinc-400">
            Panier vide
          </div>
        </div>

        <!-- Total -->
        <div class="border-t border-zinc-200 px-5 py-3 flex justify-between items-center">
          <div class="gcma-section-label">Total estimé</div>
          <div class="text-2xl font-black text-zinc-900">{{ totalMad.toFixed(2) }} <span class="text-sm font-normal text-zinc-400">MAD</span></div>
        </div>

        <!-- Feedback -->
        <div v-if="successMsg" class="mx-5 mb-3 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700 flex items-center gap-2">
          <BadgeCheck :size="16" /> {{ successMsg }}
        </div>
        <div v-if="errorMsg" class="mx-5 mb-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 flex items-start gap-2">
          <AlertTriangle :size="16" class="shrink-0 mt-0.5" /> {{ errorMsg }}
        </div>

        <!-- Acciones -->
        <div class="flex gap-3 border-t border-zinc-200 px-5 py-4">
          <button type="button" class="h-12 flex-1 rounded-md border border-zinc-300 bg-white text-sm font-bold text-zinc-500" @click="emit('close')">
            Continuer achats
          </button>
          <button
            type="button"
            :disabled="!canSubmit || !!successMsg"
            class="h-16 flex-[2] rounded-md bg-blue-600 text-sm font-black uppercase tracking-[0.14em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
            @click="onSubmit"
          >
            <Loader2 v-if="submitting" :size="18" class="animate-spin" />
            <BadgeCheck v-else :size="18" />
            {{ submitting ? 'Envoi...' : 'Passer la commande' }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>
