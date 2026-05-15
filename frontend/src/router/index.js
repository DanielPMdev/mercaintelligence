import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: 'Inicio' }
    },
    {
      path: '/ipc',
      name: 'ipc',
      component: () => import('@/views/IPCView.vue'),
      meta: { title: 'IPC Personalizado' }
    },
    {
      path: '/anomalias',
      name: 'anomalias',
      component: () => import('@/views/AnomaliasView.vue'),
      meta: { title: 'Alertas de Anomalías' }
    },
    {
      path: '/marcas',
      name: 'marcas',
      component: () => import('@/views/MarcasView.vue'),
      meta: { title: 'Análisis de Marcas' }
    },
    {
      path: '/catalogo',
      name: 'catalogo',
      component: () => import('@/views/CatalogoView.vue'),
      meta: { title: 'Catálogo' }
    },
    {
      path: '/shrinkflation',
      name: 'shrinkflation',
      component: () => import('@/views/ShrinkflationView.vue'),
      meta: { title: 'Shrinkflation' }
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
      meta: { title: 'Acerca del Proyecto' }
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: 'Página no encontrada' }
    }
  ]
})

// Actualizar el título de la pestaña en cada navegación
router.afterEach((to) => {
  document.title = `MercaIntelligence — ${to.meta.title || 'Dashboard'}`
})

export default router