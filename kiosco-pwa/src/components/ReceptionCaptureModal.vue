<template>
  <Teleport to="body">
    <div v-if="open"
         class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-5"
         @click.self="emit('close')">
      <div class="w-full max-w-xl rounded-md border border-zinc-200 bg-white shadow-xl animate-fade-in">
        <div class="flex items-center justify-between border-b border-zinc-200 px-6 py-5">
          <div>
            <div class="gcma-section-label">Reception quai</div>
            <h2 class="mt-1 text-xl font-black text-zinc-900">Capturer la reception</h2>
          </div>
          <button @click="emit('close')"
                  class="flex h-12 w-12 items-center justify-center rounded-md border border-zinc-200 bg-zinc-50 text-zinc-500 active:bg-zinc-100 transition">
            <X :size="20" />
          </button>
        </div>

        <div class="space-y-5 px-6 py-6">
          <div class="gcma-data-row p-4">
            <div class="gcma-section-label">Article</div>
            <div class="mt-1 text-lg font-bold text-zinc-900">{{ item?.item_name }}</div>
            <div class="mt-2 text-sm text-zinc-500">{{ item?.item_code }} · reliquat {{ maxQtyLabel }} {{ item?.uom }}</div>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <label class="space-y-2">
              <span class="gcma-section-label">Quantite recue</span>
              <input v-model="form.qty"
                     type="number"
                     min="0"
                     step="any"
                     inputmode="decimal"
                     class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl font-bold text-zinc-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20" />
            </label>
            <label class="space-y-2">
              <span class="gcma-section-label">Lot fournisseur</span>
              <input v-model="form.supplierBatch"
                     type="text"
                     autocomplete="off"
                     class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-xl text-zinc-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20"
                     placeholder="LOT-FOURN-001" />
            </label>
          </div>

          <div class="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
            <label class="space-y-2">
              <span class="gcma-section-label">Date de peremption</span>
              <input v-model="form.expiryDate"
                     type="date"
                     :disabled="!item?.has_expiry_date"
                     class="w-full rounded-md border border-zinc-300 bg-white px-4 py-4 text-lg text-zinc-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/20 disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400" />
            </label>
            <div class="grid grid-cols-3 gap-2">
              <button @click="increment(1)"
                      type="button"
                      class="h-14 rounded-md border border-indigo-200 bg-indigo-50 px-3 text-sm font-bold text-indigo-700 active:bg-indigo-100 transition">
                +1
              </button>
              <button @click="increment(10)"
                      type="button"
                      class="h-14 rounded-md border border-indigo-200 bg-indigo-50 px-3 text-sm font-bold text-indigo-700 active:bg-indigo-100 transition">
                +10
              </button>
              <button @click="setMax"
                      type="button"
                      class="h-14 rounded-md border border-indigo-200 bg-indigo-600 px-3 text-sm font-black text-white active:bg-indigo-700 transition">
                MAX
              </button>
            </div>
          </div>

          <p v-if="validationMessage" class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {{ validationMessage }}
          </p>
        </div>

        <div class="flex gap-3 border-t border-zinc-200 px-6 py-5">
          <button @click="emit('close')"
                  type="button"
                  class="h-12 flex-1 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-600 active:bg-zinc-50 transition">
            Annuler
          </button>
          <button @click="submit"
                  type="button"
                  :disabled="submitting || !isValid"
                  class="h-16 flex-1 rounded-md bg-indigo-600 px-4 text-sm font-black uppercase tracking-[0.18em] text-white active:bg-indigo-700 disabled:opacity-40 transition">
            {{ submitting ? 'Enregistrement...' : 'Valider la reception' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  item: { type: Object, default: null },
  submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  qty: '',
  supplierBatch: '',
  expiryDate: '',
})

const maxQty = computed(() => Number(props.item?.qty_pending ?? 0))
const maxQtyLabel = computed(() => maxQty.value.toFixed(2).replace(/\.00$/, ''))
const parsedQty = computed(() => Number(form.qty || 0))
const isValid = computed(() => parsedQty.value > 0 && parsedQty.value <= maxQty.value)
const validationMessage = computed(() => {
  if (!form.qty) return ''
  if (parsedQty.value <= 0) return 'La quantite doit etre strictement positive.'
  if (parsedQty.value > maxQty.value) return 'La quantite depasse le reliquat disponible.'
  return ''
})

watch(() => [props.open, props.item], ([open]) => {
  if (!open) return
  form.qty = props.item?.qty_pending ? String(props.item.qty_pending) : ''
  form.supplierBatch = ''
  form.expiryDate = ''
}, { immediate: true })

function increment(step) {
  const nextValue = Math.min(maxQty.value, parsedQty.value + step)
  form.qty = nextValue > 0 ? String(nextValue) : String(step)
}

function setMax() {
  form.qty = String(maxQty.value)
}

function submit() {
  if (!isValid.value || props.submitting) return
  emit('submit', {
    qty: parsedQty.value,
    supplierBatch: form.supplierBatch.trim(),
    expiryDate: form.expiryDate || null,
  })
}
</script>
