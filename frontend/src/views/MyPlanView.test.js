import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resetAuthForTests } from '../services/auth'
import MyPlanView from './MyPlanView.vue'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  resetAuthForTests()
  vi.restoreAllMocks()
})

describe('MyPlanView', () => {
  it('публично показывает приглашение войти и не запрашивает приватный план', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({
      authenticated: false,
      user: null,
      csrf_token: null,
      login_url: '/api/v1/auth/login',
    }))
    const wrapper = mount(MyPlanView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Каталог и календарь можно смотреть без авторизации')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/session')
  })

  it('показывает ближайшие этапы и сохранённые олимпиады после входа', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: true,
          user: { id: 1, name: 'Анна', grade: 8 },
          csrf_token: 'csrf',
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).startsWith('/api/v1/me/plan?')) {
        return Promise.resolve(jsonResponse({
          items: [{
            id: 4,
            olympiad: {
              slug: 'math',
              name: 'Олимпиада по математике',
              family_name: 'Олимпиада',
              profile: 'Математика',
            },
            status: 'registered',
            reminders_enabled: true,
            reminder_days_before: [7, 1],
            stage_progress: [{
              stage_id: 11,
              stage_name: 'Регистрация',
              participated: true,
              advanced: true,
              result: 'Допущена',
              updated_at: '2026-08-26T10:00:00Z',
            }],
          }],
          upcoming_stages: [{
            stage_id: 12,
            stage_name: 'Отборочный этап',
            starts_on: '2026-10-10',
            ends_on: '2026-10-10',
            date_precision: 'exact',
            is_date_confirmed: true,
            olympiad: {
              slug: 'math',
              name: 'Олимпиада по математике',
              family_name: 'Олимпиада',
              profile: 'Математика',
            },
            progress: null,
          }],
        }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(MyPlanView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Анна')
    expect(wrapper.text()).toContain('Отборочный этап')
    expect(wrapper.text()).toContain('Олимпиада по математике')
    expect(wrapper.text()).toContain('Зарегистрирован')
    expect(wrapper.text()).toContain('Регистрация')
    expect(wrapper.text()).toContain('прошёл дальше')
    expect(wrapper.text()).toContain('Допущена')
    expect(fetchMock.mock.calls.some(([path]) => String(path).startsWith('/api/v1/me/plan?'))).toBe(true)
  })

  it('показывает архивный план без битой ссылки и позволяет отозвать имя и удалить его', async () => {
    const archivedPlan = {
      id: 9,
      academic_year: '2026/27',
      edition_status: 'archived',
      olympiad: {
        slug: 'archived-math',
        name: 'Архивная олимпиада',
        family_name: 'Архивная олимпиада',
        profile: 'Математика',
      },
      status: 'completed',
      is_name_public: true,
      reminders_enabled: true,
      reminder_days_before: [7, 1],
      stage_progress: [{
        stage_id: 21,
        stage_name: 'Финал',
        stage_is_active: false,
        participated: true,
        advanced: null,
        result: 'Финалист',
      }],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((path, options = {}) => {
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: true,
          user: { id: 1, name: 'Анна', grade: 8 },
          csrf_token: 'csrf',
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).startsWith('/api/v1/me/plan?')) {
        return Promise.resolve(jsonResponse({ items: [archivedPlan], upcoming_stages: [] }))
      }
      if (String(path).includes('/olympiads/archived-math/planning?') && options.method === 'PATCH') {
        return Promise.resolve(jsonResponse({
          ...archivedPlan,
          is_name_public: false,
          reminders_enabled: false,
          reminder_days_before: [],
        }))
      }
      if (String(path).includes('/olympiads/archived-math/planning?') && options.method === 'DELETE') {
        return Promise.resolve(new Response(null, { status: 204 }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(MyPlanView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Архивная карточка')
    expect(wrapper.text()).toContain('Финалист')
    expect(wrapper.find('.my-plan-card a').exists()).toBe(false)

    await wrapper.get('.archived-plan-deactivate').trigger('click')
    await flushPromises()
    const patchCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'PATCH')
    expect(patchCall[1].headers.get('X-CSRF-Token')).toBe('csrf')
    expect(JSON.parse(patchCall[1].body)).toEqual({
      is_name_public: false,
      reminders_enabled: false,
      reminder_days_before: [],
    })
    expect(wrapper.find('.archived-plan-deactivate').exists()).toBe(false)

    await wrapper.get('.archived-plan-remove').trigger('click')
    await flushPromises()
    const deleteCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deleteCall[1].headers.get('X-CSRF-Token')).toBe('csrf')
    expect(wrapper.text()).toContain('План пока пуст')
  })
})
