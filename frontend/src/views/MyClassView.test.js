import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getMyClass: vi.fn(), getClassCandidates: vi.fn(), addClassStudent: vi.fn(), removeClassStudent: vi.fn(),
}))
vi.mock('../services/api', () => api)
vi.mock('../services/auth', () => ({ loginUrl: () => '/login' }))
import MyClassView from './MyClassView.vue'

const anna = { id: 1, name: 'Анна', grade: 9, plans: [] }
const boris = { id: 2, name: 'Борис', grade: 10, plans: [] }
const document = (items, notifications = true) => ({ items, csrf_token: 'csrf', notifications_available: notifications })

async function render() {
  const wrapper = mount(MyClassView, { global: { stubs: { RouterLink: RouterLinkStub } } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getMyClass.mockResolvedValue(document([anna]))
  api.getClassCandidates.mockResolvedValue({ items: [boris] })
  api.addClassStudent.mockResolvedValue(boris)
  api.removeClassStudent.mockResolvedValue(null)
})

describe('Мой класс', () => {
  it('показывает учеников, олимпиады и отправляет фильтры на сервер', async () => {
    api.getMyClass.mockResolvedValue(document([{ ...anna, plans: [{
      id: 1, olympiad: { slug: 'math', name: 'Математика' }, academic_year: '2026/27',
      edition_status: 'published', status: 'registered',
    }] }]))
    const wrapper = await render()
    expect(wrapper.text()).toContain('Мои ученики · 1')
    expect(wrapper.text()).toContain('Математика')
    expect(wrapper.text()).toContain('Зарегистрирован')
    await wrapper.get('#class-search').setValue('Борис')
    await wrapper.get('#class-grade').setValue('10')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.getClassCandidates).toHaveBeenLastCalledWith({ q: 'Борис', grade: 10 })
  })

  it('добавляет и убирает ученика с CSRF, обновляет оба списка', async () => {
    const wrapper = await render()
    api.getMyClass.mockResolvedValue(document([anna, boris]))
    api.getClassCandidates.mockResolvedValue({ items: [] })
    await wrapper.get('[aria-label="Добавить: Борис"]').trigger('click')
    await flushPromises()
    expect(api.addClassStudent).toHaveBeenCalledWith(2, 'csrf')
    expect(wrapper.text()).toContain('Мои ученики · 2')
    api.getMyClass.mockResolvedValue(document([anna]))
    api.getClassCandidates.mockResolvedValue({ items: [boris] })
    await wrapper.get('[aria-label="Убрать из класса: Борис"]').trigger('click')
    await flushPromises()
    expect(api.removeClassStudent).toHaveBeenCalledWith(2, 'csrf')
    expect(wrapper.text()).toContain('Мои ученики · 1')
  })

  it('сообщает об ошибке добавления и сохраняет список', async () => {
    const wrapper = await render()
    api.addClassStudent.mockRejectedValue(new Error('Не удалось добавить'))
    await wrapper.get('[aria-label="Добавить: Борис"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Не удалось добавить')
    expect(wrapper.text()).toContain('Мои ученики · 1')
  })

  it('объясняет ограничение уведомлений локального администратора', async () => {
    api.getMyClass.mockResolvedValue(document([], false))
    const wrapper = await render()
    expect(wrapper.text()).toContain('локальный администратор')
    expect(wrapper.text()).toContain('В классе пока нет учеников')
  })

  it('не загружает справочник при отказе доступа', async () => {
    api.getMyClass.mockRejectedValue({ status: 403 })
    const wrapper = await render()
    expect(wrapper.text()).toContain('Раздел для учителей и администраторов')
    expect(api.getClassCandidates).not.toHaveBeenCalled()
  })
})
