import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  getCalendarEvents: vi.fn(),
  getMetadata: vi.fn(),
  getOlympiads: vi.fn(),
}))

vi.mock('../services/api', () => apiMocks)

import CatalogView from './CatalogView.vue'

const supportedMetadata = {
  academic_year: '2026/27',
  profiles: ['Математика'],
  categories: [
    { slug: 'mathematics', name: 'Математика', count: 42 },
    { slug: 'programming', name: 'Программирование', count: 18 },
  ],
  grades: [5, 6, 7, 8, 9, 10, 11],
  registry_levels: [1, 2, 3],
  benefit_types: ['bvi', 'hundred_points', 'other', 'prize'],
  universities: [
    { slug: 'hse', name: 'НИУ ВШЭ', short_name: 'ВШЭ', count: 17 },
    { slug: 'msu', name: 'МГУ имени М. В. Ломоносова', short_name: 'МГУ', count: 10 },
  ],
  counts: { total: 353, popular: 20, registry: 100 },
}

function catalogResponse() {
  return {
    items: [],
    pagination: { page: 1, per_page: 18, pages: 0, total: 0 },
  }
}

async function mountCatalog(query = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'catalog', component: { template: '<div />' } }],
  })
  await router.push({ name: 'catalog', query })
  await router.isReady()
  const wrapper = mount(CatalogView, {
    global: {
      plugins: [router],
      stubs: {
        AppPagination: true,
        ErrorAlert: true,
        LoadingState: true,
        OlympiadCalendar: true,
        OlympiadCard: true,
      },
    },
  })
  await flushPromises()
  await flushPromises()
  return { router, wrapper }
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.getMetadata.mockResolvedValue(supportedMetadata)
  apiMocks.getOlympiads.mockResolvedValue(catalogResponse())
  apiMocks.getCalendarEvents.mockResolvedValue({ events: [], total: 0 })
})

describe('CatalogView: упрощённые фильтры', () => {
  it('показывает доступные сейчас или позже регистрации и фильтрует по льготе в вузе', async () => {
    apiMocks.getOlympiads.mockResolvedValue({
      items: [{ edition_id: 1, slug: 'math', name: 'Математика' }],
      pagination: { page: 1, per_page: 18, pages: 1, total: 1 },
    })
    const { router, wrapper } = await mountCatalog({
      university: 'hse',
      registration_status: 'not_found',
      registry_status: 'draft',
      benefit_type: 'prize',
      popular: 'true',
    })

    expect(wrapper.get('#university-filter').element.value).toBe('hse')
    expect(wrapper.get('label[for="university-filter"]').text()).toBe('Льготы в вузе')
    expect(wrapper.get('#university-filter').text()).toContain('ВШЭ · 17')
    expect(wrapper.find('#benefit-type-filter').exists()).toBe(false)
    expect(wrapper.find('#registration-status-filter').exists()).toBe(false)
    expect(wrapper.find('#registry-status-filter').exists()).toBe(false)
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(0)
    expect(apiMocks.getMetadata).toHaveBeenCalledWith('2026/27', {
      registration_available: 'true',
    })
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      registration_available: 'true',
      university: 'hse',
    }))
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.not.objectContaining({
      benefit_type: expect.anything(),
      registry_status: expect.anything(),
      popular: expect.anything(),
    }))
    expect(wrapper.getComponent({ name: 'OlympiadCard' }).props()).toMatchObject({
      activeUniversity: 'hse',
    })

    await wrapper.get('.filter-panel .btn-link').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.university).toBeUndefined()
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      registration_available: 'true',
    }))
  })

  it('оставляет ограничение доступной регистрации в календаре', async () => {
    await mountCatalog({
      view: 'calendar',
      month: '2026-10',
      university: 'msu',
    })

    expect(apiMocks.getCalendarEvents).toHaveBeenLastCalledWith(expect.objectContaining({
      month: '2026-10',
      registration_available: 'true',
      university: 'msu',
    }))
  })

  it('не отправляет новые параметры, если metadata старого backend их не объявляет', async () => {
    apiMocks.getMetadata.mockResolvedValue({
      academic_year: '2026/27',
      profiles: [],
      grades: [5, 6, 7, 8, 9, 10, 11],
      registry_levels: [1, 2, 3],
      counts: { total: 0, popular: 0, registry: 0 },
    })
    const { router, wrapper } = await mountCatalog({
      university: 'hse',
    })

    expect(router.currentRoute.value.query).toMatchObject({
      university: 'hse',
    })
    expect(wrapper.find('#university-filter').exists()).toBe(false)
    for (const [params] of apiMocks.getOlympiads.mock.calls) {
      expect(params).not.toHaveProperty('university')
      expect(params).toHaveProperty('registration_available', 'true')
    }
  })
})

