<script setup>
/**
 * LaboratoireQC -- Quality lab inspection console.
 *
 * Refactored: KioskLayout, EmptyState, plain HTML for simple wrappers,
 * kept PrimeVue Drawer + form inputs (SelectButton, InputNumber, InputText, Textarea).
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import SelectButton from 'primevue/selectbutton'
import KioskLayout from '../components/KioskLayout.vue'
import EmptyState from '../components/EmptyState.vue'
import { useOperarioStore } from '../stores/operario'
import { aprobarCalidad, getLotesCuarentena } from '../api/kiosco'
import {
  FlaskConical,
  RefreshCw,
  Search,
  ArrowLeft,
  ScanSearch,
  BadgeCheck,
  ShieldAlert,
  Package,
  CalendarClock,
  ArrowRightLeft,
  Plus,
  Trash2,
  Sparkles,
  Beaker,
  X,
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToast()
const store = useOperarioStore()

const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const query = ref('')
const lotes = ref([])
const selectedLot = ref(null)
const drawerVisible = ref(false)
const remarks = ref('')
const selectedDecision = ref('Approved')
const quantity = ref(1)
const auditTrail = ref(null)

const decisionOptions = [
  { label: 'Approuver', value: 'Approved' },
  { label: 'Rejeter', value: 'Rejected' },
]

const parameterRows = ref([])

let _rowSeq = 0
function nextRowId() { return String(++_rowSeq) }

function buildDefaultRows() {
  return [
    { id: nextRowId(), name: 'pH', value: 8.2, numeric: true },
    { id: nextRowId(), name: 'viscosite KU', value: 95, numeric: true },
    { id: nextRowId(), name: 'aspect', value: 'Conforme', numeric: false },
  ]
}

function resetForm(lot) {
  selectedLot.value = lot
  drawerVisible.value = !!lot
  selectedDecision.value = 'Approved'
  quantity.value = lot ? Math.min(1, Number(lot.qty) || 1) || 1 : 1
  remarks.value = lot ? `Controle laboratoire du lot ${lot.batch_no}` : ''
  parameterRows.value = buildDefaultRows()
}

watch(selectedDecision, (decision) => {
  const aspectRow = parameterRows.value.find((row) => row.name.toLowerCase() === 'aspect')
  if (!aspectRow) return
  aspectRow.value = decision === 'Approved' ? 'Conforme' : 'Non conforme'
})

const filteredLots = computed(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return lotes.value
  return lotes.value.filter((lot) =>
    [lot.item_code, lot.item_name, lot.batch_no, lot.fecha_fabricacion]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(needle))
  )
})

const metrics = computed(() => {
  const totalLots = lotes.value.length
  const totalQty = lotes.value.reduce((sum, l) => sum + Number(l.qty || 0), 0)
  const oldestDate = [...lotes.value].map((l) => l.fecha_fabricacion).filter(Boolean).sort()[0]
  return [
    {
      label: 'Lots en attente',
      value: totalLots,
      icon: ScanSearch,
      cardClass: 'border-green-200 bg-green-50',
      iconClass: 'text-green-600 bg-green-100',
    },
    {
      label: 'Volume sous quarantaine',
      value: `${totalQty.toFixed(1)} Nos`,
      icon: Package,
      cardClass: 'border-cyan-200 bg-cyan-50',
      iconClass: 'text-cyan-600 bg-cyan-100',
    },
    {
      label: 'Plus ancien lot',
      value: oldestDate || "Aujourd'hui",
      icon: CalendarClock,
      cardClass: 'border-zinc-200 bg-zinc-50',
      iconClass: 'text-zinc-600 bg-zinc-100',
    },
  ]
})

function addParameterRow() {
  parameterRows.value.push({ id: nextRowId(), name: '', value: '', numeric: false })
}

function removeParameterRow(id) {
  if (parameterRows.value.length === 1) return
  parameterRows.value = parameterRows.value.filter((r) => r.id !== id)
}

function serializeParameters() {
  const result = {}
  for (const row of parameterRows.value) {
    const p = row.name.trim()
    if (!p) continue
    result[p] = row.numeric ? Number(row.value) : String(row.value ?? '').trim()
  }
  return result
}

function validateForm() {
  if (!selectedLot.value) return 'Aucun lot selectionne.'
  if (!quantity.value || Number(quantity.value) <= 0) return 'La quantite doit etre superieure a zero.'
  if (Number(quantity.value) > Number(selectedLot.value.qty)) return 'La quantite depasse le stock disponible.'
  const params = serializeParameters()
  if (Object.keys(params).length === 0) return 'Ajoutez au moins un parametre laboratoire.'
  for (const [key, value] of Object.entries(params)) {
    if (!key || value === '' || Number.isNaN(value)) return 'Chaque parametre doit avoir un nom et une valeur valide.'
  }
  return null
}

async function loadLots() {
  const hasSession = await store.ensureSession()
  if (!hasSession || !store.hasModule('quality')) {
    router.push({ name: 'hub' })
    return
  }
  loading.value = true
  error.value = ''
  try {
    const data = await getLotesCuarentena()
    lotes.value = data.lotes ?? []
  } catch (err) {
    error.value = err?.message_fr ?? 'Impossible de charger les lots du laboratoire.'
    lotes.value = []
  } finally {
    loading.value = false
  }
}

async function submitInspection() {
  const validationError = validateForm()
  if (validationError) {
    toast.add({ severity: 'warn', summary: 'Saisie incomplete', detail: validationError, life: 3500 })
    return
  }
  submitting.value = true
  try {
    const payload = {
      itemCode: selectedLot.value.item_code,
      batchNo: selectedLot.value.batch_no,
      qty: quantity.value,
      parametros: serializeParameters(),
      aprobada: selectedDecision.value === 'Approved' ? '1' : '0',
      resultado: selectedDecision.value,
      remarks: remarks.value.trim(),
    }
    const result = await aprobarCalidad(payload)
    auditTrail.value = {
      batchNo: result.batch_no,
      qty: result.qty,
      status: result.quality_status,
      qualityInspection: result.quality_inspection,
      stockEntry: result.stock_entry ?? null,
      message: result.message_fr,
      at: new Date().toLocaleString('fr-FR'),
    }
    toast.add({
      severity: result.quality_status === 'Accepted' ? 'success' : 'info',
      summary: result.quality_status === 'Accepted' ? 'Lot libere' : 'Lot maintenu',
      detail: result.message_fr,
      life: 4500,
    })
    await loadLots()
    drawerVisible.value = false
    selectedLot.value = null
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Validation impossible', detail: err?.message_fr ?? 'Erreur laboratoire inattendue.', life: 5000 })
  } finally {
    submitting.value = false
  }
}

const contentScrollRef = ref(null)

function onDrawerShow() {
  nextTick(() => {
    if (contentScrollRef.value) contentScrollRef.value.scrollTop = 0
  })
}

function openLot(lot) { resetForm(lot) }

onMounted(loadLots)
</script>

<template>
  <KioskLayout>
    <!-- Header -->
    <div class="kiosk-panel overflow-hidden rounded-md p-6 md:p-7">
      <div class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div class="space-y-4">
          <div class="kiosk-chip inline-flex items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.24em]">
            <FlaskConical :size="14" />
            Laboratory Release Desk
          </div>
          <div>
            <div class="gcma-section-label">Controle qualite</div>
            <h1 class="mt-2 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl md:text-4xl">Laboratoire qualite</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-500">
              Vue complete des lots en quarantaine, decision qualite, liberation immediate et tracabilite native ERPNext dans une seule console d'analyse.
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-3">
          <button @click="router.push({ name: 'hub' })"
                  class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 flex items-center gap-2 active:bg-zinc-50 transition">
            <ArrowLeft :size="18" />
            Retour aux modules
          </button>
          <button @click="loadLots"
                  class="h-12 rounded-md bg-blue-600 px-5 text-sm font-bold text-white flex items-center gap-2 active:bg-blue-700 transition">
            <RefreshCw :size="18" :class="{ 'animate-spin': loading }" />
            Actualiser
          </button>
        </div>
      </div>
    </div>

    <!-- Metrics -->
    <div class="grid gap-4 md:grid-cols-3 text-zinc-500">
      <div v-for="metric in metrics" :key="metric.label"
           class="kiosk-panel overflow-hidden rounded-md">
        <div class="gcma-data-row flex items-start justify-between gap-4 p-5" :class="metric.cardClass">
          <div>
            <div class="gcma-section-label">{{ metric.label }}</div>
            <div class="mt-2 text-3xl font-black text-zinc-900">{{ metric.value }}</div>
          </div>
          <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md" :class="metric.iconClass">
            <component :is="metric.icon" :size="22" />
          </div>
        </div>
      </div>
    </div>

    <!-- Main grid -->
    <div class="grid gap-4 sm:gap-5 lg:grid-cols-[1.15fr_0.85fr]">
      <!-- Left: lots list -->
      <div class="space-y-5">
        <!-- Search bar -->
        <div class="kiosk-panel overflow-hidden rounded-md p-5">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div class="gcma-section-label">Recherche</div>
              <div class="mt-2 text-2xl font-black text-zinc-900">Lots en quarantaine</div>
            </div>
            <div class="relative w-full md:max-w-sm">
              <Search :size="18" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400" />
              <InputText v-model="query"
                         placeholder="Item, lot, date..."
                         class="!h-12 !w-full !rounded-md !border-zinc-300 !bg-zinc-50 !pl-11 !text-zinc-900 placeholder:!text-zinc-400" />
            </div>
          </div>
        </div>

        <!-- Loading skeletons -->
        <div v-if="loading" class="grid gap-4 md:grid-cols-2">
          <div v-for="n in 4" :key="n" class="kiosk-panel-soft rounded-md p-5 space-y-3">
            <div class="h-4 w-32 animate-pulse rounded-md bg-zinc-200" />
            <div class="h-8 w-56 animate-pulse rounded-md bg-zinc-200" />
            <div class="h-4 w-40 animate-pulse rounded-md bg-zinc-200" />
            <div class="h-24 w-full animate-pulse rounded-md bg-zinc-200" />
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          {{ error }}
        </div>

        <!-- Empty state -->
        <EmptyState v-else-if="filteredLots.length === 0"
                    :icon="ScanSearch"
                    title="Aucun lot visible"
                    message="La quarantaine est vide ou votre filtre masque tous les resultats. Rafraichissez les donnees ou simplifiez la recherche." />

        <!-- Lot cards -->
        <div v-else class="grid gap-4 md:grid-cols-2">
          <article v-for="lot in filteredLots" :key="`${lot.item_code}-${lot.batch_no}`"
                   class="kiosk-panel overflow-hidden rounded-md">
            <div class="space-y-5 p-5">
              <div class="flex items-start justify-between gap-4">
                <div class="space-y-3">
                  <span class="kiosk-chip inline-block rounded-md px-3 py-2 text-[11px] font-semibold tracking-[0.18em]">
                    {{ lot.batch_no }}
                  </span>
                  <div>
                    <h3 class="text-2xl font-black leading-tight text-zinc-900">{{ lot.item_name }}</h3>
                    <p class="mt-1 text-sm text-zinc-500">{{ lot.item_code }}</p>
                  </div>
                </div>
                <div class="kiosk-icon-shell flex h-14 w-14 items-center justify-center rounded-md text-zinc-600">
                  <Beaker :size="24" />
                </div>
              </div>
              <div class="grid grid-cols-1 gap-3 text-sm text-zinc-500 sm:grid-cols-2">
                <div class="gcma-stat">
                  <div class="text-zinc-400">Stock disponible</div>
                  <div class="mt-1 text-xl font-black text-zinc-900">{{ lot.qty }} {{ lot.uom }}</div>
                </div>
                <div class="gcma-stat">
                  <div class="text-zinc-400">Fabrication</div>
                  <div class="mt-1 font-semibold text-zinc-900">{{ lot.fecha_fabricacion || 'N/A' }}</div>
                </div>
              </div>
              <button @click="openLot(lot)"
                      class="h-16 w-full rounded-md bg-blue-600 px-5 text-sm font-black uppercase tracking-[0.16em] text-white flex items-center justify-center gap-2 active:bg-blue-700 transition">
                <ArrowRightLeft :size="18" />
                Lancer l'inspection
              </button>
            </div>
          </article>
        </div>
      </div>

      <!-- Right: sidebar -->
      <div class="space-y-5">
        <!-- Audit trail -->
        <div class="kiosk-panel overflow-hidden rounded-md p-5">
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-blue-600">
                <Sparkles :size="22" />
              </div>
              <div>
                <div class="gcma-section-label">Derniere action</div>
                <div class="text-2xl font-black text-zinc-900">Journal immediat</div>
              </div>
            </div>
            <div v-if="auditTrail" class="gcma-data-row p-5">
              <div class="flex items-center justify-between gap-3">
                <span class="rounded-md px-3 py-2 text-[11px] font-semibold"
                      :class="auditTrail.status === 'Accepted' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
                  {{ auditTrail.status === 'Accepted' ? 'Lot approuve' : 'Lot rejete' }}
                </span>
                <div class="text-xs uppercase tracking-[0.2em] text-zinc-400">{{ auditTrail.at }}</div>
              </div>
              <div class="mt-4 space-y-2 text-sm text-zinc-500">
                <div><span class="text-zinc-400">Lot:</span> {{ auditTrail.batchNo }}</div>
                <div><span class="text-zinc-400">QI:</span> {{ auditTrail.qualityInspection }}</div>
                <div v-if="auditTrail.stockEntry"><span class="text-zinc-400">Stock Entry:</span> {{ auditTrail.stockEntry }}</div>
                <div><span class="text-zinc-400">Quantite:</span> {{ auditTrail.qty }}</div>
                <div class="pt-2 text-zinc-700">{{ auditTrail.message }}</div>
              </div>
            </div>
            <div v-else class="kiosk-panel-soft rounded-md border-dashed p-6 text-sm leading-7 text-zinc-500">
              Les decisions qualite validees apparaitront ici avec leurs documents ERPNext pour laisser un repere visuel immediat a l'equipe.
            </div>
          </div>
        </div>

        <!-- Decision guide -->
        <div class="kiosk-panel overflow-hidden rounded-md p-5">
          <div class="space-y-4">
            <div class="gcma-section-label">Cadre metier</div>
            <div class="text-2xl font-black text-zinc-900">Decision assistee</div>
            <hr class="border-zinc-200" />
            <div class="space-y-3 text-sm leading-7 text-zinc-500">
              <div class="gcma-data-row border border-green-200 bg-green-50 p-4">
                <div class="flex items-center gap-2 text-green-700"><BadgeCheck :size="16" /> Approuve</div>
                <div class="mt-1 text-zinc-600">Le lot est deplace vers le stock vendable et l'inspection reste liee au document de liberation.</div>
              </div>
              <div class="gcma-data-row border border-red-200 bg-red-50 p-4">
                <div class="flex items-center gap-2 text-red-700"><ShieldAlert :size="16" /> Rejete</div>
                <div class="mt-1 text-zinc-600">Le lot reste en quarantaine et l'inspection reference le document qui a cree le stock retenu.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer (PrimeVue -- #container slot = full layout control, scroll guaranteed) -->
    <Drawer v-model:visible="drawerVisible" position="right"
            class="!w-full !max-w-[38rem]" :pt="{ root: { class: '!p-0 !bg-transparent' } }"
            @show="onDrawerShow">
      <template #container="{ closeCallback }">
        <div class="flex h-full flex-col bg-white border-l border-zinc-200">

          <!-- Header (fixed) -->
          <div class="flex shrink-0 items-center justify-between gap-3 border-b border-zinc-200 p-5">
            <div class="flex items-center gap-3">
              <div class="kiosk-icon-shell flex h-11 w-11 items-center justify-center rounded-md text-zinc-600">
                <FlaskConical :size="20" />
              </div>
              <div>
                <div class="text-xs uppercase tracking-[0.2em] text-zinc-400">Inspection en cours</div>
                <div class="text-lg font-black text-zinc-900">{{ selectedLot?.batch_no }}</div>
              </div>
            </div>
            <button @click="closeCallback"
                    class="h-10 w-10 flex items-center justify-center rounded-md border border-zinc-200 text-zinc-400 active:bg-zinc-100 transition">
              <X :size="18" />
            </button>
          </div>

          <!-- Scrollable content -->
          <div ref="contentScrollRef" class="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
            <div v-if="selectedLot" class="space-y-5 pb-2">

              <!-- Product summary -->
              <div class="gcma-data-row p-5">
                <div class="text-sm text-zinc-500">Produit</div>
                <div class="mt-1 text-2xl font-black text-zinc-900">{{ selectedLot.item_name }}</div>
                <div class="mt-1 text-sm text-zinc-400">{{ selectedLot.item_code }}</div>
                <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-zinc-500">
                  <div class="rounded-md bg-zinc-50 border border-zinc-200 p-3">
                    <div class="text-zinc-400">Disponible</div>
                    <div class="mt-1 font-bold text-zinc-900">{{ selectedLot.qty }} {{ selectedLot.uom }}</div>
                  </div>
                  <div class="rounded-md bg-zinc-50 border border-zinc-200 p-3">
                    <div class="text-zinc-400">Date</div>
                    <div class="mt-1 font-bold text-zinc-900">{{ selectedLot.fecha_fabricacion }}</div>
                  </div>
                </div>
              </div>

              <!-- Verdict -->
              <div class="space-y-3">
                <div class="text-xs uppercase tracking-[0.22em] text-zinc-400">Verdict</div>
                <SelectButton v-model="selectedDecision" :options="decisionOptions"
                              option-label="label" option-value="value" :allow-empty="false"
                              class="decision-switch w-full" />
              </div>

              <!-- Quantity + ref -->
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <label class="text-xs uppercase tracking-[0.22em] text-zinc-400">Quantite inspectee</label>
                  <InputNumber v-model="quantity" :min="0" :max="Number(selectedLot.qty)"
                               :min-fraction-digits="0" :max-fraction-digits="2" fluid input-class="w-full" />
                </div>
                <div class="space-y-2">
                  <label class="text-xs uppercase tracking-[0.22em] text-zinc-400">Reference lot</label>
                  <InputText :model-value="selectedLot.batch_no" disabled
                             class="!h-12 !w-full !rounded-md !border-zinc-300 !bg-zinc-100 !text-zinc-500" />
                </div>
              </div>

              <!-- Parameters -->
              <div class="gcma-data-row space-y-4 p-5">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <div class="gcma-section-label">Mesures laboratoire</div>
                    <div class="mt-1 text-xl font-black text-zinc-900">Parametres</div>
                  </div>
                  <button @click="addParameterRow"
                          class="h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 flex items-center gap-2 active:bg-zinc-50 transition">
                    <Plus :size="16" />
                    Ajouter
                  </button>
                </div>
                <div class="space-y-3">
                  <div v-for="row in parameterRows" :key="row.id"
                       class="grid gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-4 md:grid-cols-[1.1fr_0.9fr_auto]">
                    <div class="space-y-2">
                      <label class="gcma-section-label">Parametre</label>
                      <InputText v-model="row.name" class="!h-14 !w-full !rounded-md !border-zinc-300 !bg-white !text-zinc-900" />
                    </div>
                    <div class="space-y-2">
                      <label class="gcma-section-label">Valeur</label>
                      <InputNumber v-if="row.numeric" v-model="row.value" :min-fraction-digits="0" :max-fraction-digits="2" fluid />
                      <InputText v-else v-model="row.value" class="!h-14 !w-full !rounded-md !border-zinc-300 !bg-white !text-zinc-900" />
                    </div>
                    <div class="flex flex-row items-center gap-2 md:flex-col md:items-end md:justify-end">
                      <button @click="row.numeric = !row.numeric"
                              class="flex-1 h-12 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-700 active:bg-zinc-50 transition md:flex-none">
                        {{ row.numeric ? 'Num.' : 'Texte' }}
                      </button>
                      <button @click="removeParameterRow(row.id)"
                              class="h-12 w-12 shrink-0 rounded-md text-red-500 flex items-center justify-center active:text-red-600 transition">
                        <Trash2 :size="16" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Remarks -->
              <div class="space-y-2">
                <label class="gcma-section-label">Remarques</label>
                <Textarea v-model="remarks" rows="4" auto-resize
                          class="!w-full !rounded-md !border-zinc-300 !bg-zinc-50 !text-zinc-900" />
              </div>

            </div>
          </div>

          <!-- Footer (fixed) -->
          <div class="shrink-0 border-t border-zinc-200 p-5">
            <div class="grid gap-3 sm:grid-cols-2">
              <button @click="closeCallback"
                      class="h-16 rounded-md border border-zinc-300 bg-white text-sm font-bold text-zinc-700 active:bg-zinc-50 transition">
                Annuler
              </button>
              <button @click="submitInspection" :disabled="submitting || !selectedLot"
                      class="h-16 rounded-md bg-blue-600 text-sm font-black uppercase tracking-[0.14em] text-white flex items-center justify-center gap-2 active:bg-blue-700 transition disabled:opacity-50">
                <RefreshCw v-if="submitting" :size="16" class="animate-spin" />
                {{ selectedDecision === 'Approved' ? 'Valider et liberer' : 'Enregistrer le rejet' }}
              </button>
            </div>
          </div>

        </div>
      </template>
    </Drawer>
  </KioskLayout>
</template>
