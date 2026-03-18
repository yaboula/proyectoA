<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Award, CreditCard, Headset, PackagePlus, RefreshCcw, ShieldAlert, Sparkles } from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import {
  createSupportTicket,
  crearPedidoPortal,
  getLoyaltyPoints,
  getPortalDashboard,
  getPortalEstadoCuenta,
  redimirPuntos,
} from '../api/customerPortal'

const loading = ref(false)
const submittingOrder = ref(false)
const submittingTicket = ref(false)
const submittingRedeem = ref(false)

const dashboard = ref(null)
const estadoCuenta = ref(null)
const loyalty = ref(null)
const puntosARedimir = ref('100')

const orderItemCode = ref('')
const orderQty = ref('1')

const sosDescription = ref('')
const sosBatch = ref('')
const sosPhotoFile = ref(null)

const successMessage = ref('')
const errorMessage = ref('')

const isBlocked = computed(() => Boolean(dashboard.value?.bloqueado_30_dias))

function formatMoney(value) {
  const amount = Number(value || 0)
  return `${amount.toFixed(2)} MAD`
}

function normalizeError(error, fallback) {
  if (typeof error === 'string') return error
  return error?.message || error?.message_fr || fallback
}

async function loadPortalData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [home, cuenta, pts] = await Promise.all([
      getPortalDashboard(),
      getPortalEstadoCuenta(),
      getLoyaltyPoints().catch(() => null),
    ])

    dashboard.value = home
    estadoCuenta.value = cuenta
    loyalty.value = pts
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Impossible de charger votre espace client.')
    dashboard.value = null
    estadoCuenta.value = null
    loyalty.value = null
  } finally {
    loading.value = false
  }
}

async function onRedimirPuntos() {
  const puntos = parseInt(puntosARedimir.value || '0', 10)
  if (!puntos || puntos <= 0) return

  submittingRedeem.value = true
  successMessage.value = ''
  errorMessage.value = ''

  try {
    const res = await redimirPuntos({ puntos })
    successMessage.value = `${res.puntos_canjeados} points échangés — remise de ${res.descuento_aplicado_mad} MAD sur votre prochaine commande.`
    await loadPortalData()
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Échec de l\'échange de points.')
  } finally {
    submittingRedeem.value = false
  }
}

function onPickPhoto(event) {
  sosPhotoFile.value = event.target.files?.[0] ?? null
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('PHOTO_READ_ERROR'))
    reader.readAsDataURL(file)
  })
}

async function submitOrder() {
  if (submittingOrder.value || isBlocked.value) return

  const itemCode = orderItemCode.value.trim()
  const qty = Number(orderQty.value)

  if (!itemCode || !Number.isFinite(qty) || qty <= 0) {
    errorMessage.value = 'Saisissez un article valide et une quantite superieure a zero.'
    return
  }

  submittingOrder.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const payload = {
      id_cliente: dashboard.value?.id_cliente,
      items: [{ item_code: itemCode, qty }],
    }

    const response = await crearPedidoPortal(payload)
    successMessage.value = `Commande creee avec succes: ${response?.sales_order ?? ''}`.trim()

    orderItemCode.value = ''
    orderQty.value = '1'
    await loadPortalData()
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Echec de creation de commande.')
  } finally {
    submittingOrder.value = false
  }
}

async function submitSos() {
  if (submittingTicket.value) return

  const description = sosDescription.value.trim()
  if (!description) {
    errorMessage.value = 'La description du ticket SOS est obligatoire.'
    return
  }

  submittingTicket.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const b64Photo = sosPhotoFile.value ? await fileToBase64(sosPhotoFile.value) : ''
    const response = await createSupportTicket(
      description,
      b64Photo,
      sosBatch.value.trim(),
      dashboard.value?.id_cliente,
    )

    successMessage.value = `Ticket SOS envoye: ${response?.issue_id ?? ''}`.trim()
    sosDescription.value = ''
    sosBatch.value = ''
    sosPhotoFile.value = null
  } catch (error) {
    errorMessage.value = normalizeError(error, 'Echec de creation du ticket SOS.')
  } finally {
    submittingTicket.value = false
  }
}

