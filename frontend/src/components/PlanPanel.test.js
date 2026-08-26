import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PlanPanel from './PlanPanel.vue'

function planning(plan = null) {
  return {
    participant_count: 3,
    public_participants: [{ name: 'Анна' }, { name: 'Михаил' }],
    plan,
  }
}

describe('PlanPanel', () => {
  it('не мешает публичному просмотру и предлагает безопасный вход через backend', () => {
    const wrapper = mount(PlanPanel, {
      props: { authenticated: false, planning: planning() },
    })

    expect(wrapper.text()).toContain('3 выбрали эту олимпиаду')
    expect(wrapper.text()).toContain('Просмотр олимпиады останется доступен без входа')
    expect(wrapper.get('a').attributes('href')).toMatch(/^\/api\/v1\/auth\/login\?next=/)
    expect(wrapper.text()).toContain('Анна')
  })

  it('добавляет олимпиаду только явным действием пользователя', async () => {
    const wrapper = mount(PlanPanel, {
      props: { authenticated: true, planning: planning() },
    })

    await wrapper.get('button.btn-primary').trigger('click')
    expect(wrapper.emitted('add')).toHaveLength(1)
  })

  it('сохраняет статус, opt-in имени и выбранные напоминания', async () => {
    const wrapper = mount(PlanPanel, {
      props: {
        authenticated: true,
        planning: planning({
          status: 'planned',
          is_name_public: false,
          reminders_enabled: true,
          reminder_days_before: [7, 1],
          stage_progress: [],
        }),
      },
    })

    await wrapper.get('#plan-status').setValue('registered')
    await wrapper.get('#plan-public-name').setValue(true)
    await wrapper.get('#reminder-day-3').setValue(true)
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('save-settings')[0][0]).toEqual({
      status: 'registered',
      is_name_public: true,
      reminders_enabled: true,
      reminder_days_before: [7, 3, 1],
    })
  })

  it('не позволяет включить напоминания без единого срока', async () => {
    const wrapper = mount(PlanPanel, {
      props: {
        authenticated: true,
        planning: planning({
          status: 'planned',
          is_name_public: false,
          reminders_enabled: true,
          reminder_days_before: [1],
          stage_progress: [],
        }),
      },
    })

    await wrapper.get('#reminder-day-1').setValue(false)
    expect(wrapper.text()).toContain('Выберите хотя бы один срок')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('сохраняет сроки при выключении доставки, чтобы backend мог принять настройки', async () => {
    const wrapper = mount(PlanPanel, {
      props: {
        authenticated: true,
        planning: planning({
          status: 'planned',
          is_name_public: false,
          reminders_enabled: true,
          reminder_days_before: [7, 1],
          stage_progress: [],
        }),
      },
    })

    await wrapper.get('#plan-reminders').setValue(false)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save-settings')[0][0]).toMatchObject({
      reminders_enabled: false,
      reminder_days_before: [7, 1],
    })
  })
})
