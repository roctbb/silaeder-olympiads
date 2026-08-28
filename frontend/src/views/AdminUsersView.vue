<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import { adminLogout, adminSession, getAdminUsers } from '../services/api'
import { LABELS, pluralize } from '../utils/format'

const router = useRouter()
const academicYear = '2026/27'
const items = ref([])
const username = ref('')
const search = ref('')
const appliedSearch = ref('')
const loading = ref(true)
const error = ref('')
const summary = ref({ total_users: 0, users_with_plans: 0, plans_total: 0 })
const pagination = ref({ page: 1, per_page: 25, total: 0, pages: 0 })

const planStatusLabels = {
  planned: 'В плане',
  registered: 'Зарегистрирован',
  participating: 'Участвует',
  completed: 'Завершено',
}

const dateTimeFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatDateTime(value) {
  if (!value) return 'Неизвестно'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Неизвестно' : dateTimeFormatter.format(date)
}

function userIdentity(item) {
  return item.preferred_username ? '@' + item.preferred_username : item.email || 'Без логина'
}

async function loadUsers(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const result = await getAdminUsers({
      academic_year: academicYear,
      q: appliedSearch.value,
      page,
      per_page: pagination.value.per_page,
    })
    items.value = result.items
    summary.value = result.summary
    pagination.value = result.pagination
  } catch (caught) {
    if (caught.status === 401) {
      await router.replace({ name: 'admin-login', query: { redirect: '/admin/users' } })
      return
    }
    error.value = caught.message || 'Не удалось загрузить пользователей.'
  } finally {
    loading.value = false
  }
}

async function initialize() {
  try {
    const session = await adminSession()
    username.value = session.username
    await loadUsers()
  } catch (caught) {
    if (caught.status === 401) {
      await router.replace({ name: 'admin-login', query: { redirect: '/admin/users' } })
      return
    }
    error.value = caught.message || 'Не удалось открыть раздел пользователей.'
    loading.value = false
  }
}

function applySearch() {
  appliedSearch.value = search.value.trim()
  loadUsers(1)
}

function clearSearch() {
  search.value = ''
  appliedSearch.value = ''
  loadUsers(1)
}

async function logout() {
  await adminLogout()
  await router.replace({ name: 'admin-login' })
}

onMounted(initialize)
</script>

