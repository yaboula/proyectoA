import { createRouter, createWebHistory } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import LoginQR from '../views/LoginQR.vue'

const routes = [
  {
    path: '/',
    name: 'login',
    component: LoginQR,
    meta: { guest: true },
  },
  {
    path: '/hub',
    name: 'hub',
    component: () => import('../views/ModuleHub.vue'),
  },
  {
    path: '/tareas',
    name: 'tareas',
    component: () => import('../views/TareasList.vue'),
  },
  {
    path: '/laboratoire',
    name: 'laboratoire',
    component: () => import('../views/LaboratoireQC.vue'),
  },
  {
    path: '/poka-yoke/:workOrder',
    name: 'poka-yoke',
    component: () => import('../views/PokaYokeScanner.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const store = useOperarioStore()

  if (to.meta.guest) {
    return true
  }

  const ok = await store.ensureSession()
  if (!ok) {
    return { name: 'login' }
  }

  return true
})

export default router
