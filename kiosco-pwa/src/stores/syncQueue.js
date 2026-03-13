import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { reportarConsumo, aprobarCalidad, subirConteoFisico, postCheckin } from '../api/kiosco'

export const useSyncQueueStore = defineStore('syncQueue', () => {
  const queue = ref([])
  const isSyncing = ref(false)

  const pendingCount = computed(() => queue.value.length)
  const hasPending = computed(() => pendingCount.value > 0)

  // Enqueue a failed operation
  function enqueueOperation(type, payload, context = {}) {
    const id = Date.now().toString(36) + Math.random().toString(36).substr(2)
    queue.value.push({
      id,
      type,
      payload,
      context,
      timestamp: new Date().toISOString(),
      retryCount: 0,
      lastError: null
    })
    return id
  }

  // Remove operation from queue (success or manual discard)
  function removeOperation(id) {
    queue.value = queue.value.filter(op => op.id !== id)
  }

  // Attempt to sync all pending operations
  async function syncAll() {
    if (isSyncing.value || !hasPending.value) return false
    
    // Only attempt sync if we think we might be online
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false

    isSyncing.value = true
    let successCount = 0

    // Process sequentially to avoid rapid fire errors
    for (const op of [...queue.value]) {
      try {
        let result = null
        if (op.type === 'EP4_REPORTAR_CONSUMO') {
          result = await reportarConsumo(
            op.payload.workOrder, 
            op.payload.lotesUsados, 
            op.payload.consumosExtra
          )
        } else if (op.type === 'EP7_APROBAR_CALIDAD') {
          result = await aprobarCalidad(op.payload)
        } else if (op.type === 'EP_REC_5_SUBIR_CONTEO') {
          result = await subirConteoFisico(op.payload.warehouse, op.payload.conteo)
        } else if (op.type === 'B2B_POST_CHECKIN') {
          result = await postCheckin(op.payload)
        }

        const isSuccess = (result && result.success) || (result?.status === 'success')
        if (isSuccess) {
          removeOperation(op.id)
          successCount++
        } else {
           op.retryCount++
           op.lastError = result?.message_fr ?? 'Erreur lors du traitement differe.'
        }
      } catch (err) {
        op.retryCount++
        op.lastError = err?.message_fr ?? err.message ?? 'Connexion echouee.'
      }
    }

    isSyncing.value = false
    return successCount > 0
  }

  return {
    queue,
    isSyncing,
    pendingCount,
    hasPending,
    enqueueOperation,
    removeOperation,
    syncAll
  }
}, {
  persist: {
    storage: localStorage,
    paths: ['queue']
  }
})
