import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OlympiadCard from './OlympiadCard.vue'

function olympiad(overrides = {}) {
  return {
    edition_id: 1,
    slug: 'test',
    name: 'Тестовая олимпиада',
    profile: 'Математика',
    description: '',
    geography: 'russia',
    grades: [],
    data_status: 'announcement_pending',
    registry_status: 'not_listed',
    stages_count: 0,
    next_stage: null,
    ...overrides,
  }
}

describe('OlympiadCard', () => {
  const global = { stubs: { RouterLink: RouterLinkStub } }

  it('показывает завершённый сезон, когда этапы есть, но будущих нет', () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad({ stages_count: 3 }) },
      global,
    })
    expect(wrapper.text()).toContain('Этапы завершены')
    expect(wrapper.text()).not.toContain('Дата уточняется')
    expect(wrapper.get('.status-completed .fa-circle-check').exists()).toBe(true)
  })

  it('показывает TBA, если этапы ещё не объявлены', () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad() },
      global,
    })
    expect(wrapper.text()).toContain('Дата уточняется')
  })

  it('не называет прошлогодний ориентир завершённым сезоном', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          stages_count: 5,
          data_status: 'previous_year_estimate',
          previous_year_reference: '2025/26',
        }),
      },
      global,
    })
    expect(wrapper.text()).toContain('Даты нового сезона уточняются')
    expect(wrapper.text()).not.toContain('Этапы завершены')
  })

  it('публично показывает число пользователей, добавивших олимпиаду в план', () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad({ participant_count: 12 }) },
      global,
    })
    expect(wrapper.text()).toContain('В планах')
    expect(wrapper.text()).toContain('12')
  })

  it('показывает авторизованному пользователю быстрый плюс и заменяет его галочкой', async () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad(), authenticated: true },
      global,
    })

    const button = wrapper.get('.olympiad-card-plan-action')
    expect(button.attributes('aria-label')).toBe('Добавить олимпиаду в мой план')
    expect(button.get('.fa-plus').exists()).toBe(true)
    await button.trigger('click')
    expect(wrapper.emitted('add-to-plan')).toHaveLength(1)

    await wrapper.setProps({ inPlan: true })
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.get('.fa-check').exists()).toBe(true)
  })

  it('не показывает управление личным планом без авторизации', () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad(), authenticated: false },
      global,
    })

    expect(wrapper.find('.olympiad-card-plan-action').exists()).toBe(false)
  })

  it('показывает текстовые условия участия, когда номера классов неприменимы', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          eligibility_notes: 'Учащиеся музыкальных школ без ограничения по классу',
        }),
      },
      global,
    })
    expect(wrapper.text()).toContain('Кто может участвовать')
    expect(wrapper.text()).toContain('Учащиеся музыкальных школ без ограничения по классу')
    expect(wrapper.text()).not.toContain('Классы уточняются')
  })

  it('явно показывает календарный цикл, если он не совпадает с учебным сезоном', () => {
    const wrapper = mount(OlympiadCard, {
      props: { olympiad: olympiad({ cycle_label: 'Календарный цикл 2026' }) },
      global,
    })

    expect(wrapper.get('.badge-cycle').text()).toContain('Календарный цикл 2026')
    expect(wrapper.get('.badge-cycle .fa-calendar-days').exists()).toBe(true)
  })

  it('сохраняет приоритет подтверждённых числовых классов', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          grades: [7, 8, 9],
          eligibility_notes: 'Более широкое текстовое условие',
        }),
      },
      global,
    })
    expect(wrapper.text()).toContain('7–9 классы')
    expect(wrapper.text()).not.toContain('Более широкое текстовое условие')
  })

  it('выделяет только открытую или анонсированную регистрацию', () => {
    const open = mount(OlympiadCard, {
      props: { olympiad: olympiad({ registration_status: 'open' }) },
      global,
    })
    expect(open.text()).toContain('Регистрация открыта')

    const missing = mount(OlympiadCard, {
      props: { olympiad: olympiad({ registration_status: 'not_found' }) },
      global,
    })
    expect(missing.text()).not.toContain('Регистрация не опубликована')
  })

  it('объясняет льготу приёма-2026 и первой показывает совпавшую с фильтрами', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          benefit_summary: [
            {
              benefit_type: 'hundred_points',
              admission_year: 2026,
              university: { slug: 'hse', name: 'НИУ ВШЭ', short_name: 'ВШЭ' },
            },
            {
              benefit_type: 'other',
              admission_year: 2026,
              university: { slug: 'msu', name: 'МГУ имени М. В. Ломоносова', short_name: 'МГУ' },
            },
            {
              benefit_type: 'prize',
              admission_year: 2026,
              university: { slug: 'mipt', name: 'МФТИ', short_name: 'МФТИ' },
            },
            {
              benefit_type: 'bvi',
              admission_year: 2026,
              university: { slug: 'bmstu', name: 'МГТУ имени Н. Э. Баумана', short_name: 'МГТУ' },
            },
            {
              benefit_type: 'grant',
              admission_year: 2026,
              university: { slug: 'itmo', name: 'Университет ИТМО', short_name: 'ИТМО' },
            },
          ],
        }),
        activeBenefitType: 'bvi',
        activeUniversity: 'bmstu',
      },
      global,
    })

    const badges = wrapper.findAll('.benefit-summary-badge')
    expect(badges).toHaveLength(2)
    expect(badges[0].text()).toContain('БВИ · МГТУ · приём 2026')
    expect(wrapper.text()).toContain('Льготы и награды')
    expect(wrapper.get('.benefit-summary-more').text()).toBe('ещё 2')
    expect(wrapper.text()).not.toContain('ИТМО')
  })

  it('не скрывает общую БВИ без конкретного вуза и года приёма', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          benefit_summary: [{
            benefit_type: 'bvi',
            admission_year: null,
            university: null,
          }],
        }),
        activeBenefitType: 'bvi',
      },
      global,
    })

    expect(wrapper.get('.benefit-summary-badge').text()).toBe('БВИ · общее право')
    expect(wrapper.text()).not.toContain('приём 2027')
  })

  it('первой показывает mixed-запись с обоими правами при фильтре БВИ', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          benefit_summary: [
            {
              benefit_type: 'prize',
              admission_year: 2025,
              has_bvi: false,
              has_hundred_points: false,
              university: { slug: 'mipt', name: 'МФТИ', short_name: 'МФТИ' },
            },
            {
              benefit_type: 'other',
              admission_year: 2026,
              has_bvi: true,
              has_hundred_points: true,
              university: { slug: 'hse', name: 'НИУ ВШЭ', short_name: 'ВШЭ' },
            },
          ],
        }),
        activeBenefitType: 'bvi',
        activeUniversity: 'hse',
      },
      global,
    })

    const badges = wrapper.findAll('.benefit-summary-badge')
    expect(badges[0].text()).toBe('БВИ / 100 баллов · ВШЭ · приём 2026')
    expect(badges[1].text()).toBe('Призы · МФТИ')
    expect(wrapper.text()).not.toContain('приём 2025')
  })

  it('не называет приз без вуза общим правом и скрывает его admission_year', () => {
    const wrapper = mount(OlympiadCard, {
      props: {
        olympiad: olympiad({
          benefit_summary: [{
            benefit_type: 'prize',
            admission_year: 2025,
            has_bvi: false,
            has_hundred_points: false,
            university: null,
          }],
        }),
      },
      global,
    })

    expect(wrapper.get('.benefit-summary-badge').text()).toBe('Призы')
    expect(wrapper.text()).not.toContain('приём 2025')
    expect(wrapper.text()).not.toContain('общее право')
  })
})
