<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  BadgeCheck,
  Boxes,
  Loader2,
  PackageX,
  Search,
  ShoppingCart,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import CartePedidoModal from '../components/CartePedidoModal.vue'
import { useOperarioStore } from '../stores/operario'
import { getCatalogoStock } from '../api/customerPortal'

const operarioStore = useOperarioStore()

const router = useRouter()

const searchQuery = ref('')
const items = ref([])
const loading = ref(false)
const errorMessage = ref('')
const totalItems = ref(0)
const priceList = ref('')

// Carrito ligero: { [item_code]: { item, qty } }
const cart = ref({})
const showCartModal = ref(false)

const cartCount = computed(() => Object.values(cart.value).reduce((s, v) => s + v.qty, 0))
const cartItems = computed(() => Object.values(cart.value).filter(v => v.qty > 0))
const idClienteActivo = computed(() => operarioStore.customerId || operarioStore.user || '')

let debounceTimer = null

async function fetchCatalog() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await getCatalogoStock({ search: searchQuery.value.trim() || undefined })
    items.value = res?.items ?? []
    totalItems.value = res?.total ?? 0
    priceList.value = res?.price_list ?? ''
  } catch (err) {
    errorMessage.value = err?.message || err?.message_fr || 'Impossible de charger le catalogue.'
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(searchQuery, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchCatalog, 400)
})

onMounted(fetchCatalog)

function addToCart(item) {
  const prev = cart.value[item.item_code]
  cart.value = {
    ...cart.value,
    [item.item_code]: {
      item,
      qty: (prev?.qty ?? 0) + 1,
    },
  }
}

function removeFromCart(itemCode) {
  const prev = cart.value[itemCode]
  if (!prev) return
  const newQty = prev.qty - 1
  if (newQty <= 0) {
    const updated = { ...cart.value }
    delete updated[itemCode]
    cart.value = updated
  } else {
    cart.value = { ...cart.value, [itemCode]: { ...prev, qty: newQty } }
  }
}

function goToCart() {
  showCartModal.value = true
}

function onCartSubmitted() {
  cart.value = {}
  showCartModal.value = false
}
</script>

