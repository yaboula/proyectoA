<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import SelectButton from 'primevue/selectbutton'
import Message from 'primevue/message'
import Divider from 'primevue/divider'
import Skeleton from 'primevue/skeleton'
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

function buildDefaultRows() {
  return [
    { id: crypto.randomUUID(), name: 'pH', value: 8.2, numeric: true },
    { id: crypto.randomUUID(), name: 'viscosité KU', value: 95, numeric: true },
    { id: crypto.randomUUID(), name: 'aspect', value: 'Conforme', numeric: false },
  ]
}

function resetForm(lot) {
  selectedLot.value = lot
  drawerVisible.value = !!lot
  selectedDecision.value = 'Approved'
  quantity.value = lot ? Math.min(1, Number(lot.qty) || 1) || 1 : 1
  remarks.value = lot ? `Contrôle laboratoire du lot ${lot.batch_no}` : ''
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
      .some((value) => String(value).toLowerCase().includes(needle))
  )
})

const metrics = computed(() => {
  const totalLots = lotes.value.length
  const totalQty = lotes.value.reduce((sum, lot) => sum + Number(lot.qty || 0), 0)
  const oldestDate = [...lotes.value]
    .map((lot) => lot.fecha_fabricacion)
    .filter(Boolean)
    .sort()[0]

  return [
    {
      label: 'Lots en attente',
      value: totalLots,
      icon: ScanSearch,
      tone: 'from-teal-400/18 to-transparent',
    },
    {
      label: 'Volume sous quarantaine',
      value: `${totalQty.toFixed(1)} Nos`,
      icon: Package,
      tone: 'from-cyan-400/18 to-transparent',
    },
    {
      label: 'Plus ancien lot',
      value: oldestDate || 'Aujourd’hui',
      icon: CalendarClock,
      tone: 'from-orange-400/18 to-transparent',
    },
  ]
})

function addParameterRow() {
  parameterRows.value.push({
    id: crypto.randomUUID(),
    name: '',
    value: '',
    numeric: false,
  })
}

function removeParameterRow(id) {
  if (parameterRows.value.length === 1) return
  parameterRows.value = parameterRows.value.filter((row) => row.id !== id)
}

function serializeParameters() {
  const result = {}
  for (const row of parameterRows.value) {
    const parameter = row.name.trim()
    if (!parameter) continue

    if (row.numeric) {
      result[parameter] = Number(row.value)
    } else {
      result[parameter] = String(row.value ?? '').trim()
    }
  }
  return result
}

function validateForm() {
  if (!selectedLot.value) return 'Aucun lot sélectionné.'
  if (!quantity.value || Number(quantity.value) <= 0) return 'La quantité doit être supérieure à zéro.'
  if (Number(quantity.value) > Number(selectedLot.value.qty)) return 'La quantité dépasse le stock disponible en quarantaine.'

  const params = serializeParameters()
  if (Object.keys(params).length === 0) return 'Ajoutez au moins un paramètre laboratoire.'

  for (const [key, value] of Object.entries(params)) {
    if (!key || value === '' || Number.isNaN(value)) {
      return 'Chaque paramètre doit avoir un nom et une valeur valide.'
    }
  }

  return null
}

async function loadLots() {
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
    toast.add({
      severity: 'warn',
      summary: 'Saisie incomplète',
      detail: validationError,
      life: 3500,
    })
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
      summary: result.quality_status === 'Accepted' ? 'Lot libéré' : 'Lot maintenu',
      detail: result.message_fr,
      life: 4500,
    })

    await loadLots()
    drawerVisible.value = false
    selectedLot.value = null
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Validation impossible',
      detail: err?.message_fr ?? 'Erreur laboratoire inattendue.',
      life: 5000,
    })
  } finally {
    submitting.value = false
  }
}

function openLot(lot) {
  resetForm(lot)
}

onMounted(loadLots)
</script>

