import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetAuthForTests } from '../services/auth'
import OlympiadDetailView from './OlympiadDetailView.vue'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function olympiad() {
  return {
    slug: 'math',
    name: 'Олимпиада по математике',
    family_name: 'Тестовая олимпиада',
    profile: 'Математика',
    description: 'Описание олимпиады',
    is_popular: true,
    registry_status: 'not_listed',
    registry_level: null,
    is_team: false,
    registration_url: null,
    registration_closes_at: null,
    registration_status: 'not_found',
    registration_checked_on: '2026-08-26',
    website_url: 'https://example.test',
    grades: [7, 8, 9],
    geography: 'russia',
    organizer: 'Организатор',
    academic_year: '2026/27',
    cycle_label: null,
    data_status: 'confirmed',
    previous_year_reference: null,
    stages: [{
      id: 7,
      name: 'Отборочный этап',
      stage_type: 'Отборочный',
      starts_on: '2026-10-10',
      ends_on: '2026-10-10',
      date_precision: 'exact',
      is_date_confirmed: true,
      format: 'online',
      location: null,
      registration_opens_on: null,
      registration_closes_on: null,
      details: null,
      source_url: null,
    }],
    materials: [],
    benefits: [],
    sources: [],
    notes: null,
    updated_at: '2026-08-26T10:00:00Z',
    participant_count: 2,
    public_participants: [{ name: 'Анна' }],
  }
}

