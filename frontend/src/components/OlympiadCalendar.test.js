import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OlympiadCalendar from './OlympiadCalendar.vue'

function event(overrides = {}) {
  return {
    id: 'test-event',
    olympiadSlug: 'test-math',
    olympiadName: 'Тестовая олимпиада',
    stageName: 'Финал',
    startsOn: '2026-10-05',
    endsOn: '2026-10-07',
    isRange: true,
    confidence: 'confirmed',
    displayStatus: 'confirmed',
    datePrecision: 'range',
    previousYearEstimate: false,
    profiles: [
      { slug: 'test-math', name: 'Тест — Математика', profile: 'Математика' },
    ],
    ...overrides,
  }
}

function mountCalendar(props = {}) {
  return mount(OlympiadCalendar, {
    props: {
      month: '2026-10',
      events: [event()],
      sourceTotal: 1,
      ...props,
    },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
}

function profiles(count) {
  return Array.from({ length: count }, (_, index) => ({
    slug: `test-profile-${index + 1}`,
    name: `Тестовая олимпиада — Направление ${index + 1}`,
    profile: `Направление ${index + 1}`,
  }))
}

describe('OlympiadCalendar', () => {
  it('рендерит сетку Пн–Вс, диапазон и ссылку на олимпиаду', () => {
    const wrapper = mountCalendar()
    expect(wrapper.findAll('.calendar-weekdays > div').map((item) => item.text())).toEqual([
      'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс',
    ])
    expect(wrapper.find('.calendar-event-confirmed').attributes('to')).toBeUndefined()
    expect(wrapper.find('.calendar-desktop button.calendar-event').exists()).toBe(false)
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({
      name: 'olympiad',
      params: { slug: 'test-math' },
    })
    expect(wrapper.text()).toContain('Подтверждённый диапазон')
  })

  it('показывает крайний срок как «до», а не как день проведения', () => {
    const wrapper = mountCalendar({
      events: [event({
        startsOn: '2026-10-31',
        endsOn: '2026-10-31',
        isDeadline: true,
        isRange: false,
      })],
    })

    expect(wrapper.get('.calendar-event').attributes('aria-label')).toContain(
      'до 31 октября 2026 г.',
    )
    expect(wrapper.get('.calendar-agenda-date').text()).toContain('до 31 окт.')
    expect(wrapper.text()).toContain('Подтверждённый крайний срок')
  })

  it('показывает календарный цикл прямо в событии', () => {
    const wrapper = mountCalendar({
      events: [event({ cycleLabel: 'Сезон 2026' })],
    })

    expect(wrapper.get('.calendar-event-flag').text()).toBe('Сезон 2026')
    expect(wrapper.get('.calendar-agenda .badge').text()).toBe('Сезон 2026')
  })

  it('явно подписывает прошлогодний ориентир и объединённые профили', () => {
    const wrapper = mountCalendar({
      sourceTotal: 5,
      events: [event({
        confidence: 'estimate',
        displayStatus: 'estimate',
        previousYearEstimate: true,
        profiles: [
          { slug: 'math', name: 'Тест — Математика', profile: 'Математика' },
          { slug: 'physics', name: 'Тест — Физика', profile: 'Физика' },
          { slug: 'cs', name: 'Тест — Информатика', profile: 'Информатика' },
          { slug: 'chemistry', name: 'Тест — Химия', profile: 'Химия' },
        ],
      })],
    })

    expect(wrapper.find('.calendar-event-previous-year').exists()).toBe(true)
    expect(wrapper.text()).toContain('Ориентир прошлого года')
    expect(wrapper.text()).toContain('5 записей в 1 событие')
    expect(wrapper.find('.calendar-profile-more summary').text()).toContain('Ещё 1')
  })

  it('не называет подтверждённый источник точной датой при примерной точности', () => {
    const wrapper = mountCalendar({
      events: [event({
        confidence: 'confirmed',
        displayStatus: 'estimate',
        datePrecision: 'approximate',
      })],
    })

    expect(wrapper.text()).toContain('Ориентировочно')
    expect(wrapper.text()).not.toContain('Подтверждённый диапазон')
  })

  it('раскрывает все направления агрегированного события вместо перехода на первое', async () => {
    const groupedProfiles = profiles(22)
    groupedProfiles[0] = { slug: 'biology', name: 'Высшая проба — Биология', profile: 'Биология' }
    groupedProfiles[21] = {
      slug: 'oriental-studies',
      name: 'Высшая проба — Востоковедение',
      profile: 'Востоковедение',
    }
    const wrapper = mountCalendar({
      sourceTotal: 22,
      events: [event({
        olympiadSlug: 'biology',
        olympiadName: 'Высшая проба',
        stageName: 'Регистрация',
        profiles: groupedProfiles,
      })],
    })

    const eventSegments = wrapper.findAll('.calendar-desktop button.calendar-event')
    expect(eventSegments).toHaveLength(3)
    expect(eventSegments[0].attributes()).toMatchObject({
      type: 'button',
      'aria-expanded': 'false',
      'aria-controls': 'calendar-profile-choice',
    })
    expect(eventSegments[0].attributes('aria-label')).toContain('22 направления')
    expect(wrapper.find('.calendar-event-selection').exists()).toBe(false)

    await eventSegments[0].trigger('click')

    const picker = wrapper.get('.calendar-event-selection')
    expect(picker.attributes('role')).toBe('region')
    expect(picker.text()).toContain('Выберите направление')
    expect(picker.text()).toContain('22 направления')
    expect(wrapper.findAll('.calendar-desktop button.calendar-event').every(
      (segment) => segment.attributes('aria-expanded') === 'true',
    )).toBe(true)

    const profileLinks = picker.findAllComponents(RouterLinkStub)
    expect(profileLinks).toHaveLength(22)
    expect(profileLinks.map((link) => link.props('to').params.slug)).toEqual(
      expect.arrayContaining(['biology', 'oriental-studies']),
    )
  })

  it('закрывает выбор повторным кликом и сбрасывает его при смене месяца', async () => {
    const wrapper = mountCalendar({
      events: [event({ profiles: profiles(4) })],
    })
    const trigger = wrapper.get('.calendar-desktop button.calendar-event')

    await trigger.trigger('click')
    expect(wrapper.find('.calendar-event-selection').exists()).toBe(true)

    await trigger.trigger('click')
    expect(wrapper.find('.calendar-event-selection').exists()).toBe(false)
    expect(trigger.attributes('aria-expanded')).toBe('false')

    await trigger.trigger('click')
    await wrapper.get('.calendar-event-selection').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.calendar-event-selection').exists()).toBe(false)

    await trigger.trigger('click')
    await wrapper.setProps({
      month: '2026-11',
      events: [event({
        id: 'november-event',
        startsOn: '2026-11-10',
        endsOn: '2026-11-10',
        isRange: false,
        profiles: profiles(3),
      })],
    })
    expect(wrapper.find('.calendar-event-selection').exists()).toBe(false)
    expect(wrapper.get('.calendar-desktop button.calendar-event').attributes('aria-expanded')).toBe('false')
  })

  it('открывает выбор направлений для агрегата из списка «Ещё»', async () => {
    const visibleEvents = Array.from({ length: 4 }, (_, index) => event({
      id: `visible-${index}`,
      olympiadSlug: `visible-${index}`,
      olympiadName: `Видимая олимпиада ${index}`,
      startsOn: '2026-10-12',
      endsOn: '2026-10-12',
      isRange: false,
      profiles: [{
        slug: `visible-${index}`,
        name: `Видимая олимпиада ${index}`,
        profile: 'Математика',
      }],
    }))
    const hiddenAggregate = event({
      id: 'hidden-aggregate',
      olympiadName: 'Скрытый агрегат',
      startsOn: '2026-10-12',
      endsOn: '2026-10-12',
      isRange: false,
      profiles: profiles(5),
    })
    const wrapper = mountCalendar({ events: [...visibleEvents, hiddenAggregate] })

    const hiddenTrigger = wrapper.get('.calendar-more-event')
    expect(hiddenTrigger.text()).toContain('5 направлений')
    await hiddenTrigger.trigger('click')

    expect(wrapper.get('.calendar-event-selection').findAllComponents(RouterLinkStub)).toHaveLength(5)
  })

  it('отправляет события навигации по месяцам', async () => {
    const wrapper = mountCalendar()
    const buttons = wrapper.findAll('.calendar-navigation button')
    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    await buttons[2].trigger('click')

    expect(wrapper.emitted('previous')).toHaveLength(1)
    expect(wrapper.emitted('today')).toHaveLength(1)
    expect(wrapper.emitted('next')).toHaveLength(1)
  })
})
