/**
 * useScanner — USB HID barcode/QR scanner composable.
 *
 * Listens for rapid keydown events (characteristic of HID scanners)
 * and emits the complete scan value on Enter. Includes gap-based
 * buffer reset to avoid mixing scan data with normal typing.
 *
 * @param {Function} onScan — Callback invoked with the scanned string.
 * @param {Object}   opts
 * @param {number}   opts.gapMs    — Max ms between keystrokes (default 80).
 * @param {number}   opts.minLength — Min chars to trigger onScan (default 3).
 * @param {import('vue').Ref<boolean>} opts.disabled — Reactive flag to pause listening.
 */
import { ref, onMounted, onUnmounted } from 'vue'

export function useScanner(onScan, { gapMs = 80, minLength = 3, disabled } = {}) {
  let buffer = ''
  let lastKeyTime = 0
  const isScanning = ref(false)

  function onKeyDown(e) {
    if (disabled?.value) return

    const now = Date.now()
    if (now - lastKeyTime > gapMs && buffer.length > 0) buffer = ''
    lastKeyTime = now

    if (e.key === 'Enter') {
      e.preventDefault()
      const value = buffer.trim()
      buffer = ''
      isScanning.value = false
      if (value.length >= minLength) onScan(value)
      return
    }

    if (e.key.length === 1) {
      buffer += e.key
      isScanning.value = true
    }
  }

  onMounted(() => document.addEventListener('keydown', onKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', onKeyDown))

  return { isScanning }
}
