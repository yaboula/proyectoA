<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  BadgeCheck,
  Building2,
  CircleCheckBig,
  Loader2,
  MapPin,
  Phone,
  Receipt,
  TriangleAlert,
  UserPlus,
} from 'lucide-vue-next'
import KioskLayout from '../components/KioskLayout.vue'
import FullScreenOverlay from '../components/FullScreenOverlay.vue'
import { crearClienteB2B } from '../api/customerPortal'

const router = useRouter()

// ── Formulario ────────────────────────────────────────────────────────────────
const form = ref({
  customer_name: '',
  customer_group: 'Droguerie',
  territory: 'Rabat',
  mobile_no: '',
  email_id: '',
  tax_id: '',
  address_line1: '',
  city: '',
  representant_name: '',
})

const GRUPOS = ['Droguerie', 'Distributeur', 'Grossiste']
const TERRITOIRES = ['Casablanca', 'Rabat']

// ── Estado ────────────────────────────────────────────────────────────────────
const submitting = ref(false)
const errorMsg = ref('')
const successOverlay = ref(false)
const createdCustomerId = ref('')

// ── Validación ────────────────────────────────────────────────────────────────
function validate() {
  if (!form.value.customer_name.trim()) return 'La raison sociale est obligatoire.'
  if (form.value.mobile_no && !/^[+\d\s\-()]{6,20}$/.test(form.value.mobile_no))
    return 'Numéro de téléphone invalide.'
  if (form.value.email_id && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email_id))
    return 'Adresse e-mail invalide.'
  return null
}

async function onSubmit() {
  const err = validate()
  if (err) { errorMsg.value = err; return }

  submitting.value = true
  errorMsg.value = ''

  try {
    const res = await crearClienteB2B({ ...form.value })
    createdCustomerId.value = res.customer_id ?? res.customer_name ?? ''
    successOverlay.value = true
  } catch (e) {
    errorMsg.value =
      e?.message_fr ||
      e?.message ||
      e?.exc_type === 'ValidationError'
        ? e.message || 'Erreur de validation.'
        : 'Impossible de créer le client. Réessayez.'
  } finally {
    submitting.value = false
  }
}

function onSuccessDismiss() {
  // Redirigir al catálogo con el nuevo cliente ya seleccionable
  router.push({ name: 'catalogo-stock' })
}
</script>

<template>
  <KioskLayout maxWidth="5xl">

    <FullScreenOverlay
      v-if="successOverlay"
      variant="success"
      :title="`Client créé !`"
      :subtitle="createdCustomerId"
      hint="Appuyez pour continuer vers le catalogue"
      clickable
      @click="onSuccessDismiss"
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
              <UserPlus :size="13" />
              Nouveau client B2B
            </div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">
              Enregistrement client
            </h1>
            <p class="mt-1 text-sm text-zinc-500">
              Crée le client directement dans ERPNext · Address et Contact synchronisés
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Formulario -->
    <form class="kiosk-panel p-5 md:p-6 space-y-5" @submit.prevent="onSubmit">

      <!-- Raison sociale -->
      <div>
        <div class="gcma-section-label mb-2 flex items-center gap-1.5">
          <Building2 :size="13" /> Raison sociale *
        </div>
        <input
          v-model="form.customer_name"
          type="text"
          autocomplete="organization"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl text-zinc-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          placeholder="Droguerie El Wafa SARL..."
          required
        />
      </div>

      <!-- Groupe & Territoire -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <div class="gcma-section-label mb-2">Groupe *</div>
          <div class="flex flex-col gap-1.5">
            <button
              v-for="g in GRUPOS"
              :key="g"
              type="button"
              class="rounded-md border py-3 text-sm font-bold transition"
              :class="form.customer_group === g
                ? 'border-blue-500 bg-blue-600 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300'"
              @click="form.customer_group = g"
            >
              {{ g }}
            </button>
          </div>
        </div>
        <div>
          <div class="gcma-section-label mb-2">Territoire *</div>
          <div class="flex flex-col gap-1.5">
            <button
              v-for="t in TERRITOIRES"
              :key="t"
              type="button"
              class="rounded-md border py-3 text-sm font-bold transition"
              :class="form.territory === t
                ? 'border-blue-500 bg-blue-600 text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300'"
              @click="form.territory = t"
            >
              {{ t }}
            </button>
          </div>
        </div>
      </div>

      <!-- Téléphone -->
      <div>
        <div class="gcma-section-label mb-2 flex items-center gap-1.5">
          <Phone :size="13" /> Téléphone
        </div>
        <input
          v-model="form.mobile_no"
          type="tel"
          autocomplete="tel"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="+212 6XX XXX XXX"
        />
      </div>

      <!-- ICE (numéro fiscal Maroc) -->
      <div>
        <div class="gcma-section-label mb-2 flex items-center gap-1.5">
          <Receipt :size="13" /> ICE (identifiant fiscal)
        </div>
        <input
          v-model="form.tax_id"
          type="text"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-mono text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="000 000 000 00000"
        />
      </div>

      <!-- Adresse -->
      <div>
        <div class="gcma-section-label mb-2 flex items-center gap-1.5">
          <MapPin :size="13" /> Adresse
        </div>
        <input
          v-model="form.address_line1"
          type="text"
          autocomplete="street-address"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="Rue, Quartier..."
        />
        <input
          v-model="form.city"
          type="text"
          autocomplete="address-level2"
          class="mt-2 w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="Ville"
        />
      </div>

      <!-- Representant -->
      <div>
        <div class="gcma-section-label mb-2 flex items-center gap-1.5">
          <BadgeCheck :size="13" /> Nom du représentant / gérant
        </div>
        <input
          v-model="form.representant_name"
          type="text"
          autocomplete="name"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="Mohammed El Alami..."
        />
      </div>

      <!-- E-mail -->
      <div>
        <div class="gcma-section-label mb-2">E-mail</div>
        <input
          v-model="form.email_id"
          type="email"
          autocomplete="email"
          class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-base text-zinc-900 focus:border-blue-600 focus:outline-none"
          placeholder="contact@droguerie.ma"
        />
      </div>

      <!-- Info sync ERPNext -->
      <div class="kiosk-panel-soft rounded-md p-4 text-xs text-zinc-500 space-y-1">
        <div class="flex items-center gap-1.5 font-semibold text-zinc-600">
          <CircleCheckBig :size="13" class="text-green-600" />
          Synchronisation ERPNext automatique
        </div>
        <div>• Customer créé dans le groupe sélectionné</div>
        <div>• Address (Billing) liée via Dynamic Link</div>
        <div>• Contact représentant lié au Customer</div>
        <div>• Limite de crédit: 0 MAD par défaut (à configurer dans ERP)</div>
      </div>

      <!-- Error -->
      <div
        v-if="errorMsg"
        class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex items-start gap-2"
      >
        <TriangleAlert :size="16" class="shrink-0 mt-0.5" />
        {{ errorMsg }}
      </div>

      <!-- Submit -->
      <button
        type="submit"
        :disabled="submitting || !form.customer_name.trim()"
        class="h-16 w-full rounded-md bg-blue-600 text-sm font-black uppercase tracking-[0.14em] text-white active:bg-blue-700 disabled:opacity-40 transition flex items-center justify-center gap-2"
      >
        <Loader2 v-if="submitting" :size="18" class="animate-spin" />
        <UserPlus v-else :size="18" />
        {{ submitting ? 'Création en cours...' : 'Créer ce client dans ERPNext' }}
      </button>

    </form>

  </KioskLayout>
</template>