<template>
  <div class="min-h-dvh px-5 py-5 text-slate-100">
    <section class="mx-auto flex max-w-7xl flex-col gap-5">
      <div class="glass-panel overflow-hidden rounded-[28px] border border-white/10 p-6 shadow-[0_20px_70px_rgba(0,0,0,0.34)] md:p-7">
        <div class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div class="space-y-4">
            <div class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-300">
              <FlaskConical :size="14" />
              Laboratory Release Desk
            </div>
            <div>
              <h1 class="text-4xl font-black tracking-tight text-white md:text-5xl">Laboratoire qualité</h1>
              <p class="mt-3 max-w-3xl text-base leading-7 text-slate-300">
                Vue complète des lots en quarantaine, décision qualité, libération immédiate et traçabilité native ERPNext dans une seule console d’analyse.
              </p>
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
            <Button
              label="Retour aux modules"
              severity="secondary"
              class="!h-12 !rounded-2xl !border !border-white/10 !bg-white/6 !px-4 !text-slate-100 hover:!bg-white/10"
              @click="router.push({ name: 'hub' })"
            >
              <template #icon>
                <ArrowLeft :size="18" />
              </template>
            </Button>
            <Button
              label="Actualiser"
              class="!h-12 !rounded-2xl !border-0 !bg-gradient-to-r !from-teal-400 !to-emerald-400 !px-5 !font-bold !text-slate-950"
              @click="loadLots"
            >
              <template #icon>
                <RefreshCw :size="18" :class="{ 'animate-spin': loading }" />
              </template>
            </Button>
          </div>
        </div>
      </div>

      <div class="grid gap-4 lg:grid-cols-3">
        <Card
          v-for="metric in metrics"
          :key="metric.label"
          class="metric-card overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/50"
        >
          <template #content>
            <div class="relative overflow-hidden rounded-[20px] border border-white/8 p-5">
              <div class="absolute inset-0 bg-gradient-to-br" :class="metric.tone" />
              <div class="relative z-10 flex items-start justify-between gap-4">
                <div>
                  <div class="text-xs uppercase tracking-[0.22em] text-slate-500">{{ metric.label }}</div>
                  <div class="mt-2 text-3xl font-black text-white">{{ metric.value }}</div>
                </div>
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-black/20 text-slate-100">
                  <component :is="metric.icon" :size="22" />
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <div class="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div class="space-y-5">
          <Card class="overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/50">
            <template #content>
              <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <div class="text-xs uppercase tracking-[0.24em] text-slate-500">Recherche</div>
                  <div class="mt-2 text-2xl font-black text-white">Lots en quarantaine</div>
                </div>
                <div class="relative w-full md:max-w-sm">
                  <Search :size="18" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                  <InputText
                    v-model="query"
                    placeholder="Item, lot, date..."
                    class="!h-12 !w-full !rounded-2xl !border-white/10 !bg-white/6 !pl-11 !text-slate-100 placeholder:!text-slate-500"
                  />
                </div>
              </div>
            </template>
          </Card>

          <div v-if="loading" class="grid gap-4 md:grid-cols-2">
            <Card v-for="n in 4" :key="n" class="rounded-[24px] border border-white/8 bg-slate-950/45">
              <template #content>
                <div class="space-y-3 p-1">
                  <Skeleton width="8rem" height="1rem" class="!rounded-full" />
                  <Skeleton width="14rem" height="2rem" class="!rounded-xl" />
                  <Skeleton width="10rem" height="1rem" class="!rounded-xl" />
                  <Skeleton width="100%" height="6rem" class="!rounded-2xl" />
                </div>
              </template>
            </Card>
          </div>

          <Message v-else-if="error" severity="error" class="!rounded-2xl !border !border-rose-400/25 !bg-rose-400/10 !text-rose-100">
            {{ error }}
          </Message>

          <div v-else-if="filteredLots.length === 0" class="empty-state rounded-[28px] border border-dashed border-white/10 bg-slate-950/35 p-10 text-center">
            <div class="mx-auto flex h-18 w-18 items-center justify-center rounded-3xl bg-white/6 text-slate-400">
              <ScanSearch :size="36" />
            </div>
            <h2 class="mt-5 text-2xl font-black text-white">Aucun lot visible</h2>
            <p class="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-400">
              La quarantaine est vide ou votre filtre masque tous les résultats. Rafraîchissez les données ou simplifiez la recherche.
            </p>
          </div>

          <div v-else class="grid gap-4 md:grid-cols-2">
            <Card
              v-for="lot in filteredLots"
              :key="`${lot.item_code}-${lot.batch_no}`"
              class="lot-card overflow-hidden rounded-[26px] border border-white/10 bg-slate-950/48 shadow-[0_16px_40px_rgba(0,0,0,0.22)]"
            >
              <template #content>
                <div class="space-y-5">
                  <div class="flex items-start justify-between gap-4">
                    <div class="space-y-3">
                      <Tag :value="lot.batch_no" rounded class="!rounded-full !bg-teal-400/12 !px-3 !py-1 !text-[11px] !font-semibold !tracking-[0.18em] !text-teal-100" />
                      <div>
                        <h3 class="text-2xl font-black leading-tight text-white">{{ lot.item_name }}</h3>
                        <p class="mt-1 text-sm text-slate-400">{{ lot.item_code }}</p>
                      </div>
                    </div>
                    <div class="flex h-14 w-14 items-center justify-center rounded-3xl border border-white/10 bg-white/6 text-orange-200">
                      <Beaker :size="24" />
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-3 text-sm text-slate-300">
                    <div class="rounded-2xl border border-white/8 bg-white/5 p-3">
                      <div class="text-slate-500">Stock disponible</div>
                      <div class="mt-1 text-xl font-black text-white">{{ lot.qty }} {{ lot.uom }}</div>
                    </div>
                    <div class="rounded-2xl border border-white/8 bg-white/5 p-3">
                      <div class="text-slate-500">Fabrication</div>
                      <div class="mt-1 font-semibold text-white">{{ lot.fecha_fabricacion || 'N/A' }}</div>
                    </div>
                  </div>

                  <Button
                    label="Lancer l’inspection"
                    class="!h-13 !w-full !rounded-2xl !border-0 !bg-gradient-to-r !from-orange-400 !to-amber-300 !font-black !uppercase !tracking-[0.16em] !text-slate-950"
                    @click="openLot(lot)"
                  >
                    <template #icon>
                      <ArrowRightLeft :size="18" />
                    </template>
                  </Button>
                </div>
              </template>
            </Card>
          </div>
        </div>

        <div class="space-y-5">
          <Card class="overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/50">
            <template #content>
              <div class="space-y-4">
                <div class="flex items-center gap-3">
                  <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/12 text-emerald-300">
                    <Sparkles :size="22" />
                  </div>
                  <div>
                    <div class="text-xs uppercase tracking-[0.22em] text-slate-500">Dernière action</div>
                    <div class="text-2xl font-black text-white">Journal immédiat</div>
                  </div>
                </div>

                <div v-if="auditTrail" class="rounded-[24px] border border-white/10 bg-white/5 p-5">
                  <div class="flex items-center justify-between gap-3">
                    <Tag
                      :value="auditTrail.status === 'Accepted' ? 'Lot approuvé' : 'Lot rejeté'"
                      rounded
                      :class="auditTrail.status === 'Accepted'
                        ? '!rounded-full !bg-emerald-400/14 !px-3 !py-1 !text-emerald-100'
                        : '!rounded-full !bg-rose-400/14 !px-3 !py-1 !text-rose-100'"
                    />
                    <div class="text-xs uppercase tracking-[0.2em] text-slate-500">{{ auditTrail.at }}</div>
                  </div>
                  <div class="mt-4 space-y-2 text-sm text-slate-300">
                    <div><span class="text-slate-500">Lot:</span> {{ auditTrail.batchNo }}</div>
                    <div><span class="text-slate-500">QI:</span> {{ auditTrail.qualityInspection }}</div>
                    <div v-if="auditTrail.stockEntry"><span class="text-slate-500">Stock Entry:</span> {{ auditTrail.stockEntry }}</div>
                    <div><span class="text-slate-500">Quantité:</span> {{ auditTrail.qty }}</div>
                    <div class="pt-2 text-slate-200">{{ auditTrail.message }}</div>
                  </div>
                </div>
                <div v-else class="rounded-[24px] border border-dashed border-white/10 bg-white/4 p-6 text-sm leading-7 text-slate-400">
                  Les décisions qualité validées apparaîtront ici avec leurs documents ERPNext pour laisser un repère visuel immédiat à l’équipe.
                </div>
              </div>
            </template>
          </Card>

          <Card class="overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/50">
            <template #content>
              <div class="space-y-4">
                <div class="text-xs uppercase tracking-[0.22em] text-slate-500">Cadre métier</div>
                <div class="text-2xl font-black text-white">Décision assistée</div>
                <Divider class="!my-0 !border-white/8" />
                <div class="space-y-3 text-sm leading-7 text-slate-300">
                  <div class="rounded-2xl border border-emerald-400/16 bg-emerald-400/8 p-4">
                    <div class="flex items-center gap-2 text-emerald-100"><BadgeCheck :size="16" /> Approuvé</div>
                    <div class="mt-1 text-slate-200">Le lot est déplacé vers le stock vendable et l’inspection reste liée au document de libération.</div>
                  </div>
                  <div class="rounded-2xl border border-rose-400/16 bg-rose-400/8 p-4">
                    <div class="flex items-center gap-2 text-rose-100"><ShieldAlert :size="16" /> Rejeté</div>
                    <div class="mt-1 text-slate-200">Le lot reste en quarantaine et l’inspection référence le document qui a créé le stock retenu.</div>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </section>

    <Drawer v-model:visible="drawerVisible" position="right" class="!w-full !max-w-[38rem] !border-l !border-white/10 !bg-[#091119] !text-slate-100">
      <template #header>
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-orange-400/12 text-orange-200">
            <FlaskConical :size="20" />
          </div>
          <div>
            <div class="text-xs uppercase tracking-[0.2em] text-slate-500">Inspection en cours</div>
            <div class="text-lg font-black text-white">{{ selectedLot?.batch_no }}</div>
          </div>
        </div>
      </template>

      <div v-if="selectedLot" class="space-y-5 pb-8">
        <div class="rounded-[24px] border border-white/10 bg-white/5 p-5">
          <div class="text-sm text-slate-400">Produit</div>
          <div class="mt-1 text-2xl font-black text-white">{{ selectedLot.item_name }}</div>
          <div class="mt-1 text-sm text-slate-500">{{ selectedLot.item_code }}</div>
          <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300">
            <div class="rounded-2xl border border-white/8 bg-black/16 p-3">
              <div class="text-slate-500">Disponible</div>
              <div class="mt-1 font-bold text-white">{{ selectedLot.qty }} {{ selectedLot.uom }}</div>
            </div>
            <div class="rounded-2xl border border-white/8 bg-black/16 p-3">
              <div class="text-slate-500">Date</div>
              <div class="mt-1 font-bold text-white">{{ selectedLot.fecha_fabricacion }}</div>
            </div>
          </div>
        </div>

        <div class="space-y-3">
          <div class="text-xs uppercase tracking-[0.22em] text-slate-500">Verdict</div>
          <SelectButton
            v-model="selectedDecision"
            :options="decisionOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            class="decision-switch w-full"
          />
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-2">
            <label class="text-xs uppercase tracking-[0.22em] text-slate-500">Quantité inspectée</label>
            <InputNumber
              v-model="quantity"
              :min="0"
              :max="Number(selectedLot.qty)"
              :min-fraction-digits="0"
              :max-fraction-digits="2"
              fluid
              input-class="w-full"
            />
          </div>
          <div class="space-y-2">
            <label class="text-xs uppercase tracking-[0.22em] text-slate-500">Référence lot</label>
            <InputText :model-value="selectedLot.batch_no" disabled class="!h-12 !w-full !rounded-2xl !border-white/10 !bg-white/6 !text-slate-300" />
          </div>
        </div>

        <div class="space-y-4 rounded-[24px] border border-white/10 bg-white/5 p-5">
          <div class="flex items-center justify-between gap-4">
            <div>
              <div class="text-xs uppercase tracking-[0.22em] text-slate-500">Mesures laboratoire</div>
              <div class="mt-1 text-xl font-black text-white">Paramètres</div>
            </div>
            <Button
              label="Ajouter"
              severity="secondary"
              class="!h-11 !rounded-2xl !border !border-white/10 !bg-white/6 !px-4 !text-slate-100"
              @click="addParameterRow"
            >
              <template #icon>
                <Plus :size="16" />
              </template>
            </Button>
          </div>

          <div class="space-y-3">
            <div v-for="row in parameterRows" :key="row.id" class="grid gap-3 rounded-[22px] border border-white/8 bg-black/16 p-4 md:grid-cols-[1.1fr_0.9fr_auto]">
              <div class="space-y-2">
                <label class="text-xs uppercase tracking-[0.2em] text-slate-500">Paramètre</label>
                <InputText v-model="row.name" class="!h-11 !w-full !rounded-2xl !border-white/10 !bg-white/6 !text-slate-100" />
              </div>
              <div class="space-y-2">
                <label class="text-xs uppercase tracking-[0.2em] text-slate-500">Valeur</label>
                <InputNumber
                  v-if="row.numeric"
                  v-model="row.value"
                  :min-fraction-digits="0"
                  :max-fraction-digits="2"
                  fluid
                />
                <InputText v-else v-model="row.value" class="!h-11 !w-full !rounded-2xl !border-white/10 !bg-white/6 !text-slate-100" />
              </div>
              <div class="flex flex-col justify-end gap-2 md:items-end">
                <Button
                  :label="row.numeric ? 'Num.' : 'Texte'"
                  severity="secondary"
                  class="!h-11 !rounded-2xl !border !border-white/10 !bg-white/6 !px-4 !text-slate-100"
                  @click="row.numeric = !row.numeric"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  class="!h-10 !w-10 !text-rose-300"
                  @click="removeParameterRow(row.id)"
                >
                  <template #icon>
                    <Trash2 :size="16" />
                  </template>
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-xs uppercase tracking-[0.22em] text-slate-500">Remarques</label>
          <Textarea v-model="remarks" rows="4" auto-resize class="!w-full !rounded-[22px] !border-white/10 !bg-white/6 !text-slate-100" />
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <Button
            label="Annuler"
            severity="secondary"
            class="!h-14 !rounded-2xl !border !border-white/10 !bg-white/6 !font-bold !text-slate-100"
            @click="drawerVisible = false"
          />
          <Button
            :label="selectedDecision === 'Approved' ? 'Valider et libérer' : 'Enregistrer le rejet'"
            :loading="submitting"
            class="!h-14 !rounded-2xl !border-0 !font-black !uppercase !tracking-[0.14em]"
            :class="selectedDecision === 'Approved'
              ? '!bg-gradient-to-r !from-emerald-400 !to-teal-300 !text-slate-950'
              : '!bg-gradient-to-r !from-rose-400 !to-orange-300 !text-slate-950'"
            @click="submitInspection"
          />
        </div>
      </div>
    </Drawer>
  </div>
</template>