describe('CatalogView: укрупнённые направления', () => {
  it('читает direction из URL и передаёт его каталогу вместо точного profile', async () => {
    const { router, wrapper } = await mountCatalog({ direction: 'mathematics' })

    expect(wrapper.get('label[for="direction-filter"]').text()).toBe('Направление')
    expect(wrapper.get('#direction-filter').element.value).toBe('mathematics')
    expect(wrapper.get('#direction-filter').text()).toContain('Математика · 42')
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      direction: 'mathematics',
    }))
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.not.objectContaining({
      profile: expect.anything(),
    }))

    await wrapper.get('#direction-filter').setValue('programming')
    await flushPromises()
    expect(router.currentRoute.value.query.direction).toBe('programming')
    expect(router.currentRoute.value.query.profile).toBeUndefined()
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      direction: 'programming',
    }))

    await wrapper.get('.filter-panel .btn-link').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.direction).toBeUndefined()
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.not.objectContaining({
      direction: expect.anything(),
    }))
  })

  it('передаёт direction календарю и сохраняет его при смене месяца', async () => {
    const { router, wrapper } = await mountCatalog({
      view: 'calendar',
      month: '2026-10',
      direction: 'programming',
    })

    expect(apiMocks.getCalendarEvents).toHaveBeenLastCalledWith(expect.objectContaining({
      direction: 'programming',
      month: '2026-10',
    }))

    await wrapper.getComponent({ name: 'OlympiadCalendar' }).vm.$emit('next')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({
      direction: 'programming',
      month: '2026-11',
      view: 'calendar',
    })
    expect(apiMocks.getCalendarEvents).toHaveBeenLastCalledWith(expect.objectContaining({
      direction: 'programming',
      month: '2026-11',
    }))
  })

  it('использует старые profiles/profile, если backend не объявил categories', async () => {
    apiMocks.getMetadata.mockResolvedValue({
      academic_year: '2026/27',
      profiles: ['Математика', 'Физика'],
      grades: [5, 6, 7, 8, 9, 10, 11],
      registry_levels: [1, 2, 3],
      counts: { total: 2, popular: 0, registry: 0 },
    })
    const { router, wrapper } = await mountCatalog({ profile: 'Физика' })

    expect(wrapper.get('#direction-filter').element.value).toBe('Физика')
    expect(wrapper.get('#direction-filter').text()).toContain('Математика')
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      profile: 'Физика',
    }))
    for (const [params] of apiMocks.getOlympiads.mock.calls) {
      expect(params).not.toHaveProperty('direction')
    }

    await wrapper.get('#direction-filter').setValue('Математика')
    await flushPromises()
    expect(router.currentRoute.value.query.profile).toBe('Математика')
    expect(router.currentRoute.value.query.direction).toBeUndefined()
  })

  it('сохраняет старую exact-profile ссылку даже с новым metadata', async () => {
    const { router, wrapper } = await mountCatalog({ profile: 'Математика' })

    expect(wrapper.get('#direction-filter').text()).toContain('Точный профиль: Математика')
    expect(wrapper.get('#direction-filter').element.value).toBe(
      'legacy-profile:Математика',
    )
    expect(apiMocks.getOlympiads).toHaveBeenLastCalledWith(expect.objectContaining({
      profile: 'Математика',
    }))
    expect(router.currentRoute.value.query.direction).toBeUndefined()

    await wrapper.get('#direction-filter').setValue('programming')
    await flushPromises()
    expect(router.currentRoute.value.query.direction).toBe('programming')
    expect(router.currentRoute.value.query.profile).toBeUndefined()
  })
})
