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
    path: '/tareas',
    name: 'tareas',
    component: () => import('../views/TareasList.vue'),
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

// Navigation guard — redirect to login if not authenticated
router.beforeEach((to) => {
  const store = useOperarioStore()
  if (!to.meta.guest && !store.isLoggedIn) {
    return { name: 'login' }
  }
})

export default router
