export function parseKioscoBatchQr(rawValue) {
  const value = String(rawValue ?? '').trim()
  if (!value) {
    return { itemCode: null, batchNo: null, raw: '' }
  }

  const normalized = value.startsWith('QA,') ? value.slice(3) : value
  const parts = normalized.split('|').map(part => part.trim()).filter(Boolean)
  if (parts.length !== 2) {
    return { itemCode: null, batchNo: null, raw: value }
  }

  return {
    itemCode: parts[0] || null,
    batchNo: parts[1] || null,
    raw: value,
  }
}
