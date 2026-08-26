import { describe, expect, it } from 'vitest'
import {
  buildMonthDays,
  eventsOverlappingMonth,
  formatMonthLabel,
  groupCalendarEvents,
  isValidMonthKey,
  monthBounds,
  normalizeCalendarEvents,
  shiftMonthKey,
} from './calendar'

function record(overrides = {}) {
  return {
    id: 10,
    olympiad: {
      slug: 'test-math',
      name: 'Тестовая олимпиада',
      profile: 'Математика',
      data_status: 'confirmed',
    },
    stage: {
      id: 10,
      name: 'Финал',
      starts_on: '2026-09-29',
      ends_on: '2026-10-02',
      date_precision: 'exact',
      is_date_confirmed: true,
      format: 'offline',
    },
    ...overrides,
  }
}

describe('calendar utils', () => {
  it('проверяет и переключает месяцы через границу года', () => {
    expect(isValidMonthKey('2026-09')).toBe(true)
    expect(isValidMonthKey('2026-13')).toBe(false)
    expect(shiftMonthKey('2026-12', 1)).toBe('2027-01')
    expect(shiftMonthKey('2027-01', -1)).toBe('2026-12')
    expect(formatMonthLabel('2026-09')).toBe('Сентябрь 2026 г.')
    expect(monthBounds('2026-09')).toEqual({ startsOn: '2026-09-01', endsOn: '2026-09-30' })
  })

  it('отличает доверие к источнику от точности формулировки даты', () => {
    const [confirmed, estimate] = normalizeCalendarEvents([
      record({
        id: 9,
        stage: { ...record().stage, id: 9, starts_on: '2026-09-28', ends_on: '2026-09-28' },
      }),
      record({
        id: 11,
        stage: { ...record().stage, id: 11, date_precision: 'approximate' },
      }),
    ])

    expect(confirmed).toMatchObject({
      olympiadSlug: 'test-math',
      startsOn: '2026-09-28',
      endsOn: '2026-09-28',
      isRange: false,
      confidence: 'confirmed',
    })
    expect(estimate).toMatchObject({
      isRange: true,
      confidence: 'confirmed',
      displayStatus: 'estimate',
      previousYearEstimate: false,
    })
  })

  it('помечает прошлогодний ориентир неподтверждённым независимо от stage flag', () => {
    const [event] = normalizeCalendarEvents([
      record({
        olympiad: { ...record().olympiad, data_status: 'previous_year_estimate' },
      }),
    ])
    expect(event).toMatchObject({
      confidence: 'estimate',
      displayStatus: 'estimate',
      previousYearEstimate: true,
    })
  })

  it('сохраняет семантику крайнего срока с одной ends_on', () => {
    const [deadline] = normalizeCalendarEvents([
      record({
        stage: {
          ...record().stage,
          starts_on: null,
          ends_on: '2026-10-31',
          date_precision: 'exact',
        },
      }),
    ])

    expect(deadline).toMatchObject({
      startsOn: '2026-10-31',
      endsOn: '2026-10-31',
      isDeadline: true,
      isRange: false,
    })
  })

  it('переносит явную метку календарного цикла в событие', () => {
    const [event] = normalizeCalendarEvents([
      record({
        olympiad: {
          ...record().olympiad,
          cycle_label: 'Сезон 2026',
        },
      }),
    ])

    expect(event.cycleLabel).toBe('Сезон 2026')
  })

  it('объединяет одинаковые family, этап и диапазон, сохраняя профили', () => {
    const records = [
      record(),
      record({
        id: 11,
        olympiad: {
          ...record().olympiad,
          slug: 'test-physics',
          name: 'Тестовая олимпиада — Физика',
          family_name: 'Тестовая олимпиада',
          profile: 'Физика',
        },
      }),
    ]
    records[0].olympiad.family_name = 'Тестовая олимпиада'

    const groups = groupCalendarEvents(normalizeCalendarEvents(records))
    expect(groups).toHaveLength(1)
    expect(groups[0].profiles.map((profile) => profile.profile)).toEqual(['Математика', 'Физика'])
  })

  it('включает пересекающиеся с месяцем диапазоны и исключает остальные', () => {
    const events = normalizeCalendarEvents([
      record(),
      record({
        id: 12,
        stage: { ...record().stage, id: 12, starts_on: '2026-11-01', ends_on: '2026-11-02' },
      }),
    ])
    expect(eventsOverlappingMonth('2026-10', events).map((event) => event.id)).toEqual(['10'])
  })

  it('строит полные недели с понедельника и размечает сегменты диапазона', () => {
    const events = normalizeCalendarEvents([record()])
    const days = buildMonthDays('2026-10', events, '2026-10-01')

    expect(days).toHaveLength(35)
    expect(days[0].date).toBe('2026-09-28')
    expect(days.at(-1).date).toBe('2026-11-01')
    expect(days[0].weekday).toBe(0)
    expect(days.find((day) => day.date === '2026-10-01').isToday).toBe(true)
    expect(days.find((day) => day.date === '2026-09-29').events[0]).toMatchObject({
      segmentStarts: true,
      segmentEnds: false,
    })
    expect(days.find((day) => day.date === '2026-10-02').events[0]).toMatchObject({
      segmentEnds: true,
    })
  })
})
