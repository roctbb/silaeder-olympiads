import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  adminLogin: vi.fn(),
  adminSession: vi.fn(),
}))

vi.mock('../services/api', () => apiMocks)

import AdminLoginView from './AdminLoginView.vue'

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/login', name: 'admin-login', component: AdminLoginView },
      { path: '/admin', name: 'admin', component: { template: '<div />' } },
      { path: '/admin/users', name: 'admin-users', component: { template: '<div />' } },
    ],
  })
  await router.push('/admin/login?redirect=/admin/users')
  await router.isReady()
  const wrapper = mount(AdminLoginView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.adminSession.mockRejectedValue({ status: 401 })
})

describe('AdminLoginView', () => {
  it('предлагает администраторам войти через ЛК с возвратом в админку', async () => {
    const wrapper = await mountView()
    const crmLink = wrapper.get('a.btn-primary')

    expect(crmLink.text()).toContain('Войти через ЛК Силаэдр')
    expect(crmLink.attributes('href')).toBe(
      '/api/v1/auth/login?next=%2Fadmin%2Fusers',
    )
    expect(wrapper.text()).toContain('локальная учётная запись')
  })
})
