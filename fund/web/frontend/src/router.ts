import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('./views/Dashboard.vue'),
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('./views/Compare.vue'),
    },
    {
      path: '/positions',
      name: 'positions',
      component: () => import('./views/MyPositions.vue'),
    },
    {
      path: '/advanced-ranking',
      name: 'advanced-ranking',
      component: () => import('./views/AdvancedRanking.vue'),
    },
  ],
})

export default router
