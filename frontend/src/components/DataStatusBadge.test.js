import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import DataStatusBadge from './DataStatusBadge.vue'

describe('DataStatusBadge', () => {
  it.each([
    [
      { starts_on: '2026-09-01', date_precision: 'exact', is_date_confirmed: true },
      'confirmed',
      'Дата подтверждена',
      'status-confirmed',
      'fa-circle-check',
    ],
    [
      { starts_on: '2026-09-01', date_precision: 'approximate', is_date_confirmed: false },
      'previous_year_estimate',
      'Ориентир по прошлому году',
      'status-estimate',
      'fa-clock-rotate-left',
    ],
    [
      { starts_on: null, ends_on: null, date_precision: 'tba', is_date_confirmed: false },
      'announcement_pending',
      'Дата уточняется',
      'status-tba',
      'fa-circle-question',
    ],
  ])('показывает корректную уверенность в дате', (stage, dataStatus, label, className, iconClass) => {
    const wrapper = mount(DataStatusBadge, { props: { stage, dataStatus } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.classes()).toContain(className)
    expect(wrapper.get('i.fa-solid').classes()).toContain(iconClass)
  })
})
