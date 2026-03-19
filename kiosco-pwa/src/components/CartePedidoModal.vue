<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  BadgeCheck,
  Building2,
  ChevronRight,
  Loader2,
  Search,
  ShoppingCart,
  Trash2,
  TriangleAlert,
  UserPlus,
  Users,
} from 'lucide-vue-next'
import { getEstadoCuenta, getClientesB2B, syncPedidosOffline } from '../api/customerPortal'
import { useSyncQueueStore } from '../stores/syncQueue'

const props = defineProps({
  idCliente: { type: String, default: '' },
  cartItems: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'submitted'])

const router = useRouter()
const syncStore = useSyncQueueStore()

// ── Modo de selección de cliente ──────────────────────────────────────────────
// 'select'  → búsqueda en base de clientes ERPNext
// 'custom'  → entrada manual ad-hoc (cliente no registrado)
const modoCliente = ref(props.idCliente ? 'confirmed' : 'select')

// ── Estado selector ────────────────────────────────────────────────────────────
const searchQuery = ref('')
const clientesLista = ref([])
const loadingClientes = ref(false)
const clienteSeleccionado = ref(null)   // objeto completo del cliente
const clienteCustomNombre = ref('')      // modo custom
const clienteCustomTel = ref('')

// ── Estado cuenta (verificación crédito) ─────────────────────────────────────
const loadingEstado = ref(false)
const estadoCuenta = ref(null)
const clienteVerificado = ref(!!props.idCliente)

// ── Carrito / submit ──────────────────────────────────────────────────────────
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const localCart = ref(props.cartItems.map(it => ({ ...it })))

// ── Computed ──────────────────────────────────────────────────────────────────
const clienteActivo = computed(() => {
  if (props.idCliente) return props.idCliente
  if (modoCliente.value === 'select') return clienteSeleccionado.value?.id ?? ''
  if (modoCliente.value === 'custom') return clienteCustomNombre.value.trim()
  if (modoCliente.value === 'confirmed') return props.idCliente
  return ''
})

const bloqueado = computed(() => {
  if (modoCliente.value === 'custom') return false
  return estadoCuenta.value?.bloqueado_para_venta ?? false
})

const canSubmit = computed(() =>
  clienteVerificado.value &&
  clienteActivo.value.length > 0 &&
  !bloqueado.value &&
  localCart.value.length > 0 &&
  !submitting.value &&
  !successMsg.value
)

const totalMad = computed(() =>
  localCart.value.reduce((s, it) => s + (it.precio || 0) * it.qty, 0)
)

// ── Búsqueda de clientes ───────────────────────────────────────────────────────
let debounceTimer = null
watch(searchQuery, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(buscarClientes, 350)
})

async function buscarClientes() {
  loadingClientes.value = true
  try {
    const res = await getClientesB2B({ search: searchQuery.value })
    clientesLista.value = res?.clientes ?? []
  } catch {
    clientesLista.value = []
  } finally {
    loadingClientes.value = false
  }
}

onMounted(() => {
  if (modoCliente.value === 'select') buscarClientes()
  if (props.idCliente) verificarCuenta(props.idCliente)
})

// ── Seleccionar cliente de la lista ──────────────────────────────────────────
async function seleccionarCliente(cliente) {
  clienteSeleccionado.value = cliente
  clienteVerificado.value = false
  estadoCuenta.value = null
  await verificarCuenta(cliente.id)
}

// ── Verificar estado de cuenta ────────────────────────────────────────────────
async function verificarCuenta(idCliente) {
  if (!idCliente) return
  loadingEstado.value = true
  try {
    estadoCuenta.value = await getEstadoCuenta(idCliente)
  } catch {
    estadoCuenta.value = null
  } finally {
    loadingEstado.value = false
    clienteVerificado.value = true
  }
}

// ── Modo custom: confirmar cliente manual ─────────────────────────────────────
function confirmarCustom() {
  if (!clienteCustomNombre.value.trim()) return
  clienteVerificado.value = true
  estadoCuenta.value = null
}

// ── Cambio de modo ────────────────────────────────────────────────────────────
function setModo(modo) {
  modoCliente.value = modo
  clienteSeleccionado.value = null
  clienteVerificado.value = false
  estadoCuenta.value = null
  errorMsg.value = ''
  searchQuery.value = ''
  if (modo === 'select') buscarClientes()
}

// ── Carrito ───────────────────────────────────────────────────────────────────
function changeQty(index, delta) {
  const newQty = localCart.value[index].qty + delta
  if (newQty <= 0) {
    localCart.value.splice(index, 1)
  } else {
    localCart.value[index] = { ...localCart.value[index], qty: newQty }
  }
}

// ── Submit pedido ─────────────────────────────────────────────────────────────
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
      successMsg.value = `Commande ${result.ids_creados?.[0] ?? ''} enregistrée avec succès.`
      emit('submitted', result)
    } else {
      throw new Error('La commande n\'a pas pu être traitée.')
    }
  } catch {
    syncStore.enqueue({ type: 'pedido', payload: pedido })
    errorMsg.value = 'Hors ligne: commande sauvegardée localement et sera synchronisée automatiquement.'
  } finally {
    submitting.value = false
  }
}