onMounted(loadPortalData)
</script>

<template>
  <KioskLayout max-width="7xl">
    <div class="kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar items-start">
        <div class="max-w-3xl space-y-4">
          <div class="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-blue-700">
            <ShieldAlert :size="14" />
            Portail B2B Client
          </div>
          <div>
            <div class="gcma-section-label">Self-service 24/7</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">
              Mon espace droguerie
            </h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Passez vos commandes, consultez votre compte et ouvrez un ticket SOS qualite en un clic.
            </p>
          </div>
        </div>

        <button
          type="button"
          :disabled="loading"
          @click="loadPortalData"
          class="h-12 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100 disabled:opacity-40 transition flex items-center justify-center gap-2"
        >
          <RefreshCcw :size="18" />
          Actualiser
        </button>
      </div>
    </div>

    <div v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      {{ errorMessage }}
    </div>

    <div v-if="successMessage" class="rounded-md border border-green-200 bg-green-50 p-5 text-sm text-green-700">
      {{ successMessage }}
    </div>

    <div v-if="loading" class="kiosk-panel rounded-md p-5">
      <div class="animate-pulse space-y-3">
        <div class="h-5 w-56 rounded-md bg-zinc-200"></div>
        <div class="h-4 w-40 rounded-md bg-zinc-200"></div>
        <div class="h-16 rounded-md bg-zinc-200"></div>
      </div>
    </div>

    <EmptyState
      v-else-if="!dashboard"
      :icon="AlertTriangle"
      title="Aucune donnee client"
      message="Verifiez la session portail et les permissions du compte client."
    />

    <template v-else>
      <div
        v-if="isBlocked"
        class="rounded-md border border-red-200 bg-red-50 p-5 text-red-700"
      >
        <div class="flex items-start gap-3">
          <AlertTriangle :size="20" class="mt-0.5 shrink-0" />
          <div>
            <div class="text-sm font-black uppercase tracking-[0.18em]">Compte bloque</div>
            <p class="mt-2 text-sm leading-6">
              {{ dashboard.mensaje_bloqueo_30_dias || 'Retard superieur a 30 jours. Veuillez regler votre situation ou contacter la comptabilite.' }}
            </p>
          </div>
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article class="gcma-stat">
          <div class="gcma-section-label">Client</div>
          <div class="mt-1 text-lg font-black text-zinc-900">{{ dashboard.id_cliente }}</div>
        </article>
        <article class="gcma-stat">
          <div class="gcma-section-label">Dette totale</div>
          <div class="mt-1 text-lg font-black text-zinc-900">{{ formatMoney(dashboard.estado_cuenta?.deuda_total) }}</div>
        </article>
        <article class="gcma-stat">
          <div class="gcma-section-label">Dette echue</div>
          <div class="mt-1 text-lg font-black text-zinc-900">{{ formatMoney(dashboard.estado_cuenta?.deuda_vencida) }}</div>
        </article>
      </div>

      <div class="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <section class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
          <div>
            <div class="gcma-section-label">Commande rapide</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900">Nouvelle commande</h2>
          </div>

          <div class="space-y-3">
            <div>
              <label class="gcma-section-label">Code article</label>
              <input
                v-model="orderItemCode"
                type="text"
                class="mt-1 h-14 w-full rounded-md border border-zinc-300 bg-white px-4 text-xl font-mono text-zinc-900"
                placeholder="EX: PT-PIN-BLC-MAT-20L"
              >
            </div>
            <div>
              <label class="gcma-section-label">Quantite</label>
              <input
                v-model="orderQty"
                type="number"
                min="1"
                step="1"
                class="mt-1 h-14 w-full rounded-md border border-zinc-300 bg-white px-4 text-xl font-semibold text-zinc-900"
              >
            </div>
          </div>

          <button
            type="button"
            :disabled="submittingOrder || isBlocked"
            @click="submitOrder"
            class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
          >
            <PackagePlus :size="18" />
            {{ submittingOrder ? 'Envoi...' : 'Envoyer commande' }}
          </button>
        </section>

        <section class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
          <div>
            <div class="gcma-section-label">SOS Support</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900">Ticket qualite immediat</h2>
          </div>

          <div class="space-y-3">
            <div>
              <label class="gcma-section-label">Lot concerne</label>
              <input
                v-model="sosBatch"
                type="text"
                class="mt-1 h-14 w-full rounded-md border border-zinc-300 bg-white px-4 text-xl font-mono text-zinc-900"
                placeholder="EX: LOT-RESINE-001"
              >
            </div>
            <div>
              <label class="gcma-section-label">Description</label>
              <textarea
                v-model="sosDescription"
                rows="4"
                class="mt-1 w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-base text-zinc-900"
                placeholder="Decrivez le probleme constate..."
              />
            </div>
            <div class="space-y-2">
              <label class="gcma-section-label">Photo (optionnelle)</label>
              <label class="flex h-16 cursor-pointer items-center justify-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 text-sm font-bold text-blue-700 active:bg-blue-100">
                <Headset :size="18" />
                Joindre une photo
                <input
                  type="file"
                  class="hidden"
                  accept="image/jpeg, image/png"
                  capture="environment"
                  @change="onPickPhoto"
                >
              </label>
              <p class="text-xs text-zinc-500">
                {{ sosPhotoFile ? `Fichier: ${sosPhotoFile.name}` : 'Aucune photo selectionnee.' }}
              </p>
            </div>
          </div>

          <button
            type="button"
            :disabled="submittingTicket"
            @click="submitSos"
            class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white active:bg-blue-700 disabled:opacity-40 transition"
          >
            {{ submittingTicket ? 'Creation...' : 'Creer ticket SOS' }}
          </button>
        </section>
      </div>

      <section class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="gcma-toolbar items-start">
          <div>
            <div class="gcma-section-label">Recommandations</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
              <Sparkles :size="20" class="text-blue-700" />
              Catalogue intelligent
            </h2>
          </div>
          <span class="kiosk-chip rounded-md px-3 py-1 text-xs font-bold">
            {{ dashboard.sugerencias?.length || 0 }} suggestions
          </span>
        </div>

        <div class="mt-4 space-y-2">
          <div
            v-for="item in dashboard.sugerencias || []"
            :key="item.item_code"
            class="gcma-data-row flex items-center justify-between rounded-md border px-4 py-3"
          >
            <div>
              <div class="text-sm font-bold text-zinc-900">{{ item.item_name || item.item_code }}</div>
              <div class="text-xs text-zinc-500">{{ item.item_code }}</div>
            </div>
            <span class="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">
              Score {{ item.score }}
            </span>
          </div>
          <p v-if="!(dashboard.sugerencias || []).length" class="text-sm text-zinc-500">
            Pas encore de suggestions disponibles.
          </p>
        </div>
      </section>

      <!-- Sección Loyalty Program -->
      <section v-if="loyalty" class="kiosk-panel rounded-md p-5 md:p-6 space-y-4">
        <div class="gcma-toolbar items-start">
          <div>
            <div class="gcma-section-label">Fidélité</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
              <Award :size="20" class="text-amber-500" />
              Programme de fidélité
            </h2>
          </div>
          <div class="gcma-stat text-right">
            <div class="text-2xl font-black text-amber-600">{{ loyalty.saldo?.saldo_puntos ?? 0 }}</div>
            <div class="gcma-section-label mt-0.5">points</div>
          </div>
        </div>

        <!-- Estadísticas -->
        <div class="grid grid-cols-3 gap-3">
          <div class="gcma-stat text-center">
            <div class="text-lg font-black text-zinc-900">{{ loyalty.saldo?.puntos_acumulados ?? 0 }}</div>
            <div class="gcma-section-label mt-0.5">accumulés</div>
          </div>
          <div class="gcma-stat text-center">
            <div class="text-lg font-black text-zinc-900">{{ loyalty.saldo?.puntos_canjeados ?? 0 }}</div>
            <div class="gcma-section-label mt-0.5">échangés</div>
          </div>
          <div class="gcma-stat text-center">
            <div class="text-lg font-black text-amber-600">{{ loyalty.equivalencia_mad ?? 0 }} MAD</div>
            <div class="gcma-section-label mt-0.5">valeur</div>
          </div>
        </div>

        <!-- Detalle por familia -->
        <div v-if="loyalty.detalle_por_familia?.length" class="space-y-2">
          <div class="gcma-section-label">Points par famille de produit</div>
          <div
            v-for="fam in loyalty.detalle_por_familia"
            :key="fam.familia"
            class="gcma-data-row flex items-center justify-between px-3 py-2"
          >
            <span class="text-sm font-semibold text-zinc-700">{{ fam.familia }}</span>
            <span class="kiosk-chip rounded-md px-2 py-1 text-xs font-bold">
              {{ fam.puntos_estimados }} pts · {{ fam.facturacion_ytd }} MAD
            </span>
          </div>
        </div>

        <!-- Redimir puntos -->
        <div v-if="(loyalty.saldo?.saldo_puntos ?? 0) > 0" class="kiosk-panel-soft rounded-md p-4 space-y-3">
          <div class="gcma-section-label">Échanger des points</div>
          <div class="flex gap-3">
            <input
              v-model="puntosARedimir"
              type="number"
              min="10"
              :max="loyalty.saldo?.saldo_puntos"
              class="w-28 rounded-md border border-zinc-300 bg-white px-4 py-3 text-xl font-mono text-zinc-900 text-center focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
            />
            <button
              type="button"
              :disabled="submittingRedeem || !puntosARedimir"
              class="h-14 flex-1 rounded-md bg-amber-500 text-sm font-black uppercase tracking-[0.14em] text-white active:bg-amber-600 disabled:opacity-40 transition flex items-center justify-center gap-2"
              @click="onRedimirPuntos"
            >
              <Award :size="16" />
              {{ submittingRedeem ? 'Traitement...' : 'Échanger' }}
            </button>
          </div>
          <p class="text-xs text-zinc-500">1 point = 10 MAD de remise sur votre prochaine commande</p>
        </div>
      </section>

      <section class="kiosk-panel rounded-md p-5 md:p-6">
        <div class="gcma-toolbar items-start">
          <div>
            <div class="gcma-section-label">Compte courant</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900 flex items-center gap-2">
              <CreditCard :size="20" class="text-blue-700" />
              Factures et paiements
            </h2>
          </div>
        </div>

        <div class="mt-4 grid gap-4 lg:grid-cols-2">
          <article class="kiosk-panel-soft rounded-md p-4">
            <h3 class="text-sm font-black uppercase tracking-[0.16em] text-zinc-500">Factures</h3>
            <div class="mt-3 space-y-2">
              <div
                v-for="row in estadoCuenta?.facturas || []"
                :key="row.name"
                class="gcma-data-row rounded-md border px-3 py-3"
              >
                <div class="text-sm font-bold text-zinc-900">{{ row.name }}</div>
                <div class="text-xs text-zinc-500">{{ row.posting_date }} · Echeance {{ row.due_date || '-' }}</div>
                <div class="mt-1 text-xs text-zinc-600">
                  Total {{ formatMoney(row.grand_total) }} · Reste {{ formatMoney(row.outstanding_amount) }}
                </div>
              </div>
              <p v-if="!(estadoCuenta?.facturas || []).length" class="text-sm text-zinc-500">Aucune facture recente.</p>
            </div>
          </article>

          <article class="kiosk-panel-soft rounded-md p-4">
            <h3 class="text-sm font-black uppercase tracking-[0.16em] text-zinc-500">Paiements</h3>
            <div class="mt-3 space-y-2">
              <div
                v-for="row in estadoCuenta?.pagos || []"
                :key="row.name"
                class="gcma-data-row rounded-md border px-3 py-3"
              >
                <div class="text-sm font-bold text-zinc-900">{{ row.name }}</div>
                <div class="text-xs text-zinc-500">{{ row.posting_date }}</div>
                <div class="mt-1 text-xs text-zinc-600">{{ formatMoney(row.paid_amount) }} {{ row.currency || '' }}</div>
              </div>
              <p v-if="!(estadoCuenta?.pagos || []).length" class="text-sm text-zinc-500">Aucun paiement recent.</p>
            </div>
          </article>
        </div>
      </section>
    </template>
  </KioskLayout>
</template>
