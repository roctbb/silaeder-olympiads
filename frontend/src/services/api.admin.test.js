import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  adminLogin,
  adminLogout,
  adminSession,
  createAdminOlympiad,
  deleteAdminOlympiad,
  getAdminUsers,
  resetAdminSessionForTests,
  updateAdminOlympiad,
} from './api'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  resetAdminSessionForTests()
  vi.restoreAllMocks()
})

describe('admin API CSRF contract', () => {
  it('запоминает CSRF после входа и передаёт его во всех admin mutations', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({
        authenticated: true,
        username: 'editor',
        csrf_token: 'admin-csrf',
      }))
      .mockResolvedValueOnce(jsonResponse({ slug: 'math' }, 201))
      .mockResolvedValueOnce(jsonResponse({ slug: 'math' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await adminLogin({ username: 'editor', password: 'secret' })
    await createAdminOlympiad({ slug: 'math' })
    await updateAdminOlympiad('math', { slug: 'math' })
    await deleteAdminOlympiad('math')
    await adminLogout()

    expect(fetchMock.mock.calls[0][1].headers.has('X-CSRF-Token')).toBe(false)
    for (const [, options] of fetchMock.mock.calls.slice(1)) {
      expect(options.headers.get('X-CSRF-Token')).toBe('admin-csrf')
      expect(options.credentials).toBe('include')
    }
    expect(fetchMock.mock.calls.map(([, options]) => options.method)).toEqual([
      'POST', 'POST', 'PUT', 'DELETE', 'DELETE',
    ])
  })

  it('восстанавливает CSRF из проверки существующей admin session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({
        authenticated: true,
        username: 'editor',
        csrf_token: 'restored-csrf',
      }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await adminSession()
    await deleteAdminOlympiad('old-card')

    expect(fetchMock.mock.calls[1][1].headers.get('X-CSRF-Token')).toBe('restored-csrf')
  })

  it('передаёт фильтры списка пользователей без CSRF', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ items: [], pagination: {}, summary: {} }))

    await getAdminUsers({ academic_year: '2026/27', q: 'Анна', page: 2, per_page: 25 })

    const [url, options] = fetchMock.mock.calls[0]
    const parsed = new URL(url, 'https://example.test')
    expect(parsed.pathname).toBe('/api/admin/users')
    expect(Object.fromEntries(parsed.searchParams)).toEqual({
      academic_year: '2026/27',
      q: 'Анна',
      page: '2',
      per_page: '25',
    })
    expect(options.credentials).toBe('include')
    expect(options.headers.has('X-CSRF-Token')).toBe(false)
  })
})
