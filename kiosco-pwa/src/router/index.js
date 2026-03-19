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
    path: '/rutas-comercial',
    name: 'rutas-comercial',
    component: () => import('../views/RutaComercial.vue'),
    meta: { module: 'comercial' },
  },
  {
    path: '/catalogo-stock',
    name: 'catalogo-stock',
    component: () => import('../views/CatalogoStock.vue'),
    meta: { module: 'comercial' },
  },
  {
    path: '/nuevo-cliente-b2b',
    name: 'nuevo-cliente-b2b',
    component: () => import('../views/NuevoClienteB2B.vue'),
    meta: { module: 'comercial' },
  },
  {
    path: '/picking-fefo',
    name: 'picking-fefo',
    component: () => import('../views/KioscoPickingFEFO.vue'),
    meta: { module: 'logistica' },
  },
  {
    path: '/chofer-pod',
    name: 'chofer-pod',
    component: () => import('../views/AppChoferPOD.vue'),
    meta: { module: 'logistica' },
  },
  {
    path: '/portal-b2b',
    name: 'portal-b2b',
    component: () => import('../views/PortalB2BCliente.vue'),
    meta: { guest: true },
  },
  {
    path: '/panel-gerencial-360',
    name: 'panel-gerencial-360',
    component: () => import('../views/PanelGerencial360.vue'),
    meta: { guest: true },
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
