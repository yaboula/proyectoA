import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getOperarioSession,
  loginOperario as apiLogin,
  logoutOperario as apiLogout,
} from '../api/kiosco'

export const useOperarioStore = defineStore('operario', () => {

  const operario = ref(null)
  const sid = ref(null)
  const initialized = ref(false)
  const restoring = ref(false)

  const isLoggedIn = computed(() => !!operario.value)
  const fullName = computed(() => operario.value?.full_name ?? '')
  const profileCode = computed(() => operario.value?.profile_code ?? null)
  const profileLabel = computed(() => operario.value?.profile_label ?? '')
  const allowedModules = computed(() => operario.value?.allowed_modules ?? [])

  function applySession(data) {
    operario.value = data.operario
    sid.value = data.sid ?? null
  }

  function clearSession() {
    operario.value = null
    sid.value = null
  }

  async function login(qrToken) {
    const normalizedToken = String(qrToken ?? '').trim()
    if (normalizedToken.length < 5) {
      throw {
        success: false,
        error_code: 'MISSING_TOKEN',
        message_fr: 'Code QR manquant. Veuillez scanner votre badge.',
      }
    }

    const data = await apiLogin(normalizedToken)
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

  function hasModule(moduleCode) {
    return allowedModules.value.includes(moduleCode)
  }

  return {
    operario,
    sid,
    initialized,
    restoring,
    isLoggedIn,
    fullName,
    profileCode,
    profileLabel,
    allowedModules,
    hasModule,
    login,
    restoreSession,
    ensureSession,
    logout,
  }
}, {
  persist: {
    storage: sessionStorage,
    paths: ['operario', 'sid']
  }
})
