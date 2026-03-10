import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getOperarioSession,
  loginOperario as apiLogin,
  logoutOperario as apiLogout,
} from '../api/kiosco'

const STORAGE_KEY = 'gcma-kiosco-operario-session'

export const useOperarioStore = defineStore('operario', () => {
  const saved = typeof window !== 'undefined'
    ? JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || 'null')
    : null

  const operario = ref(saved?.operario ?? null)
  const sid = ref(null)
  const initialized = ref(false)
  const restoring = ref(false)

  const isLoggedIn = computed(() => !!operario.value)
  const fullName = computed(() => operario.value?.full_name ?? '')

  function persist() {
    if (typeof window === 'undefined') return

    if (operario.value) {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ operario: operario.value })
      )
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY)
    }
  }

  function applySession(data) {
    operario.value = data.operario
    sid.value = data.sid ?? null
    persist()
  }

  function clearSession() {
    operario.value = null
    sid.value = null
    persist()
  }

  async function login(qrToken) {
    const data = await apiLogin(qrToken)
    if (!data.success) throw data
    applySession(data)
    initialized.value = true
    return data
  }

  async function restoreSession() {
    if (restoring.value) return isLoggedIn.value

    restoring.value = true
    try {
      const data = await getOperarioSession()
      if (!data.success) {
        clearSession()
        initialized.value = true
        return false
      }

      applySession(data)
      initialized.value = true
      return true
    } catch {
      clearSession()
      initialized.value = true
      return false
    } finally {
      restoring.value = false
    }
  }

  async function ensureSession() {
    if (isLoggedIn.value) {
      initialized.value = true
      return true
    }

    return restoreSession()
  }

  async function logout() {
    try {
      await apiLogout()
    } catch {
      // Ignore backend logout failures and clear the local session anyway.
    }
    clearSession()
    initialized.value = true
  }

  return {
    operario,
    sid,
    initialized,
    restoring,
    isLoggedIn,
    fullName,
    login,
    restoreSession,
    ensureSession,
    logout,
  }
})
