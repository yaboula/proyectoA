import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { parseKioscoBatchQr } from '../utils/qr'

function normalizeWarehouseEntries(payload) {
  return Array.isArray(payload) ? payload : []
}

export const useBlindInventoryStore = defineStore('blindInventory', () => {
  const activeWarehouse = ref('')
  const countsByWarehouse = ref({})
  const lastScan = ref(null)

  const currentEntries = computed(() => {
    return normalizeWarehouseEntries(countsByWarehouse.value[activeWarehouse.value])
  })

  const totalScans = computed(() => {
    return currentEntries.value.reduce((acc, row) => acc + Number(row.qty_fisica ?? 0), 0)
  })

  const distinctLots = computed(() => currentEntries.value.length)

  function ensureWarehouse(warehouse) {
    if (!countsByWarehouse.value[warehouse]) {
      countsByWarehouse.value[warehouse] = []
    }
    return countsByWarehouse.value[warehouse]
  }

  function setActiveWarehouse(warehouse) {
    activeWarehouse.value = warehouse
    ensureWarehouse(warehouse)
  }

  function addCount(warehouse, itemCode, batchNo, qty = 1) {
    const rows = ensureWarehouse(warehouse)
    const existing = rows.find(row => row.item_code === itemCode && row.batch_no === batchNo)
    if (existing) {
      existing.qty_fisica = Number(existing.qty_fisica ?? 0) + Number(qty)
    } else {
      rows.unshift({
        item_code: itemCode,
        batch_no: batchNo,
        qty_fisica: Number(qty),
      })
    }

    lastScan.value = {
      warehouse,
      item_code: itemCode,
      batch_no: batchNo,
      qty,
      scanned_at: new Date().toISOString(),
    }
  }

  function addScan(warehouse, qrValue) {
    const parsed = parseKioscoBatchQr(qrValue)
    if (!parsed.itemCode || !parsed.batchNo) {
      throw new Error('QR_INVALIDE')
    }
    addCount(warehouse, parsed.itemCode, parsed.batchNo, 1)
    return parsed
  }

  function addManualEntry(warehouse, rawValue, qty = 1) {
    const parsed = parseKioscoBatchQr(rawValue)
    if (!parsed.itemCode || !parsed.batchNo) {
      throw new Error('QR_INVALIDE')
    }
    addCount(warehouse, parsed.itemCode, parsed.batchNo, qty)
    return parsed
  }

  function updateEntryQty(warehouse, itemCode, batchNo, qty) {
    const rows = ensureWarehouse(warehouse)
    const target = rows.find(row => row.item_code === itemCode && row.batch_no === batchNo)
    if (!target) return
    target.qty_fisica = Math.max(0, Number(qty ?? 0))
    if (target.qty_fisica <= 0) {
      removeEntry(warehouse, itemCode, batchNo)
    }
  }

  function removeEntry(warehouse, itemCode, batchNo) {
    const rows = ensureWarehouse(warehouse)
    countsByWarehouse.value[warehouse] = rows.filter(
      row => !(row.item_code === itemCode && row.batch_no === batchNo)
    )
  }

  function clearWarehouse(warehouse) {
    countsByWarehouse.value[warehouse] = []
    if (activeWarehouse.value === warehouse) {
      lastScan.value = null
    }
  }

  function buildPayload(warehouse) {
    return normalizeWarehouseEntries(countsByWarehouse.value[warehouse]).map(row => ({
      item_code: row.item_code,
      batch_no: row.batch_no,
      qty_fisica: Number(row.qty_fisica ?? 0),
    }))
  }

  return {
    activeWarehouse,
    countsByWarehouse,
    lastScan,
    currentEntries,
    totalScans,
    distinctLots,
    setActiveWarehouse,
    addScan,
    addManualEntry,
    updateEntryQty,
    removeEntry,
    clearWarehouse,
    buildPayload,
  }
}, {
  persist: {
    storage: localStorage,
    paths: ['activeWarehouse', 'countsByWarehouse', 'lastScan'],
  },
})