<template>
  <KioskLayout maxWidth="6xl">
    <CartePedidoModal
      v-if="showCartModal"
      :id-cliente="idClienteActivo"
      :cart-items="cartItems.map(v => ({ item_code: v.item.item_code, item_name: v.item.item_name, qty: v.qty, precio: v.item.precio_venta }))"
      @close="showCartModal = false"
      @submitted="onCartSubmitted"
    />

    <!-- Header -->
    <div class="kiosk-panel p-5 md:p-6">
      <div class="gcma-toolbar">
        <div class="flex items-start gap-4">
          <button
            type="button"
            class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md"
            @click="router.back()"
          >
            <ArrowLeft :size="20" class="text-zinc-600" />
          </button>
          <div>
            <div class="kiosk-chip inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em]">
              <Boxes :size="13" />
              Sprint 07
            </div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">
              Catalogue &amp; Stock
            </h1>
            <p class="mt-1 text-sm text-zinc-500">
              Stock en temps réel · {{ priceList || 'Liste standard' }}
            </p>
          </div>
        </div>

        <!-- Carrito flotante -->
        <button
          v-if="cartCount > 0"
          type="button"
          class="gcma-stat flex items-center gap-2 text-blue-700 hover:border-blue-400 transition cursor-pointer"
          @click="goToCart"
        >
          <ShoppingCart :size="18" />
          <div>
            <div class="text-xl font-black leading-none">{{ cartCount }}</div>
            <div class="gcma-section-label mt-0.5">articles</div>
          </div>
        </button>
      </div>
    </div>

    <!-- Buscador -->
    <div class="kiosk-panel p-5 md:p-6">
      <div class="relative">
        <Search :size="18" class="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400" />
        <input
          v-model="searchQuery"
          type="search"
          autocomplete="off"
          class="w-full rounded-md border border-zinc-300 bg-white py-4 pl-11 pr-4 text-lg text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          placeholder="Rechercher un article..."
        />
      </div>
    </div>

    <!-- Estado cargando -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <Loader2 :size="36" class="animate-spin text-blue-600" />
    </div>

    <!-- Error -->
    <div
      v-else-if="errorMessage"
      class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700"
    >
      {{ errorMessage }}
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="!items.length"
      :icon="PackageX"
      title="Aucun article trouvé"
      message="Modifiez votre recherche ou contactez le magasin."
    />

    <!-- Grilla de items -->
    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="item in items"
        :key="item.item_code"
        class="kiosk-panel flex flex-col justify-between gap-4 p-4"
        :class="{ 'opacity-60': !item.en_stock }"
      >
        <!-- Info -->
        <div>
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="font-mono text-xs text-zinc-400">{{ item.item_code }}</div>
              <div class="mt-0.5 text-base font-bold leading-snug text-zinc-900">{{ item.item_name }}</div>
              <div class="mt-0.5 text-xs text-zinc-500">{{ item.item_group }}</div>
            </div>
            <span
              class="shrink-0 rounded-md px-2 py-1 text-xs font-bold"
              :class="item.en_stock
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-600 border border-red-200'"
            >
              {{ item.en_stock ? 'En stock' : 'Rupture' }}
            </span>
          </div>

          <div class="mt-3 flex items-center justify-between">
            <div>
              <div class="gcma-section-label">Stock</div>
              <div class="text-lg font-black text-zinc-900">
                {{ item.stock_disponible }} <span class="text-sm font-normal text-zinc-400">{{ item.uom }}</span>
              </div>
            </div>
            <div class="text-right">
              <div class="gcma-section-label">Prix</div>
              <div class="text-lg font-black text-zinc-900">
                {{ item.precio_venta ? `${item.precio_venta} MAD` : '—' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Acciones -->
        <div class="flex items-center gap-2">
          <template v-if="cart[item.item_code]">
            <button
              type="button"
              class="h-12 w-12 rounded-md border border-zinc-300 bg-white text-xl font-bold text-zinc-600 active:bg-zinc-50"
              @click="removeFromCart(item.item_code)"
            >
              −
            </button>
            <div class="flex-1 text-center text-xl font-black text-blue-700">
              {{ cart[item.item_code].qty }}
            </div>
            <button
              type="button"
              :disabled="!item.en_stock"
              class="h-12 w-12 rounded-md border border-blue-600 bg-blue-600 text-xl font-bold text-white active:bg-blue-700 disabled:opacity-40"
              @click="addToCart(item)"
            >
              +
            </button>
          </template>
          <button
            v-else
            type="button"
            :disabled="!item.en_stock"
            class="h-14 w-full rounded-md bg-blue-600 text-sm font-black uppercase tracking-[0.14em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
            @click="addToCart(item)"
          >
            <ShoppingCart :size="16" />
            Ajouter
          </button>
        </div>
      </div>
    </div>

    <!-- Resumen carrito sticky -->
    <Teleport to="body">
      <div
        v-if="cartCount > 0"
        class="fixed bottom-0 left-0 right-0 z-30 border-t border-zinc-200 bg-white px-4 py-4 shadow-lg"
      >
        <div class="mx-auto flex max-w-2xl items-center gap-3">
          <div class="flex-1">
            <div class="text-sm font-semibold text-zinc-700">
              {{ cartCount }} article{{ cartCount > 1 ? 's' : '' }} dans le panier
            </div>
            <div class="text-xs text-zinc-400">
              Total: {{ cartItems.reduce((s, v) => s + v.item.precio_venta * v.qty, 0).toFixed(2) }} MAD
            </div>
          </div>
          <button
            type="button"
            class="h-14 rounded-md bg-blue-600 px-6 text-sm font-black uppercase tracking-[0.14em] text-white active:bg-blue-700 flex items-center gap-2"
            @click="goToCart"
          >
            <BadgeCheck :size="16" />
            Commander
          </button>
        </div>
      </div>
    </Teleport>

  </KioskLayout>
</template>
