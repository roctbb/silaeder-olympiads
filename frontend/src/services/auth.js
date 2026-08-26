import { computed, reactive, readonly } from 'vue'
import { getAuthSession } from './api'

const authState = reactive({
  initialized: false,
  loading: false,
  user: null,
  csrfToken: null,
  loginPath: '/api/v1/auth/login',
  error: '',
})

let pendingSession = null

export function currentReturnTo() {
  if (typeof window === 'undefined') return '/'
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export function loginUrl(returnTo = currentReturnTo()) {
  return `${authState.loginPath}?${new URLSearchParams({ next: returnTo })}`
}

export async function refreshAuth({ force = false } = {}) {
  if (pendingSession && !force) return pendingSession
  if (authState.initialized && !force) return authState.user

  authState.loading = true
  authState.error = ''
  pendingSession = getAuthSession()
    .then((session) => {
      authState.user = session?.authenticated ? session.user : null
      authState.csrfToken = session?.csrf_token || null
      authState.loginPath = session?.login_url || '/api/v1/auth/login'
      authState.initialized = true
      return authState.user
    })
    .catch((error) => {
      authState.user = null
      authState.csrfToken = null
      authState.initialized = true
      if (error.status !== 401) {
        authState.error = error.message || 'Не удалось проверить вход.'
      }
      return null
    })
    .finally(() => {
      authState.loading = false
      pendingSession = null
    })

  return pendingSession
}

export function clearAuth() {
  authState.user = null
  authState.csrfToken = null
  authState.initialized = true
  authState.error = ''
}

export function setAuthenticatedUser(user) {
  authState.user = user
  authState.initialized = true
}

export function useAuth() {
  return {
    state: readonly(authState),
    authenticated: computed(() => Boolean(authState.user)),
    refresh: refreshAuth,
    clear: clearAuth,
    setUser: setAuthenticatedUser,
  }
}

export function resetAuthForTests() {
  authState.initialized = false
  authState.loading = false
  authState.user = null
  authState.csrfToken = null
  authState.loginPath = '/api/v1/auth/login'
  authState.error = ''
  pendingSession = null
}
