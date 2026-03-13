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
    meta: { module: 'production' },
  },
  {
    path: '/laboratoire',
    name: 'laboratoire',
    component: () => import('../views/LaboratoireQC.vue'),
    meta: { module: 'quality' },
  },
  {
    path: '/recepcion',
    name: 'recepcion',
    component: () => import('../views/ReceptionMateriaux.vue'),
    meta: { module: 'reception' },
  },
  {
    path: '/traslado-cuarentena',
    name: 'traslado-cuarentena',
    component: () => import('../views/TransladoCuarentena.vue'),
    meta: { module: 'reception' },
  },
  {
    path: '/reimpresion',
    name: 'reimpresion',
    component: () => import('../views/ReimpresionEtiqueta.vue'),
    meta: { module: 'reception' },
  },
  {
    path: '/inventario-ciego',
    name: 'inventario-ciego',
    component: () => import('../views/InventarioCiego.vue'),
    meta: { module: 'reception' },
  },
  {
    path: '/poka-yoke/:workOrder',
    name: 'poka-yoke',
    component: () => import('../views/PokaYokeScanner.vue'),
    props: true,
    meta: { module: 'production' },
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

  if (to.meta.module && !store.hasModule(to.meta.module)) {
    return { name: 'hub' }
  }

  return true
})

export default router
