import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAuthSession } from './api'
import {
  loginUrl,
  refreshAuth,
  resetAuthForTests,
  useAuth,
} from './auth'

vi.mock('./api', () => ({
  getAuthSession: vi.fn(),
}))

beforeEach(() => {
  resetAuthForTests()
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/olympiads/math?view=details#stages')
})

describe('auth state', () => {
  it('принимает анонимный 200-ответ и строит return URL через backend', async () => {
    getAuthSession.mockResolvedValue({
      authenticated: false,
      user: null,
      csrf_token: null,
      login_url: '/api/v1/auth/login',
    })

    await refreshAuth()
    const { state, authenticated } = useAuth()
    expect(state.initialized).toBe(true)
    expect(authenticated.value).toBe(false)
    expect(loginUrl()).toBe(
      '/api/v1/auth/login?next=%2Folympiads%2Fmath%3Fview%3Ddetails%23stages',
    )
  })

  it('хранит пользователя и CSRF только в общей памяти приложения', async () => {
    getAuthSession.mockResolvedValue({
      authenticated: true,
      user: { id: 1, name: 'Анна', grade: 8 },
      csrf_token: 'csrf-value',
      login_url: '/api/v1/auth/login',
    })

    await refreshAuth()
    const { state, authenticated } = useAuth()
    expect(authenticated.value).toBe(true)
    expect(state.user.name).toBe('Анна')
    expect(state.csrfToken).toBe('csrf-value')
    expect(localStorage.length).toBe(0)
  })

  it('не ломает публичный интерфейс при ошибке проверки сессии', async () => {
    getAuthSession.mockRejectedValue(Object.assign(new Error('Сеть недоступна'), { status: 503 }))
    await expect(refreshAuth()).resolves.toBeNull()
    const { state } = useAuth()
    expect(state.user).toBeNull()
    expect(state.error).toBe('Сеть недоступна')
  })
})