<template>
  <div class="container py-4 py-lg-5 admin-users">
    <header class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-start gap-3 mb-4">
      <div>
        <p class="eyebrow mb-1">Редактор · {{ username || '…' }}</p>
        <h1 class="h2 mb-2">Пользователи и планы</h1>
        <p class="text-body-secondary mb-0">
          Выбранные олимпиады на {{ academicYear }} учебный год.
        </p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <RouterLink class="btn btn-outline-primary" :to="{ name: 'admin' }">
          <i class="fa-solid fa-list me-1" aria-hidden="true"></i>
          Олимпиады
        </RouterLink>
        <button type="button" class="btn btn-outline-secondary" @click="logout">Выйти</button>
      </div>
    </header>

    <LoadingState v-if="loading" />
    <template v-else>
      <ErrorAlert v-if="error" :message="error" @retry="loadUsers(pagination.page)" />

      <div class="row g-3 mb-4" aria-label="Сводка по пользователям">
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ summary.total_users }}</strong><span>пользователей</span>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ summary.users_with_plans }}</strong><span>с планами</span>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ summary.plans_total }}</strong><span>выборов олимпиад</span>
          </div>
        </div>
      </div>

      <section class="card border-0 shadow-sm" aria-labelledby="admin-users-title">
        <div class="card-body border-bottom p-3 p-md-4">
          <h2 id="admin-users-title" class="visually-hidden">Список пользователей</h2>
          <form class="d-flex flex-column flex-sm-row gap-2" role="search" @submit.prevent="applySearch">
            <label for="admin-user-search" class="visually-hidden">Поиск пользователя</label>
            <input
              id="admin-user-search"
              v-model="search"
              class="form-control"
              type="search"
              placeholder="Имя, логин или email"
            />
            <button class="btn btn-primary" type="submit">Найти</button>
            <button
              v-if="appliedSearch"
              class="btn btn-outline-secondary"
              type="button"
              @click="clearSearch"
            >
              Сбросить
            </button>
          </form>
        </div>

        <div v-if="items.length" class="admin-user-list">
          <details v-for="item in items" :key="item.id" class="admin-user-item">
            <summary class="admin-user-summary">
              <span class="admin-user-avatar" aria-hidden="true">
                <i class="fa-solid fa-user"></i>
              </span>
              <span class="admin-user-main">
                <strong>{{ item.name }}</strong>
                <small>{{ userIdentity(item) }}<template v-if="item.email && item.preferred_username"> · {{ item.email }}</template></small>
              </span>
              <span class="admin-user-grade">
                {{ item.grade ? item.grade + ' класс' : 'Класс не указан' }}
              </span>
              <span class="admin-user-login">
                Последний вход<br />{{ formatDateTime(item.last_login_at) }}
              </span>
              <span class="badge rounded-pill text-bg-primary admin-user-plan-count">
                {{ item.plan_count }}
                {{ pluralize(item.plan_count, 'олимпиада', 'олимпиады', 'олимпиад') }}
              </span>
              <i class="fa-solid fa-chevron-down admin-user-chevron" aria-hidden="true"></i>
            </summary>

            <div class="admin-user-plans">
              <div v-if="item.plans.length" class="row g-3">
                <div v-for="plan in item.plans" :key="plan.id" class="col-md-6 col-xl-4">
                  <article class="admin-user-plan-card h-100">
                    <div class="d-flex align-items-start justify-content-between gap-2 mb-2">
                      <span class="badge text-bg-light">
                        {{ planStatusLabels[plan.status] || plan.status }}
                      </span>
                      <span v-if="plan.edition_status === 'archived'" class="badge text-bg-secondary">
                        Архив
                      </span>
                    </div>
                    <p class="eyebrow mb-1">{{ plan.olympiad.profile }}</p>
                    <h3 class="h6 mb-2">{{ plan.olympiad.name }}</h3>
                    <p class="small text-body-secondary mb-3">
                      Добавлено {{ formatDateTime(plan.created_at) }}
                    </p>
                    <div class="d-flex flex-wrap gap-2 small mb-3">
                      <span v-if="plan.is_name_public">
                        <i class="fa-solid fa-eye me-1" aria-hidden="true"></i>Имя видно
                      </span>
                      <span v-else class="text-body-secondary">
                        <i class="fa-solid fa-eye-slash me-1" aria-hidden="true"></i>Имя скрыто
                      </span>
                      <span v-if="plan.reminders_enabled">
                        <i class="fa-solid fa-bell me-1" aria-hidden="true"></i>
                        {{ plan.reminder_days_before.join(', ') }} дн.
                      </span>
                    </div>
                    <RouterLink
                      class="btn btn-sm btn-outline-primary"
                      :to="{ name: 'olympiad', params: { slug: plan.olympiad.slug } }"
                    >
                      Открыть карточку
                    </RouterLink>
                  </article>
                </div>
              </div>
              <p v-else class="mb-0 text-body-secondary">
                На этот учебный год пользователь пока ничего не добавил.
              </p>
            </div>
          </details>
        </div>
        <div v-else class="empty-state m-3 m-md-4 p-4 text-center text-body-secondary">
          {{ appliedSearch ? 'Пользователи не найдены.' : 'Пользователей пока нет.' }}
        </div>

        <nav
          v-if="pagination.pages > 1"
          class="d-flex align-items-center justify-content-between gap-3 border-top p-3 p-md-4"
          aria-label="Страницы пользователей"
        >
          <button
            class="btn btn-sm btn-outline-secondary"
            type="button"
            :disabled="pagination.page <= 1"
            @click="loadUsers(pagination.page - 1)"
          >
            Назад
          </button>
          <span class="small text-body-secondary">
            Страница {{ pagination.page }} из {{ pagination.pages }}
          </span>
          <button
            class="btn btn-sm btn-outline-secondary"
            type="button"
            :disabled="pagination.page >= pagination.pages"
            @click="loadUsers(pagination.page + 1)"
          >
            Далее
          </button>
        </nav>
      </section>
    </template>
  </div>
</template>
