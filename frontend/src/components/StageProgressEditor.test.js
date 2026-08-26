import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StageProgressEditor from './StageProgressEditor.vue'

const stage = { id: 42, name: 'Заключительный этап' }

describe('StageProgressEditor', () => {
  it('восстанавливает сохранённый результат и отправляет полный контракт', async () => {
    const wrapper = mount(StageProgressEditor, {
      props: {
        stage,
        progress: {
          stage_id: 42,
          participated: true,
          advanced: false,
          result: '73 балла',
          updated_at: '2026-08-26T10:00:00Z',
        },
      },
    })

    expect(wrapper.get('#participated-42').element.checked).toBe(true)
    expect(wrapper.get('#result-42').element.value).toBe('73 балла')
    expect(wrapper.get('#advanced-42').element.value).toBe('no')
    await wrapper.get('#advanced-42').setValue('yes')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('save')[0][0]).toEqual({
      stage_id: 42,
      participated: true,
      advanced: true,
      result: '73 балла',
    })
  })

  it('очищает зависимые поля, если участие снято', async () => {
    const wrapper = mount(StageProgressEditor, {
      props: {
        stage,
        progress: { participated: true, advanced: true, result: 'Призёр' },
      },
    })

    await wrapper.get('#participated-42').setValue(false)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')[0][0]).toEqual({
      stage_id: 42,
      participated: false,
      advanced: null,
      result: null,
    })
  })

  it('блокирует повторное сохранение во время запроса', () => {
    const wrapper = mount(StageProgressEditor, { props: { stage, saving: true } })
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Сохраняем')
  })

  it('позволяет полностью удалить сохранённую отметку', async () => {
    const wrapper = mount(StageProgressEditor, {
      props: { stage, progress: { participated: true, advanced: null, result: null } },
    })
    await wrapper.get('button.text-danger').trigger('click')
    expect(wrapper.emitted('clear')).toEqual([[42]])
  })
})
