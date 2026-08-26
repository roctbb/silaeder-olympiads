import { describe, expect, it } from 'vitest'
import {
  LABELS,
  admissionYearLabel,
  benefitDisplayType,
  benefitHasRight,
  dateConfidence,
  formatDateRange,
  formatStageDate,
  gradesLabel,
  pluralize,
} from './format'

describe('форматирование каталога', () => {
  it('не называет справочную запись льготой', () => {
    expect(LABELS.benefitType.other).toBe('Информация')
  })

  it('даёт понятные подписи типам льгот в фильтре', () => {
    expect(LABELS.benefitFilterType).toEqual({
      bvi: 'Есть вариант БВИ',
      hundred_points: 'Есть вариант 100 баллов',
      other: 'Иные условия',
      prize: 'Призы',
    })
  })

  it('понимает смешанную запись с БВИ и 100 баллами и старый API без флагов', () => {
    const mixed = {
      benefit_type: 'other',
      has_bvi: true,
      has_hundred_points: true,
    }
    expect(benefitHasRight(mixed, 'bvi')).toBe(true)
    expect(benefitHasRight(mixed, 'hundred_points')).toBe(true)
    expect(benefitHasRight(mixed, 'other')).toBe(true)
    expect(benefitDisplayType(mixed)).toBe('БВИ / 100 баллов')
    expect(benefitHasRight({ benefit_type: 'bvi' }, 'bvi')).toBe(true)
    expect(benefitHasRight({ benefit_type: 'hundred_points' }, 'hundred_points')).toBe(true)
  })

  it('подписывает год приёма только у вузовской льготы, но не у приза', () => {
    expect(admissionYearLabel({
      benefit_type: 'bvi',
      admission_year: 2026,
      university: { slug: 'mipt' },
    })).toBe('Приём 2026')
    expect(admissionYearLabel({
      benefit_type: 'other',
      admission_year: 2026,
      university: { slug: 'hse' },
    }, true)).toBe('приём 2026')
    expect(admissionYearLabel({
      benefit_type: 'prize',
      admission_year: 2025,
      university: { slug: 'mipt' },
    })).toBe('')
    expect(admissionYearLabel({
      benefit_type: 'bvi',
      admission_year: 2026,
      university: null,
    })).toBe('')
  })

  it('не сдвигает ISO-даты из-за часового пояса', () => {
    expect(formatDateRange('2026-10-01', '2026-10-31')).toBe(
      '1 октября 2026 г. — 31 октября 2026 г.',
    )
  })

  it('не превращает месячную или примерную точность в точную дату', () => {
    expect(
      formatStageDate({
        starts_on: '2026-09-01',
        ends_on: null,
        date_precision: 'month',
      }),
    ).toBe('сентябрь 2026 г.')
    expect(
      formatStageDate({
        starts_on: '2026-10-01',
        ends_on: '2026-10-31',
        date_precision: 'approximate',
      }),
    ).toBe('примерно 1 октября 2026 г. — 31 октября 2026 г.')
  })

  it('честно подписывает неизвестные классы', () => {
    expect(gradesLabel([])).toBe('Классы уточняются')
    expect(gradesLabel([5, 6, 7, 8, 9, 10, 11])).toBe('5–11 классы')
  })

  it('различает подтверждённую, ориентировочную и неизвестную дату', () => {
    expect(
      dateConfidence(
        { starts_on: '2026-09-01', date_precision: 'exact', is_date_confirmed: true },
        'confirmed',
      ),
    ).toBe('confirmed')
    expect(
      dateConfidence(
        { starts_on: '2026-09-01', date_precision: 'approximate', is_date_confirmed: false },
        'previous_year_estimate',
      ),
    ).toBe('previous_year_estimate')
    expect(dateConfidence({ date_precision: 'tba' }, 'announcement_pending')).toBe('tba')
    expect(
      dateConfidence(
        { starts_on: '2026-09-01', date_precision: 'approximate', is_date_confirmed: false },
        'partial',
      ),
    ).toBe('tba')
  })

  it('склоняет русские счётчики', () => {
    expect(pluralize(1, 'этап', 'этапа', 'этапов')).toBe('этап')
    expect(pluralize(3, 'этап', 'этапа', 'этапов')).toBe('этапа')
    expect(pluralize(11, 'этап', 'этапа', 'этапов')).toBe('этапов')
    expect(pluralize(21, 'этап', 'этапа', 'этапов')).toBe('этап')
  })
})
