import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getTareas } from '../api/kiosco'
import { useOperarioStore } from './operario'

export const usePokaYokeStore = defineStore('pokaYoke', () => {
  const operarioStore = useOperarioStore()

  // State
  const tarea = ref(null)
  const materials = ref([])
  const customExtras = ref([])

  // Computed
  const allValidated = computed(() => {
    return materials.value.length > 0 && materials.value.every(m => m.status === 'validated')
  })

  // Actions
  function initWorkflow(workOrder, company, warehouse) {
    if (tarea.value?.work_order === workOrder) {
      // Already tracking this order, resume state
      return true
    }
    // Clean slate for new order
    clearWorkflow()
    return false
  }

  async function fetchNewTarea(workOrder, company, warehouse) {
    const data = await getTareas(company, warehouse)
    const found = (data.tareas ?? []).find(t => t.work_order === workOrder)
    
    if (!found) {
      throw new Error("Ordre de fabrication introuvable.")
    }

    tarea.value = found
    materials.value = (found.materiales ?? []).map(m => ({
      ...m,
      status: 'pending',
      scanResult: null,
    }))
    
    return true
  }

  function markMaterialValidated(itemName, scanData) {
    const idx = materials.value.findIndex(
      m => m.item_name === itemName && m.status !== 'validated'
    )
    if (idx >= 0) {
      materials.value[idx].status = 'validated'
      materials.value[idx].scanResult = scanData
      return idx
    }
    return -1
  }

  function clearWorkflow() {
    tarea.value = null
    materials.value = []
    customExtras.value = []
  }

  return {
    tarea,
    materials,
    customExtras,
    allValidated,
    initWorkflow,
    fetchNewTarea,
    markMaterialValidated,
    clearWorkflow
  }
}, {
  persist: {
    storage: localStorage,
    paths: ['tarea', 'materials', 'customExtras']
  }
})