beforeEach(() => {
  resetAuthForTests()
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('OlympiadDetailView personal layer', () => {
  it('показывает ссылку регистрации до указанного срока', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T08:49:59Z'))
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          registration_url: 'https://register.example.test',
          registration_closes_at: '2026-08-26T11:50:00+03:00',
          registration_status: 'open',
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    const primaryAction = wrapper.get('.detail-header .btn-primary')
    expect(primaryAction.text()).toContain('Перейти к регистрации')
    expect(primaryAction.attributes('href')).toBe('https://register.example.test')
    expect(wrapper.get('.detail-header .btn-outline-secondary').attributes('href')).toBe(
      'https://example.test',
    )
    expect(wrapper.text()).toContain('Регистрация открыта')
    expect(wrapper.text()).toContain('Проверено 26 авг.')
    vi.useRealTimers()
  })

  it('после срока скрывает регистрацию и оставляет официальный сайт', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-26T08:50:00Z'))
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          registration_url: 'https://register.example.test',
          registration_closes_at: '2026-08-26T11:50:00+03:00',
          registration_status: 'open',
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    const primaryAction = wrapper.get('.detail-header .btn-primary')
    expect(primaryAction.text()).toContain('Официальный сайт')
    expect(primaryAction.attributes('href')).toBe('https://example.test')
    expect(wrapper.find('.detail-header .btn-outline-secondary').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Перейти к регистрации')
    expect(wrapper.text()).toContain('Регистрация пока закрыта')
    vi.useRealTimers()
  })

  it('сохраняет весь просмотр публичным и предлагает вход только для плана', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse(olympiad()))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({
          participant_count: 2,
          public_participants: [{ name: 'Анна' }],
          plan: null,
        }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Олимпиада по математике')
    expect(wrapper.text()).toContain('Этапы')
    expect(wrapper.text()).toContain('2 выбрали эту олимпиаду')
    expect(wrapper.text()).toContain('Войдите, чтобы добавить в план')
    expect(wrapper.text()).not.toContain('Календарный цикл')
    expect(wrapper.find('.stage-progress').exists()).toBe(false)
  })

  it('показывает календарный цикл рядом с учебным годом, когда он задан', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          cycle_label: 'Календарный цикл 2026',
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    const facts = wrapper.get('.detail-facts').text()
    expect(facts).toContain('2026/27 · Календарный цикл 2026')
  })

  it('показывает точные текстовые условия вместо неизвестных классов', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          grades: [],
          eligibility_notes: 'Учащиеся музыкальных образовательных учреждений',
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Участники')
    expect(wrapper.text()).toContain('Учащиеся музыкальных образовательных учреждений')
    expect(wrapper.text()).not.toContain('Классы уточняются')
  })

  it('не называет датами прошлого года структуру этапов без опубликованного расписания', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          data_status: 'previous_year_estimate',
          previous_year_reference: '2025/26',
          stages: [{
            ...olympiad().stages[0],
            starts_on: null,
            ends_on: null,
            date_precision: 'tba',
            is_date_confirmed: false,
          }],
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Расписание 2026/27 ещё не опубликовано')
    expect(wrapper.text()).not.toContain('Даты рассчитаны')
  })

  it('показывает приватные отметки этапов только авторизованному участнику с планом', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse(olympiad()))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: true,
          user: { id: 1, name: 'Анна', grade: 8 },
          csrf_token: 'csrf',
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({
          participant_count: 2,
          public_participants: [{ name: 'Анна' }],
          plan: {
            id: 4,
            status: 'participating',
            is_name_public: true,
            reminders_enabled: true,
            reminder_days_before: [7, 1],
            stage_progress: [{
              stage_id: 7,
              stage_name: 'Отборочный этап',
              participated: true,
              advanced: true,
              result: '80 баллов',
              updated_at: '2026-08-26T10:00:00Z',
            }],
          },
        }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.stage-progress').exists()).toBe(true)
    expect(wrapper.get('#participated-7').element.checked).toBe(true)
    expect(wrapper.get('#advanced-7').element.value).toBe('yes')
    expect(wrapper.get('#result-7').element.value).toBe('80 баллов')
  })

  it('разделяет год вузовской льготы и устаревшее поле года у награды', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          benefits: [
            {
              id: 1,
              benefit_type: 'other',
              has_bvi: true,
              has_hundred_points: true,
              title: 'Право зависит от программы',
              admission_year: 2026,
              university: { slug: 'hse', name: 'НИУ ВШЭ' },
            },
            {
              id: 2,
              benefit_type: 'prize',
              has_bvi: false,
              has_hundred_points: false,
              title: 'Диплом и подарок',
              admission_year: 2025,
              university: null,
            },
          ],
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    const benefits = wrapper.get('#benefits')
    expect(benefits.text()).toContain('Льготы и награды')
    expect(benefits.text()).toContain('БВИ / 100 баллов')
    expect(benefits.text()).toContain('Приём 2026')
    expect(benefits.text()).toContain('Призы')
    expect(benefits.text()).not.toContain('Приём 2025')
  })

  it('не показывает приёмную оговорку в разделе только с наградой', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((path) => {
      if (String(path).startsWith('/api/v1/olympiads/math?')) {
        return Promise.resolve(jsonResponse({
          ...olympiad(),
          benefits: [{
            id: 1,
            benefit_type: 'prize',
            has_bvi: false,
            has_hundred_points: false,
            title: 'Диплом и подарок',
            admission_year: 2025,
            university: null,
          }],
        }))
      }
      if (path === '/api/v1/auth/session') {
        return Promise.resolve(jsonResponse({
          authenticated: false,
          user: null,
          csrf_token: null,
          login_url: '/api/v1/auth/login',
        }))
      }
      if (String(path).includes('/olympiads/math/planning?')) {
        return Promise.resolve(jsonResponse({ participant_count: 0, public_participants: [], plan: null }))
      }
      throw new Error(`Unexpected fetch: ${path}`)
    })

    const wrapper = mount(OlympiadDetailView, {
      props: { slug: 'math' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    await flushPromises()

    const benefits = wrapper.get('#benefits')
    expect(benefits.text()).toContain('Диплом и подарок')
    expect(benefits.text()).not.toContain('правила приёма')
    expect(benefits.text()).not.toContain('Приём 2025')
  })
})
