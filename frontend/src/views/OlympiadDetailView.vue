<script setup>
import { computed, ref, watch } from 'vue'
import DataStatusBadge from '../components/DataStatusBadge.vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import PlanPanel from '../components/PlanPanel.vue'
import StageTimeline from '../components/StageTimeline.vue'
import {
  addOlympiadToPlan,
  deleteStageProgress,
  getOlympiad,
  getOlympiadPlanning,
  removeOlympiadFromPlan,
  saveStageProgress,
  updateOlympiadPlan,
} from '../services/api'
import { useAuth } from '../services/auth'
import {
  LABELS,
  admissionYearLabel,
  benefitDisplayType,
  formatDate,
  gradesLabel,
  pluralize,
} from '../utils/format'

const props = defineProps({
  slug: { type: String, required: true },
})
const { state: auth, authenticated, refresh: refreshAuth, clear: clearAuth } = useAuth()
const olympiad = ref(null)
const loading = ref(true)
const error = ref('')
const planning = ref(null)
const planningLoading = ref(true)
const planningError = ref('')
const planningNotice = ref('')
const savingAction = ref('')
const savingStageId = ref(null)
let planningSequence = 0

const progressByStage = computed(() => Object.fromEntries(
  (planning.value?.plan?.stage_progress || []).map((item) => [item.stage_id, item]),
))

const hasProjectedStageDates = computed(() => (
  olympiad.value?.data_status === 'previous_year_estimate'
  && olympiad.value.stages?.some((stage) => (
    !stage.is_date_confirmed && (stage.starts_on || stage.ends_on)
  ))
))

const hasAdmissionInformation = computed(() => (
  olympiad.value?.benefits?.some((benefit) => benefit.benefit_type !== 'prize') || false
))

const hasActiveRegistration = computed(() => {
  if (!olympiad.value?.registration_url) return false
  if (!olympiad.value.registration_closes_at) return true

  const closesAt = Date.parse(olympiad.value.registration_closes_at)
  return Number.isFinite(closesAt) && Date.now() < closesAt
})

const effectiveRegistrationStatus = computed(() => {
  const status = olympiad.value?.registration_status
    || (olympiad.value?.registration_url ? 'open' : 'not_found')
  return status === 'open' && !hasActiveRegistration.value ? 'not_open' : status
})

const registrationBadgeClass = computed(() => ({
  open: 'text-bg-success',
  announced: 'text-bg-warning',
  not_open: 'text-bg-secondary',
  not_found: 'text-bg-light border text-body-secondary',
})[effectiveRegistrationStatus.value])

const updatedLabel = computed(() => {
  if (!olympiad.value?.updated_at) return ''
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(olympiad.value.updated_at))
})

async function load() {
  loading.value = true
  error.value = ''
  planning.value = null
  planningNotice.value = ''
  try {
    olympiad.value = await getOlympiad(props.slug)
  } catch (caught) {
    error.value = caught.status === 404 ? 'Олимпиада не найдена.' : caught.message
  } finally {
    loading.value = false
  }
  refreshAuth()
  loadPlanning()
}

async function loadPlanning() {
  const sequence = ++planningSequence
  planningLoading.value = true
  planningError.value = ''
  try {
    const result = await getOlympiadPlanning(props.slug)
    if (sequence === planningSequence) planning.value = result
  } catch (caught) {
    if (sequence !== planningSequence) return
    planning.value = {
      participant_count: olympiad.value?.participant_count || 0,
      public_participants: olympiad.value?.public_participants || [],
      plan: null,
    }
    planningError.value = caught.message || 'Не удалось загрузить данные плана.'
  } finally {
    if (sequence === planningSequence) planningLoading.value = false
  }
}

function handlePersonalError(caught) {
  if (caught.status === 401) {
    clearAuth()
    planningError.value = ''
    return
  }
  planningError.value = caught.message || 'Не удалось сохранить изменения.'
}

async function addToPlan() {
  savingAction.value = 'add'
  planningError.value = ''
  planningNotice.value = ''
  try {
    await addOlympiadToPlan(props.slug, {
      status: 'planned',
      is_name_public: false,
      reminders_enabled: true,
      reminder_days_before: [7, 3, 1],
    }, auth.csrfToken)
    await loadPlanning()
    planningNotice.value = 'Олимпиада добавлена в ваш план.'
  } catch (caught) {
    handlePersonalError(caught)
  } finally {
    savingAction.value = ''
  }
}

async function savePlanSettings(payload) {
  savingAction.value = 'settings'
  planningError.value = ''
  planningNotice.value = ''
  try {
    await updateOlympiadPlan(props.slug, payload, auth.csrfToken)
    await loadPlanning()
    planningNotice.value = 'Настройки плана сохранены.'
  } catch (caught) {
    handlePersonalError(caught)
  } finally {
    savingAction.value = ''
  }
}

