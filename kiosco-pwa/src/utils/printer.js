const PRINTER_ENDPOINT = 'http://localhost:9000/print'

function sanitizeText(value) {
  return String(value ?? '').replace(/\^/g, ' ').replace(/[\r\n]+/g, ' ').trim()
}

export function buildReceptionLabelZpl(label) {
  const itemName = sanitizeText(label.item_name)
  const batchNo = sanitizeText(label.batch_no)
  const expiryDate = sanitizeText(label.expiry_date || 'N/A')
  const itemCode = sanitizeText(label.item_code)

  return [
    '^XA',
    '^PW800',
    '^LL600',
    `^FO50,50^A0N,44,44^FD${itemName}^FS`,
    `^FO50,120^A0N,28,28^FDLot Interne: ${batchNo}^FS`,
    `^FO50,160^A0N,28,28^FDExp: ${expiryDate}^FS`,
    `^FO50,220^BQN,2,6^FDQA,${itemCode}|${batchNo}^FS`,
    '^XZ',
  ].join('\n')
}

export function buildKioscoLabelZpl(label) {
  return buildReceptionLabelZpl(label)
}

async function postZpl(zpl, timeoutMs = 4000) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(PRINTER_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zpl }),
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`PRINT_HTTP_${response.status}`)
    }
  } finally {
    window.clearTimeout(timer)
  }
}

export async function printReceptionLabels(labels = []) {
  const printable = Array.isArray(labels) ? labels.filter(label => label?.batch_no) : []
  if (!printable.length) {
    return { success: true, printed: 0, failed: 0 }
  }

  let printed = 0
  for (const label of printable) {
    const zpl = buildReceptionLabelZpl(label)
    await postZpl(zpl)
    printed += 1
  }

  return {
    success: true,
    printed,
    failed: 0,
  }
}

export async function printKioscoLabels(labels = []) {
  return printReceptionLabels(labels)
}

export async function printSingleKioscoLabel(label) {
  return printReceptionLabels(label ? [label] : [])
}
