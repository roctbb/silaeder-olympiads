import { createRouter, createWebHistory } from 'vue-router'
import { adminSession } from './services/api'

const routes = [
  {
    path: '/',
    name: 'catalog',
    component: () => import('./views/CatalogView.vue'),
  },
  {
    path: '/olympiads/:slug',
    name: 'olympiad',
    component: () => import('./views/OlympiadDetailView.vue'),
    props: true,
  },
  {
    path: '/my-plan',
    name: 'my-plan',
    component: () => import('./views/MyPlanView.vue'),
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('./views/AdminLoginView.vue'),
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('./views/AdminDashboardView.vue'),
    meta: { requiresAdmin: true },
  },
  {
    path: '/admin/olympiads/new',
    name: 'admin-new',
    component: () => import('./views/AdminEditorView.vue'),
    meta: { requiresAdmin: true },
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('./views/AdminUsersView.vue'),
    meta: { requiresAdmin: true },
  },
  {
    path: '/admin/olympiads/:slug',
    name: 'admin-edit',
    component: () => import('./views/AdminEditorView.vue'),
    props: true,
    meta: { requiresAdmin: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('./views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) return true
  try {
    await adminSession()
    return true
  } catch {
    return {
      name: 'admin-login',
      query: { redirect: to.fullPath },
    }
  }
})

export default router