function goNouveauClient() {
  emit('close')
  router.push({ name: 'nuevo-cliente-b2b' })
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 flex items-end justify-center bg-black/50 sm:items-center">
      <div class="w-full max-w-lg animate-fade-in rounded-t-md rounded-b-none border border-zinc-200 bg-white shadow-xl sm:rounded-md sm:mx-4">

        <!-- Header -->
        <div class="flex items-center gap-3 border-b border-zinc-200 px-5 py-4">
          <ShoppingCart :size="20" class="text-blue-600" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-black uppercase tracking-[0.16em] text-zinc-900">Panier de commande</div>
            <div v-if="clienteActivo" class="truncate text-xs text-zinc-500">
              Client: <span class="font-semibold text-zinc-700">{{ clienteSeleccionado?.nombre ?? clienteActivo }}</span>
            </div>
          </div>
          <button type="button" class="h-10 w-10 shrink-0 rounded-md border border-zinc-200 text-zinc-500 active:bg-zinc-50 flex items-center justify-center" @click="emit('close')">
            ✕
          </button>
        </div>

        <!-- ── SELECCIÓN DE CLIENTE (si no viene pre-llenado) ── -->
        <div v-if="!props.idCliente" class="border-b border-zinc-200">

          <!-- Tabs de modo -->
          <div class="flex gap-1 px-4 pt-3 pb-0">
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-bold transition"
              :class="modoCliente === 'select'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'"
              @click="setModo('select')"
            >
              <Users :size="13" /> Base clients
            </button>
            <button
              type="button"
              class="flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-bold transition"
              :class="modoCliente === 'custom'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'"
              @click="setModo('custom')"
            >
              <Building2 :size="13" /> Saisie libre
            </button>
            <button
              type="button"
              class="ml-auto flex items-center gap-1.5 rounded-md border border-dashed border-zinc-300 px-3 py-2 text-xs font-bold text-zinc-500 hover:border-blue-400 hover:text-blue-600 transition"
              @click="goNouveauClient"
            >
              <UserPlus :size="13" /> Nouveau client
            </button>
          </div>

          <!-- Modo: selección desde base de datos -->
          <div v-if="modoCliente === 'select'" class="px-4 py-3 space-y-2">
            <div class="relative">
              <Search :size="15" class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                v-model="searchQuery"
                type="search"
                autocomplete="off"
                class="w-full rounded-md border border-zinc-300 bg-white py-3 pl-9 pr-3 text-sm text-zinc-900 focus:border-blue-600 focus:outline-none"
                placeholder="Rechercher un client B2B..."
              />
            </div>

            <div v-if="loadingClientes" class="flex items-center gap-2 py-2 text-xs text-zinc-400">
              <Loader2 :size="13" class="animate-spin" /> Chargement...
            </div>

            <div v-else class="max-h-40 overflow-y-auto space-y-1">
              <button
                v-for="c in clientesLista"
                :key="c.id"
                type="button"
                class="w-full rounded-md border px-3 py-2.5 text-left text-sm transition"
                :class="clienteSeleccionado?.id === c.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50'"
                @click="seleccionarCliente(c)"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="min-w-0">
                    <div class="font-semibold text-zinc-900 truncate">{{ c.nombre }}</div>
                    <div class="text-xs text-zinc-400">{{ c.grupo }} · {{ c.territorio }}</div>
                  </div>
                  <div class="shrink-0 flex items-center gap-1.5">
                    <span
                      class="rounded-md px-2 py-0.5 text-xs font-bold"
                      :class="c.bloqueado
                        ? 'bg-red-50 text-red-600 border border-red-200'
                        : 'bg-green-50 text-green-700 border border-green-200'"
                    >
                      {{ c.bloqueado ? 'Bloqué' : 'OK' }}
                    </span>
                    <ChevronRight :size="14" class="text-zinc-300" />
                  </div>
                </div>
              </button>
              <div v-if="!loadingClientes && !clientesLista.length" class="py-4 text-center text-xs text-zinc-400">
                Aucun client trouvé
              </div>
            </div>

            <!-- Vérification en cours -->
            <div v-if="loadingEstado" class="flex items-center gap-2 text-xs text-zinc-500">
              <Loader2 :size="13" class="animate-spin" /> Vérification du compte...
            </div>
          </div>

          <!-- Modo: saisie libre (cliente no registrado) -->
          <div v-if="modoCliente === 'custom'" class="px-4 py-3 space-y-3">
            <div>
              <div class="gcma-section-label mb-1">Raison sociale *</div>
              <input
                v-model="clienteCustomNombre"
                type="text"
                autocomplete="off"
                class="w-full rounded-md border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
                placeholder="Droguerie El Wafa..."
                @keyup.enter="confirmarCustom"
              />
            </div>
            <div>
              <div class="gcma-section-label mb-1">Téléphone</div>
              <input
                v-model="clienteCustomTel"
                type="tel"
                class="w-full rounded-md border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
                placeholder="+212 6XX..."
              />
            </div>
            <div
              v-if="modoCliente === 'custom'"
              class="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700"
            >
              Saisie libre : le client ne sera pas vérifié en base. Utilisez "Nouveau client" pour l'enregistrer en ERPNext.
            </div>
            <button
              type="button"
              :disabled="!clienteCustomNombre.trim()"
              class="h-12 w-full rounded-md bg-blue-600 text-sm font-black text-white disabled:opacity-40"
              @click="confirmarCustom"
            >
              Confirmer ce client
            </button>
          </div>
        </div>

        <!-- ── ESTADO DE CUENTA (cuando hay cliente seleccionado) ── -->
        <div v-if="clienteVerificado || props.idCliente" class="px-5 pt-3">
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
                Dépassement délai paiement.
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
          <div
            v-else-if="modoCliente === 'custom' && clienteVerificado"
            class="rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-700"
          >
            Client en saisie libre — commande non soumise à vérification de crédit.
          </div>
        </div>

        <!-- ── LISTA DEL CARRITO ── -->
        <div class="max-h-52 overflow-y-auto px-5 py-3 space-y-2">
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
            :disabled="!canSubmit"
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