async function removeFromPlan() {
  if (!window.confirm('Убрать олимпиаду из вашего плана вместе с отметками этапов?')) return
  savingAction.value = 'remove'
  planningError.value = ''
  planningNotice.value = ''
  try {
    await removeOlympiadFromPlan(props.slug, auth.csrfToken)
    await loadPlanning()
    planningNotice.value = 'Олимпиада убрана из плана.'
  } catch (caught) {
    handlePersonalError(caught)
  } finally {
    savingAction.value = ''
  }
}

async function saveProgress(payload) {
  const { stage_id: stageId, ...body } = payload
  savingStageId.value = stageId
  planningError.value = ''
  planningNotice.value = ''
  try {
    const saved = await saveStageProgress(props.slug, stageId, body, auth.csrfToken)
    const current = planning.value?.plan?.stage_progress || []
    planning.value = {
      ...planning.value,
      plan: {
        ...planning.value.plan,
        stage_progress: [...current.filter((item) => String(item.stage_id) !== String(stageId)), saved],
      },
    }
  } catch (caught) {
    handlePersonalError(caught)
  } finally {
    savingStageId.value = null
  }
}

async function clearProgress(stageId) {
  savingStageId.value = stageId
  planningError.value = ''
  planningNotice.value = ''
  try {
    await deleteStageProgress(props.slug, stageId, auth.csrfToken)
    const current = planning.value?.plan?.stage_progress || []
    planning.value = {
      ...planning.value,
      plan: {
        ...planning.value.plan,
        stage_progress: current.filter((item) => String(item.stage_id) !== String(stageId)),
      },
    }
  } catch (caught) {
    handlePersonalError(caught)
  } finally {
    savingStageId.value = null
  }
}

watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <div class="container py-4 py-lg-5">
    <nav aria-label="Хлебные крошки" class="mb-4">
      <ol class="breadcrumb mb-0">
        <li class="breadcrumb-item"><RouterLink to="/">Каталог</RouterLink></li>
        <li class="breadcrumb-item active" aria-current="page">
          {{ olympiad?.family_name || 'Олимпиада' }}
        </li>
      </ol>
    </nav>

    <LoadingState v-if="loading" />
    <ErrorAlert v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="olympiad">
      <header class="detail-header rounded-4 p-4 p-lg-5 mb-5">
        <div class="row g-4 align-items-start">
          <div class="col-lg-8">
            <div class="d-flex flex-wrap gap-2 mb-3">
              <span v-if="olympiad.is_popular" class="badge badge-popular">Популярная</span>
              <span
                v-if="olympiad.registry_status && olympiad.registry_status !== 'not_listed'"
                class="badge"
                :class="olympiad.registry_status === 'approved' ? 'text-bg-primary' : 'badge-registry-pending'"
              >
                {{ LABELS.registryStatus[olympiad.registry_status] }}
                · {{ olympiad.registry_level ? olympiad.registry_level + ' уровень' : 'уровень уточняется' }}
              </span>
              <span v-if="olympiad.is_team" class="badge text-bg-info">Командная</span>
            </div>
            <p class="eyebrow mb-2">{{ olympiad.profile }}</p>
            <h1 class="display-6 fw-bold mb-3">{{ olympiad.name }}</h1>
            <p v-if="olympiad.description" class="lead text-body-secondary mb-4">
              {{ olympiad.description }}
            </p>
            <div class="d-flex flex-wrap gap-2">
              <a
                class="btn btn-primary"
                :href="hasActiveRegistration ? olympiad.registration_url : olympiad.website_url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ hasActiveRegistration ? 'Перейти к регистрации' : 'Официальный сайт' }}
                <i class="fa-solid fa-arrow-up-right-from-square external-link-icon" aria-hidden="true"></i>
              </a>
              <a
                v-if="hasActiveRegistration"
                class="btn btn-outline-secondary"
                :href="olympiad.website_url"
                target="_blank"
                rel="noopener noreferrer"
              >
                Официальный сайт
                <i class="fa-solid fa-arrow-up-right-from-square external-link-icon" aria-hidden="true"></i>
              </a>
            </div>
            <div class="d-flex flex-wrap align-items-center gap-2 mt-3" role="status">
              <span class="badge" :class="registrationBadgeClass">
                <i class="fa-solid fa-pen-to-square me-1" aria-hidden="true"></i>
                {{ LABELS.registrationStatus[effectiveRegistrationStatus] }}
              </span>
              <span v-if="olympiad.registration_checked_on" class="small text-body-secondary">
                Проверено {{ formatDate(olympiad.registration_checked_on, true) }}
              </span>
            </div>
          </div>
          <div class="col-lg-4">
            <dl class="detail-facts card border-0 mb-0">
              <div>
                <dt>{{ olympiad.grades?.length ? 'Классы' : olympiad.eligibility_notes ? 'Участники' : 'Классы' }}</dt>
                <dd>
                  {{ olympiad.grades?.length
                    ? gradesLabel(olympiad.grades)
                    : olympiad.eligibility_notes || gradesLabel(olympiad.grades) }}
                </dd>
              </div>
              <div>
                <dt>География</dt>
                <dd>{{ LABELS.geography[olympiad.geography] || olympiad.geography }}</dd>
              </div>
              <div v-if="olympiad.organizer">
                <dt>Организатор</dt>
                <dd>{{ olympiad.organizer }}</dd>
              </div>
              <div>
                <dt>Учебный год</dt>
                <dd>{{ olympiad.academic_year }}<span v-if="olympiad.cycle_label"> · {{ olympiad.cycle_label }}</span></dd>
              </div>
            </dl>
          </div>
        </div>
      </header>

      <div
        v-if="olympiad.data_status !== 'confirmed'"
        class="data-notice d-flex gap-3 align-items-start rounded-3 p-3 p-md-4 mb-5"
        role="note"
      >
        <i class="fa-solid fa-circle-info notice-icon" aria-hidden="true"></i>
        <div>
          <p class="fw-semibold mb-1">{{ LABELS.dataStatus[olympiad.data_status] }}</p>
          <p class="mb-0 text-body-secondary">
            <template
              v-if="olympiad.data_status === 'previous_year_estimate' && hasProjectedStageDates"
            >
              Показанные ориентировочные даты рассчитаны по расписанию
              {{ olympiad.previous_year_reference || 'прошлого года' }} и могут измениться
              после официального объявления.
            </template>
            <template v-else-if="olympiad.data_status === 'previous_year_estimate'">
              Расписание 2026/27 ещё не опубликовано. Структура этапов приведена по источникам
              {{ olympiad.previous_year_reference || 'прошлого года' }}; даты появятся после
              объявления организатора.
            </template>
            <template v-else>
              Часть сведений ещё уточняется. Для важных решений сверяйтесь с официальными источниками.
            </template>
          </p>
        </div>
      </div>

      <div class="row g-5 detail-content-row">
        <div class="col-lg-8">
          <section id="stages" class="mb-5" aria-labelledby="stages-title">
            <div class="section-heading">
              <div>
                <p class="eyebrow mb-1">Календарь</p>
                <h2 id="stages-title" class="h3 mb-0">Этапы</h2>
              </div>
              <span class="text-body-secondary small">
                {{ olympiad.stages.length }}
                {{ pluralize(olympiad.stages.length, 'этап', 'этапа', 'этапов') }}
              </span>
            </div>
            <StageTimeline
              :stages="olympiad.stages"
              :data-status="olympiad.data_status"
              :show-personal-progress="authenticated && Boolean(planning?.plan)"
              :progress-by-stage="progressByStage"
              :saving-stage-id="savingStageId"
              @save-progress="saveProgress"
              @clear-progress="clearProgress"
            />
          </section>

          <section id="materials" class="mb-5" aria-labelledby="materials-title">
            <div class="section-heading">
              <div>
                <p class="eyebrow mb-1">Подготовка</p>
                <h2 id="materials-title" class="h3 mb-0">Материалы прошлых лет</h2>
              </div>
            </div>
            <div v-if="olympiad.materials.length" class="list-group material-list shadow-sm">
              <a
                v-for="material in olympiad.materials"
                :key="material.id"
                class="list-group-item list-group-item-action d-flex gap-3 align-items-center p-3 p-md-4"
                :href="material.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span class="material-icon" aria-hidden="true">
                  <i class="fa-solid fa-arrow-up-right-from-square"></i>
                </span>
                <span class="flex-grow-1">
                  <span class="d-block fw-semibold">{{ material.title }}</span>
                  <span class="small text-body-secondary">
                    {{ LABELS.materialType[material.material_type] || 'Материал' }}
                    <template v-if="material.year"> · {{ material.year }}</template>
                    <template v-if="material.is_official"> · официальный</template>
                  </span>
                </span>
                <span class="visually-hidden">Открыть в новой вкладке</span>
              </a>
            </div>
            <div v-else class="empty-state rounded-4 p-4">
              <p class="mb-0 text-body-secondary d-flex align-items-center gap-2">
                <i class="fa-solid fa-folder-open empty-inline-icon" aria-hidden="true"></i>
                Ссылки на материалы пока не добавлены.
              </p>
            </div>
          </section>

          <section id="benefits" class="mb-5" aria-labelledby="benefits-title">
            <div class="section-heading">
              <div>
                <p class="eyebrow mb-1">Поступление и награды</p>
                <h2 id="benefits-title" class="h3 mb-0">Льготы и награды</h2>
              </div>
            </div>
            <div v-if="olympiad.benefits.length" class="vstack gap-3">
              <article v-for="benefit in olympiad.benefits" :key="benefit.id" class="card border-0 shadow-sm">
                <div class="card-body p-4">
                  <div class="d-flex flex-wrap align-items-start justify-content-between gap-2">
                    <div>
                      <span
                        class="badge mb-2"
                        :class="benefit.benefit_type === 'other' ? 'text-bg-secondary' : 'text-bg-success'"
                      >
                        {{ benefitDisplayType(benefit) || 'Условие' }}
                      </span>
                      <h3 class="h5 mb-1">{{ benefit.title }}</h3>
                      <p v-if="benefit.university" class="text-body-secondary mb-0">
                        {{ benefit.university.name }}
                      </p>
                    </div>
                    <span v-if="admissionYearLabel(benefit)" class="small text-body-secondary">
                      {{ admissionYearLabel(benefit) }}
                    </span>
                  </div>
                  <p v-if="benefit.description" class="mt-3 mb-0">{{ benefit.description }}</p>
                  <dl class="compact-facts compact-facts-grid mt-3 mb-0">
                    <div v-if="benefit.diploma_requirement">
                      <dt>Условие</dt>
                      <dd>{{ benefit.diploma_requirement }}</dd>
                    </div>
                    <div v-if="benefit.ege_subject">
                      <dt>Подтверждение ЕГЭ</dt>
                      <dd>
                        {{ benefit.ege_subject }}
                        <template v-if="benefit.ege_min_score"> — от {{ benefit.ege_min_score }} баллов</template>
                      </dd>
                    </div>
                  </dl>
                  <a
                    v-if="benefit.source_url"
                    class="source-link d-inline-flex mt-3"
                    :href="benefit.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Проверить условия
                    <i class="fa-solid fa-arrow-up-right-from-square external-link-icon" aria-hidden="true"></i>
                  </a>
                </div>
              </article>
              <p v-if="hasAdmissionInformation" class="small text-body-secondary mb-0">
                Условия поступления устанавливают вузы. Перед подачей документов проверьте правила приёма нужного года.
              </p>
            </div>
            <div v-else class="empty-state rounded-4 p-4">
              <p class="mb-0 text-body-secondary d-flex align-items-center gap-2">
                <i class="fa-solid fa-gift empty-inline-icon" aria-hidden="true"></i>
                Льготы или призы для этого профиля не указаны.
              </p>
            </div>
          </section>
        </div>

        <aside class="col-lg-4">
          <div class="sticky-aside">
            <PlanPanel
              :authenticated="authenticated"
              :loading="planningLoading"
              :planning="planning"
              :error="planningError"
              :notice="planningNotice"
              :saving-action="savingAction"
              @add="addToPlan"
              @remove="removeFromPlan"
              @save-settings="savePlanSettings"
              @retry="loadPlanning"
            />
            <section class="card border-0 shadow-sm mb-4" aria-labelledby="sources-title">
              <div class="card-body p-4">
                <h2 id="sources-title" class="h5 mb-3">Источники</h2>
                <ul v-if="olympiad.sources.length" class="source-list list-unstyled mb-0">
                  <li v-for="source in olympiad.sources" :key="source.id">
                    <a :href="source.url" target="_blank" rel="noopener noreferrer">
                      {{ source.title }}
                      <i class="fa-solid fa-arrow-up-right-from-square external-link-icon" aria-hidden="true"></i>
                    </a>
                    <small v-if="source.publisher || source.source_year" class="d-block text-body-secondary">
                      {{ [source.publisher, source.source_year].filter(Boolean).join(' · ') }}
                    </small>
                    <small v-if="source.accessed_on" class="d-block text-body-secondary">
                      Проверено {{ formatDate(source.accessed_on, true) }}
                    </small>
                  </li>
                </ul>
                <p v-else class="text-body-secondary mb-0 d-flex align-items-center gap-2">
                  <i class="fa-solid fa-link-slash empty-inline-icon" aria-hidden="true"></i>
                  Источники пока не добавлены.
                </p>
              </div>
            </section>

            <section v-if="olympiad.notes" class="card border-0 shadow-sm mb-4" aria-labelledby="notes-title">
              <div class="card-body p-4">
                <h2 id="notes-title" class="h5">Важно</h2>
                <p class="mb-0 text-body-secondary">{{ olympiad.notes }}</p>
              </div>
            </section>

            <p v-if="updatedLabel" class="small text-body-secondary">
              Данные обновлены {{ updatedLabel }}
            </p>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>
