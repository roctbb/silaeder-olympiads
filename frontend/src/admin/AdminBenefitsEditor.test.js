import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AdminBenefitsEditor from './AdminBenefitsEditor.vue'
import { emptyBenefit } from './formDefaults'

describe('AdminBenefitsEditor', () => {
  it('показывает оба права и автоматически фиксирует право из основного типа', async () => {
    const benefits = [emptyBenefit()]
    const wrapper = mount(AdminBenefitsEditor, {
      props: { modelValue: benefits },
    })

    const bvi = wrapper.get('#benefit-has-bvi-0')
    const hundredPoints = wrapper.get('#benefit-has-hundred-points-0')
    expect(bvi.element.checked).toBe(false)
    expect(hundredPoints.element.checked).toBe(false)

    await wrapper.get('#benefit-type-0').setValue('bvi')
    expect(benefits[0].has_bvi).toBe(true)
    expect(bvi.element.checked).toBe(true)
    expect(bvi.element.disabled).toBe(true)

    await wrapper.get('#benefit-type-0').setValue('hundred_points')
    expect(benefits[0].has_hundred_points).toBe(true)
    expect(hundredPoints.element.checked).toBe(true)
    expect(hundredPoints.element.disabled).toBe(true)

    await wrapper.get('#benefit-type-0').setValue('prize')
    expect(wrapper.find('#benefit-year-0').exists()).toBe(false)
    expect(wrapper.text()).toContain('Год сезона награды пока не хранится отдельно')
  })
})
