import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../services/auth', () => ({
  loginUrl: () => '/login',
  useAuth: () => ({
    state: {
      initialized: true,
      loading: false,
      user: null,
      csrfToken: '',
    },
    refresh: vi.fn(),
    clear: vi.fn(),
  }),
}))

vi.mock('../services/theme', () => ({
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}))

vi.mock('../services/api', () => ({ logoutUser: vi.fn() }))

import AppNavbar from './AppNavbar.vue'

describe('AppNavbar', () => {
  it('не показывает публичную ссылку на администрирование', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/my-plan', component: { template: '<div />' } },
        { path: '/admin', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppNavbar, { global: { plugins: [router] } })

    expect(wrapper.text()).not.toContain('Администрирование')
    expect(wrapper.find('a[href="/admin"]').exists()).toBe(false)
  })
})
