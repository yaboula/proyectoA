import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { loginOperario as apiLogin } from '../api/kiosco'

export const useOperarioStore = defineStore('operario', () => {
  // ── State ──
  const operario = ref(null)  // { full_name, employee_id, company, company_abbr, default_warehouse }
  const sid = ref(null)

  // ── Getters ──
  const isLoggedIn = computed(() => !!operario.value)
  const fullName = computed(() => operario.value?.full_name ?? '')

  // ── Actions ──
  async function login(qrToken) {
    const data = await apiLogin(qrToken)
    if (!data.success) throw data
    operario.value = data.operario
    sid.value = data.sid
    return data
  }

  function logout() {
    operario.value = null
    sid.value = null
  }

  return { operario, sid, isLoggedIn, fullName, login, logout }
})
