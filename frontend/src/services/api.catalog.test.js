import { afterEach, describe, expect, it, vi } from 'vitest'
import { getCalendarEvents, getMetadata, getOlympiads } from './api'

function jsonResponse(body) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('catalog API contract', () => {
  it('кодирует ограничение доступной регистрации для metadata', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ categories: [], universities: [] }))

    await getMetadata('2026/27', { registration_available: 'true' })

    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/metadata?academic_year=2026%2F27&registration_available=true',
    )
  })

  it('кодирует фильтры льготы и вуза для списка и календаря', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ items: [], pagination: {} }))
      .mockResolvedValueOnce(jsonResponse({ events: [], total: 0 }))

    const filters = {
      academic_year: '2026/27',
      benefit_type: 'hundred_points',
      university: 'hse-moscow',
    }
    await getOlympiads(filters)
    await getCalendarEvents({ ...filters, month: '2026-10' })

    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/olympiads?academic_year=2026%2F27&benefit_type=hundred_points&university=hse-moscow',
    )
    expect(fetchMock.mock.calls[1][0]).toBe(
      '/api/v1/calendar?academic_year=2026%2F27&benefit_type=hundred_points&university=hse-moscow&month=2026-10',
    )
  })

  it('кодирует укрупнённое direction одинаково для списка и календаря', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ items: [], pagination: {} }))
      .mockResolvedValueOnce(jsonResponse({ events: [], total: 0 }))

    await getOlympiads({ academic_year: '2026/27', direction: 'natural-sciences' })
    await getCalendarEvents({
      academic_year: '2026/27',
      direction: 'natural-sciences',
      month: '2026-11',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/olympiads?academic_year=2026%2F27&direction=natural-sciences',
    )
    expect(fetchMock.mock.calls[1][0]).toBe(
      '/api/v1/calendar?academic_year=2026%2F27&direction=natural-sciences&month=2026-11',
    )
  })
})
