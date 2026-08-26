export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

let adminCsrfToken = ''

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 204) return null

  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message =
      body && typeof body === 'object' && body.error
        ? body.error
        : 'Не удалось выполнить запрос'
    throw new ApiError(message, response.status, body)
  }

  return body
}

function csrfHeaders(csrfToken) {
  return csrfToken ? { 'X-CSRF-Token': csrfToken } : {}
}

export function getMetadata(academicYear = '2026/27', params = {}) {
  const clean = Object.fromEntries(
    Object.entries({ academic_year: academicYear, ...params })
      .filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
  return request('/api/v1/metadata?' + new URLSearchParams(clean))
}

export function getOlympiads(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
  const query = new URLSearchParams(clean)
  return request('/api/v1/olympiads?' + query)
}

export function getCalendarEvents(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
  return request('/api/v1/calendar?' + new URLSearchParams(clean))
}

export function getOlympiad(slug, academicYear = '2026/27') {
  const query = new URLSearchParams({ academic_year: academicYear })
  return request('/api/v1/olympiads/' + encodeURIComponent(slug) + '?' + query)
}

export function getAuthSession() {
  return request('/api/v1/auth/session')
}

export function logoutUser(csrfToken) {
  return request('/api/v1/auth/logout', {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
  })
}

export function getMyPlan(academicYear = '2026/27') {
  return request('/api/v1/me/plan?' + new URLSearchParams({ academic_year: academicYear }))
}

function planningPath(slug, academicYear = '2026/27') {
  return '/api/v1/olympiads/' + encodeURIComponent(slug)
    + '/planning?' + new URLSearchParams({ academic_year: academicYear })
}

export function getOlympiadPlanning(slug, academicYear = '2026/27') {
  return request(planningPath(slug, academicYear))
}

export function addOlympiadToPlan(slug, payload, csrfToken, academicYear = '2026/27') {
  return request(planningPath(slug, academicYear), {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
    body: JSON.stringify(payload || {}),
  })
}

export function updateOlympiadPlan(slug, payload, csrfToken, academicYear = '2026/27') {
  return request(planningPath(slug, academicYear), {
    method: 'PATCH',
    headers: csrfHeaders(csrfToken),
    body: JSON.stringify(payload),
  })
}

export function removeOlympiadFromPlan(slug, csrfToken, academicYear = '2026/27') {
  return request(planningPath(slug, academicYear), {
    method: 'DELETE',
    headers: csrfHeaders(csrfToken),
  })
}

function stageProgressPath(slug, stageId, academicYear = '2026/27') {
  return '/api/v1/olympiads/' + encodeURIComponent(slug)
    + '/stages/' + encodeURIComponent(stageId)
    + '/progress?' + new URLSearchParams({ academic_year: academicYear })
}

export function saveStageProgress(slug, stageId, payload, csrfToken, academicYear = '2026/27') {
  return request(stageProgressPath(slug, stageId, academicYear), {
    method: 'PUT',
    headers: csrfHeaders(csrfToken),
    body: JSON.stringify(payload),
  })
}

export function deleteStageProgress(slug, stageId, csrfToken, academicYear = '2026/27') {
  return request(stageProgressPath(slug, stageId, academicYear), {
    method: 'DELETE',
    headers: csrfHeaders(csrfToken),
  })
}

function rememberAdminSession(session) {
  adminCsrfToken = session?.csrf_token || ''
  return session
}

export async function adminSession() {
  try {
    return rememberAdminSession(await request('/api/admin/session'))
  } catch (error) {
    if (error.status === 401) adminCsrfToken = ''
    throw error
  }
}

export async function adminLogin(credentials) {
  const session = await request('/api/admin/session', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
  return rememberAdminSession(session)
}

export async function adminLogout() {
  try {
    return await request('/api/admin/session', {
      method: 'DELETE',
      headers: csrfHeaders(adminCsrfToken),
    })
  } finally {
    adminCsrfToken = ''
  }
}

export function getAdminOlympiads(academicYear = '2026/27') {
  const query = new URLSearchParams({ academic_year: academicYear })
  return request('/api/admin/olympiads?' + query)
}

export function createAdminOlympiad(payload) {
  return request('/api/admin/olympiads', {
    method: 'POST',
    headers: csrfHeaders(adminCsrfToken),
    body: JSON.stringify(payload),
  })
}

export function updateAdminOlympiad(originalSlug, payload) {
  return request('/api/admin/olympiads/' + encodeURIComponent(originalSlug), {
    method: 'PUT',
    headers: csrfHeaders(adminCsrfToken),
    body: JSON.stringify(payload),
  })
}

export function deleteAdminOlympiad(slug) {
  return request('/api/admin/olympiads/' + encodeURIComponent(slug), {
    method: 'DELETE',
    headers: csrfHeaders(adminCsrfToken),
  })
}

export function resetAdminSessionForTests() {
  adminCsrfToken = ''
}
