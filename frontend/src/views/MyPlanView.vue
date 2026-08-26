<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import LoginPrompt from '../components/LoginPrompt.vue'
import {
  getMyPlan,
  removeOlympiadFromPlan,
  updateOlympiadPlan,
} from '../services/api'
import { useAuth } from '../services/auth'
import { formatStageDate, pluralize } from '../utils/format'

const ACADEMIC_YEAR = '2026/27'
const { state: auth, authenticated, refresh: refreshAuth, clear: clearAuth } = useAuth()
const plan = ref({ items: [], upcoming_stages: [] })
const loading = ref(false)
const error = ref('')
const archivedAction = ref('')
let requestSequence = 0

const resultCount = computed(() => plan.value.items.reduce(
  (total, item) => total + (item.stage_progress?.length || 0),
  0,
))

const statusLabels = {
  planned: 'В планах',
  registered: 'Зарегистрирован',
  participating: 'Участвую',
  completed: 'Завершено',
}

async function loadPlan() {
  if (!authenticated.value) return
  const sequence = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const result = await getMyPlan(ACADEMIC_YEAR)
    if (sequence === requestSequence) plan.value = result
  } catch (caught) {
    if (sequence !== requestSequence) return
    if (caught.status === 401) {
      clearAuth()
      return
    }
    error.value = caught.message || 'Не удалось загрузить ваш план.'
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

function archivedActionKey(item, action) {
  return `${item.id}:${action}`
}

async function deactivateArchivedPlan(item) {
  archivedAction.value = archivedActionKey(item, 'deactivate')
  error.value = ''
  try {
    const updated = await updateOlympiadPlan(
      item.olympiad.slug,
      {
        is_name_public: false,
        reminders_enabled: false,
        reminder_days_before: [],
      },
      auth.csrfToken,
      item.academic_year,
    )
    plan.value.items = plan.value.items.map((candidate) => (
      candidate.id === item.id ? updated : candidate
    ))
  } catch (caught) {
    if (caught.status === 401) clearAuth()
    else error.value = caught.message || 'Не удалось обновить архивный план.'
  } finally {
    archivedAction.value = ''
  }
}

async function removeArchivedPlan(item) {
  if (!window.confirm('Удалить архивную олимпиаду из плана вместе с отметками этапов?')) return
  archivedAction.value = archivedActionKey(item, 'remove')
  error.value = ''
  try {
    await removeOlympiadFromPlan(
      item.olympiad.slug,
      auth.csrfToken,
      item.academic_year,
    )
    plan.value.items = plan.value.items.filter((candidate) => candidate.id !== item.id)
  } catch (caught) {
    if (caught.status === 401) clearAuth()
    else error.value = caught.message || 'Не удалось удалить архивный план.'
  } finally {
    archivedAction.value = ''
  }
}

watch(
  () => [auth.initialized, authenticated.value],
  ([initialized, signedIn], previous) => {
    if (initialized && signedIn && (!previous || !previous[1])) loadPlan()
  },
  { immediate: true },
)

onMounted(refreshAuth)
</script>

<template>
  <section class="my-plan-hero">
    <div class="container py-4 py-lg-5">
      <p class="eyebrow mb-2">2026/27 учебный год</p>
      <h1 class="display-6 fw-bold mb-2">Мой план</h1>
      <p class="text-body-secondary mb-0">
        Олимпиады, ближайшие этапы и ваши результаты в одном месте.
      </p>
    </div>
  </section>

  <div class="container py-4 py-lg-5">
    <LoadingState v-if="auth.loading && !auth.initialized" />

    <LoginPrompt
      v-else-if="!authenticated"
      title="Личный план доступен после входа"
      description="Каталог и календарь можно смотреть без авторизации. Войдите через ЛК, чтобы сохранять олимпиады и результаты."
    />

    <template v-else>
      <section class="card border-0 shadow-sm mb-4" aria-labelledby="profile-settings-title">
        <div class="card-body p-3 p-md-4">
          <div class="row g-3 align-items-center">
            <div class="col-md">
              <h2 id="profile-settings-title" class="h5 mb-1">{{ auth.user.name }}</h2>
              <p class="small text-body-secondary mb-0">
                Класс синхронизируется из профиля ученика в ЛК Силаэдр при каждом входе.
              </p>
            </div>
            <div class="col-sm-auto">
              <span class="badge text-bg-primary fs-6">
                <i class="fa-solid fa-graduation-cap me-1" aria-hidden="true"></i>
                {{ auth.user.grade ? `${auth.user.grade} класс` : 'Класс не указан в ЛК' }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <LoadingState v-if="loading" />
      <ErrorAlert v-else-if="error" :message="error" @retry="loadPlan" />

      <template v-else>
        <div class="hero-stat-grid mb-4" aria-label="Статистика личного плана">
          <div>
            <strong>{{ plan.items.length }}</strong>
            <span>{{ pluralize(plan.items.length, 'олимпиада', 'олимпиады', 'олимпиад') }}</span>
          </div>
          <div>
            <strong>{{ plan.upcoming_stages.length }}</strong>
            <span>предстоящих этапов</span>
          </div>
          <div>
            <strong>{{ resultCount }}</strong>
            <span>отметок результата</span>
          </div>
        </div>

        <section class="mb-5" aria-labelledby="upcoming-plan-title">
          <div class="section-heading">
            <div>
              <p class="eyebrow mb-1">Ближайшее</p>
              <h2 id="upcoming-plan-title" class="h3 mb-0">Предстоящие этапы</h2>
            </div>
          </div>
          <div v-if="plan.upcoming_stages.length" class="vstack gap-2">
            <RouterLink
              v-for="stage in plan.upcoming_stages"
              :key="`${stage.olympiad.slug}-${stage.stage_id}`"
              class="my-plan-event"
              :to="{ name: 'olympiad', params: { slug: stage.olympiad.slug }, hash: '#stages' }"
            >
              <span class="my-plan-event-date">{{ formatStageDate(stage, true) }}</span>
              <span class="min-w-0">
                <strong class="d-block">{{ stage.stage_name }}</strong>
                <small class="text-body-secondary">
                  {{ stage.olympiad.family_name }} · {{ stage.olympiad.profile }}
                </small>
              </span>
              <span v-if="stage.progress?.participated" class="status-badge status-confirmed">
                <i class="fa-solid fa-check" aria-hidden="true"></i>
                Участвовал
              </span>
              <i v-else class="fa-solid fa-chevron-right text-primary" aria-hidden="true"></i>
            </RouterLink>
          </div>
          <div v-else class="empty-state rounded-4 p-4">
            <p class="mb-0 text-body-secondary">
              <i class="fa-solid fa-calendar-day me-2" aria-hidden="true"></i>
              В плане пока нет предстоящих этапов с опубликованными датами.
            </p>
          </div>
        </section>

        <section aria-labelledby="plan-list-title">
          <div class="section-heading">
            <div>
              <p class="eyebrow mb-1">Все выбранные</p>
              <h2 id="plan-list-title" class="h3 mb-0">Олимпиады в плане</h2>
            </div>
          </div>
          <div v-if="plan.items.length" class="row g-3">
            <div v-for="item in plan.items" :key="item.id" class="col-md-6 col-xl-4">
              <article class="card my-plan-card h-100 border-0 shadow-sm">
                <div class="card-body p-4 d-flex flex-column">
                  <div class="d-flex align-items-start justify-content-between gap-2 mb-3">
                    <div class="d-flex flex-wrap gap-2">
                      <span class="badge text-bg-primary">{{ statusLabels[item.status] || item.status }}</span>
                      <span v-if="item.edition_status === 'archived'" class="badge text-bg-secondary">
                        Архивная карточка
                      </span>
                    </div>
                    <i
                      v-if="item.reminders_enabled && item.edition_status !== 'archived'"
                      class="fa-solid fa-bell text-primary"
                      title="Напоминания включены"
                      aria-label="Напоминания включены"
                    ></i>
                  </div>
                  <p class="eyebrow mb-2">{{ item.olympiad.profile }}</p>
                  <h3 class="h5">{{ item.olympiad.name }}</h3>
                  <p class="small text-body-secondary mb-3">
                    {{ item.stage_progress.length }}
                    {{ pluralize(item.stage_progress.length, 'отметка', 'отметки', 'отметок') }}
                    по этапам
                  </p>
                  <ul v-if="item.stage_progress.length" class="my-plan-progress-list list-unstyled mb-3">
                    <li v-for="progress in item.stage_progress" :key="progress.stage_id">
                      <strong>
                        {{ progress.stage_name }}
                        <span v-if="progress.stage_is_active === false" class="badge text-bg-secondary ms-1">
                          Архивный этап
                        </span>
                      </strong>
                      <span class="text-body-secondary">
                        <template v-if="progress.participated">Участвовал</template>
                        <template v-else>Не участвовал</template>
                        <template v-if="progress.advanced === true"> · прошёл дальше</template>
                        <template v-else-if="progress.advanced === false"> · не прошёл дальше</template>
                        <template v-if="progress.result"> · {{ progress.result }}</template>
                      </span>
                    </li>
                  </ul>
                  <div
                    v-if="item.edition_status === 'archived'"
                    class="alert alert-secondary small mt-auto mb-3"
                    role="note"
                  >
                    Карточка больше не публикуется в каталоге. Ваши прежние отметки сохранены
                    и доступны только вам.
                  </div>
                  <div v-if="item.edition_status === 'archived'" class="d-grid gap-2">
                    <button
                      v-if="item.is_name_public || item.reminders_enabled"
                      class="btn btn-sm btn-outline-secondary archived-plan-deactivate"
                      type="button"
                      :disabled="Boolean(archivedAction)"
                      @click="deactivateArchivedPlan(item)"
                    >
                      <i class="fa-solid fa-user-shield me-1" aria-hidden="true"></i>
                      {{ archivedAction === archivedActionKey(item, 'deactivate')
                        ? 'Сохраняем…'
                        : item.is_name_public
                          ? 'Скрыть имя и отключить напоминания'
                          : 'Отключить напоминания' }}
                    </button>
                    <button
                      class="btn btn-sm btn-outline-danger archived-plan-remove"
                      type="button"
                      :disabled="Boolean(archivedAction)"
                      @click="removeArchivedPlan(item)"
                    >
                      <i class="fa-solid fa-trash-can me-1" aria-hidden="true"></i>
                      {{ archivedAction === archivedActionKey(item, 'remove')
                        ? 'Удаляем…'
                        : 'Удалить из плана' }}
                    </button>
                  </div>
                  <RouterLink
                    v-else
                    class="btn btn-sm btn-outline-primary mt-auto stretched-link"
                    :to="{ name: 'olympiad', params: { slug: item.olympiad.slug } }"
                  >
                    Открыть олимпиаду
                  </RouterLink>
                </div>
              </article>
            </div>
          </div>
          <div v-else class="empty-state rounded-4 p-4 text-center">
            <span class="empty-state-icon mb-3" aria-hidden="true">
              <i class="fa-solid fa-calendar-plus"></i>
            </span>
            <h3 class="h5">План пока пуст</h3>
            <p class="text-body-secondary">Выберите олимпиаду в каталоге и добавьте её в свой план.</p>
            <RouterLink class="btn btn-primary" to="/">Перейти в каталог</RouterLink>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>
