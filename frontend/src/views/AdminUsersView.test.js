import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  adminLogout: vi.fn(),
  adminSession: vi.fn(),
  getAdminUsers: vi.fn(),
}))

vi.mock('../services/api', () => apiMocks)

import AdminUsersView from './AdminUsersView.vue'

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/users', name: 'admin-users', component: AdminUsersView },
      { path: '/admin', name: 'admin', component: { template: '<div />' } },
      { path: '/admin/login', name: 'admin-login', component: { template: '<div />' } },
      { path: '/olympiads/:slug', name: 'olympiad', component: { template: '<div />' } },
    ],
  })
  await router.push('/admin/users')
  await router.isReady()
  const wrapper = mount(AdminUsersView, {
    global: {
      plugins: [router],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.adminSession.mockResolvedValue({ username: 'editor', csrf_token: 'csrf' })
  apiMocks.adminLogout.mockResolvedValue(null)
  apiMocks.getAdminUsers.mockResolvedValue({
    items: [{
      id: 7,
      name: 'Анна Петрова',
      preferred_username: 'anna',
      email: 'anna@example.test',
      grade: 9,
      last_login_at: '2026-08-28T09:30:00+00:00',
      plan_count: 1,
      plans: [{
        id: 11,
        status: 'registered',
        is_name_public: true,
        reminders_enabled: true,
        reminder_days_before: [7, 1],
        academic_year: '2026/27',
        edition_status: 'published',
        created_at: '2026-08-27T10:00:00+00:00',
        olympiad: {
          slug: 'math',
          name: 'Олимпиада по математике',
          family_name: 'Олимпиада',
          profile: 'Математика',
        },
      }],
    }],
    summary: { total_users: 12, users_with_plans: 8, plans_total: 24 },
    pagination: { page: 1, per_page: 25, total: 12, pages: 1 },
  })
})

describe('AdminUsersView', () => {
  it('показывает пользователей и вложенные олимпиады из плана', async () => {
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('Пользователи и планы')
    expect(wrapper.findAll('.admin-stat')[0].text()).toContain('12')
    expect(wrapper.findAll('.admin-stat')[0].text()).toContain('пользователей')
    expect(wrapper.text()).toContain('Анна Петрова')
    expect(wrapper.text()).toContain('@anna')
    expect(wrapper.text()).toContain('9 класс')
    expect(wrapper.text()).toContain('Олимпиада по математике')
    expect(wrapper.text()).toContain('Зарегистрирован')
    expect(wrapper.text()).toContain('Имя видно')
    expect(apiMocks.getAdminUsers).toHaveBeenCalledWith({
      academic_year: '2026/27',
      q: '',
      page: 1,
      per_page: 25,
    })
  })

  it('ищет пользователя на сервере', async () => {
    const wrapper = await mountView()

    await wrapper.get('#admin-user-search').setValue('Борис')
    await wrapper.get('form[role="search"]').trigger('submit')
    await flushPromises()

    expect(apiMocks.getAdminUsers).toHaveBeenLastCalledWith({
      academic_year: '2026/27',
      q: 'Борис',
      page: 1,
      per_page: 25,
    })
  })
})
