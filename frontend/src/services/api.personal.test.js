import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  addOlympiadToPlan,
  getAuthSession,
  getOlympiadPlanning,
  saveStageProgress,
} from './api'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('personal API contract', () => {
  it('проверяет сессию с cookies без требования авторизации', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({
      authenticated: false,
      user: null,
    }))

    await getAuthSession()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/session', expect.objectContaining({
      credentials: 'include',
    }))
  })

  it('получает публичное состояние планирования по учебному году', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({
      participant_count: 0,
      public_participants: [],
      plan: null,
    }))

    await getOlympiadPlanning('math & cs')
    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/olympiads/math%20%26%20cs/planning?academic_year=2026%2F27',
    )
  })

  it('передаёт CSRF для добавления в план и результата этапа', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ id: 1 }, 201))
      .mockResolvedValueOnce(jsonResponse({ stage_id: 7 }))

    await addOlympiadToPlan('math', { status: 'planned' }, 'csrf-value')
    await saveStageProgress('math', 7, {
      participated: true,
      advanced: false,
      result: null,
    }, 'csrf-value')

    for (const [, options] of fetchMock.mock.calls) {
      expect(options.headers.get('X-CSRF-Token')).toBe('csrf-value')
      expect(options.credentials).toBe('include')
    }
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[1][1].method).toBe('PUT')
  })
})
