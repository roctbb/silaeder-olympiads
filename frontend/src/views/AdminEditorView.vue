<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import AdminBenefitsEditor from '../admin/AdminBenefitsEditor.vue'
import AdminMaterialsEditor from '../admin/AdminMaterialsEditor.vue'
import AdminSourcesEditor from '../admin/AdminSourcesEditor.vue'
import AdminStagesEditor from '../admin/AdminStagesEditor.vue'
import {
  emptyOlympiad,
  gradeOptions,
  olympiadFromApi,
  payloadFromForm,
  slugify,
} from '../admin/formDefaults'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import {
  createAdminOlympiad,
  getAdminOlympiads,
  updateAdminOlympiad,
} from '../services/api'

const props = defineProps({
  slug: { type: String, default: '' },
})
const router = useRouter()
const formElement = ref(null)
const form = reactive(emptyOlympiad())
const originalSlug = ref(props.slug)
const loading = ref(Boolean(props.slug))
const saving = ref(false)
const error = ref('')
const conflict = ref(false)
const savedMessage = ref('')
const missing = ref(false)
const initialized = ref(false)
const baseline = ref('')

const isNew = computed(() => !originalSlug.value)
const pageTitle = computed(() => (isNew.value ? 'Новая олимпиада' : 'Редактирование'))
const dirty = computed(() => initialized.value && JSON.stringify(form) !== baseline.value)

function setBaseline() {
  baseline.value = JSON.stringify(form)
  initialized.value = true
}

function generateSlug() {
  const base = [form.family_name || form.name, form.profile].filter(Boolean).join('-')
  form.slug = slugify(base)
}

function toggleGrade(grade, checked) {
  if (checked && !form.grades.includes(grade)) form.grades.push(grade)
  if (!checked) form.grades = form.grades.filter((item) => item !== grade)
}

async function load() {
  if (!props.slug) {
    await nextTick()
    setBaseline()
    return
  }
  loading.value = true
  error.value = ''
  conflict.value = false
  try {
    const result = await getAdminOlympiads()
    const item = result.items.find((candidate) => candidate.slug === props.slug)
    if (!item) {
      missing.value = true
      return
    }
    Object.assign(form, olympiadFromApi(item))
    originalSlug.value = item.slug
    await nextTick()
    setBaseline()
  } catch (caught) {
    if (caught.status === 401) {
      await router.replace({
        name: 'admin-login',
        query: { redirect: '/admin/olympiads/' + encodeURIComponent(props.slug) },
      })
      return
    }
    error.value = caught.message || 'Не удалось загрузить запись.'
  } finally {
    loading.value = false
  }
}

function validateStageDates() {
  for (const [index, stage] of form.stages.entries()) {
    const number = index + 1
    if (stage.starts_on && stage.ends_on && stage.ends_on < stage.starts_on) {
      error.value = 'Этап ' + number + ': дата окончания не может быть раньше даты начала.'
      document.getElementById('stage-end-' + index)?.focus()
      return false
    }
    if (
      stage.registration_opens_on &&
      stage.registration_closes_on &&
      stage.registration_closes_on < stage.registration_opens_on
    ) {
      error.value =
        'Этап ' + number + ': регистрация не может закрыться раньше, чем откроется.'
      document.getElementById('reg-close-' + index)?.focus()
      return false
    }
    if (
      stage.is_date_confirmed &&
      (stage.date_precision === 'tba' || (!stage.starts_on && !stage.ends_on))
    ) {
      error.value =
        'Этап ' + number + ': для подтверждённой даты укажите дату и её точность.'
      document.getElementById('stage-start-' + index)?.focus()
      return false
    }
  }
  return true
}

async function save() {
  savedMessage.value = ''
  error.value = ''
  conflict.value = false
  if (!validateStageDates()) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  if (!formElement.value.checkValidity()) {
    formElement.value.classList.add('was-validated')
    formElement.value.querySelector(':invalid')?.focus()
    return
  }

  saving.value = true
  try {
    const payload = payloadFromForm(form)
    const result = isNew.value
      ? await createAdminOlympiad(payload)
      : await updateAdminOlympiad(originalSlug.value, payload)

    Object.assign(form, olympiadFromApi(result))
    originalSlug.value = result.slug
    formElement.value.classList.remove('was-validated')
    await nextTick()
    setBaseline()
    savedMessage.value = 'Изменения сохранены.'
    if (props.slug !== result.slug) {
      await router.replace({ name: 'admin-edit', params: { slug: result.slug } })
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (caught) {
    if (caught.status === 401) {
      await router.replace({ name: 'admin-login', query: { redirect: router.currentRoute.value.fullPath } })
      return
    }
    if (caught.status === 409) {
      conflict.value = true
      error.value =
        'Карточку уже изменил другой редактор. Обновите её с сервера и внесите изменения заново.'
    } else {
      error.value = caught.message || 'Не удалось сохранить запись.'
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    saving.value = false
  }
}

watch(
  () => form.registry_status,
  (status) => {
    form.is_in_registry = status !== 'not_listed'
    if (status === 'not_listed') form.registry_level = ''
  },
)

onBeforeRouteLeave(() => {
  if (!dirty.value) return true
  return window.confirm('Есть несохранённые изменения. Покинуть страницу?')
})

onMounted(load)
</script>

<template>
  <div class="container py-4 py-lg-5 admin-editor">
    <nav aria-label="Хлебные крошки" class="mb-4">
      <ol class="breadcrumb">
        <li class="breadcrumb-item"><RouterLink :to="{ name: 'admin' }">Администрирование</RouterLink></li>
        <li class="breadcrumb-item active" aria-current="page">{{ pageTitle }}</li>
      </ol>
    </nav>

    <LoadingState v-if="loading" />
    <div v-else-if="missing" class="empty-state rounded-4 p-5 text-center">
      <h1 class="h3">Запись не найдена</h1>
      <p class="text-body-secondary">Возможно, она была удалена другим редактором.</p>
      <RouterLink class="btn btn-primary" :to="{ name: 'admin' }">К списку</RouterLink>
    </div>

    <template v-else>
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3 mb-4">
        <div>
          <p class="eyebrow mb-1">2026/27 учебный год</p>
          <h1 class="h2 mb-1">{{ pageTitle }}</h1>
          <p class="text-body-secondary mb-0">
            {{ isNew ? 'Создайте профиль олимпиады.' : form.name }}
          </p>
        </div>
        <span v-if="dirty" class="badge text-bg-warning">Есть несохранённые изменения</span>
      </header>

      <ErrorAlert
        v-if="error"
        :message="error"
        :retryable="conflict"
        retry-label="Обновить карточку"
        @retry="load"
      />
      <div v-if="savedMessage" class="alert alert-success" role="status">{{ savedMessage }}</div>

      <form ref="formElement" @submit.prevent="save">
        <div class="vstack gap-4">
          <section class="admin-section card border-0 shadow-sm">
            <div class="card-body p-4">
              <h2 class="h4 mb-4">Основные сведения</h2>
              <div class="row g-3">
                <div class="col-md-8">
                  <label for="admin-name" class="form-label">Название профиля олимпиады *</label>
                  <input id="admin-name" v-model="form.name" class="form-control" required maxlength="255" />
                  <div class="form-text">Например: «Высшая проба — Математика».</div>
                </div>
                <div class="col-md-4">
                  <label for="admin-profile" class="form-label">Направление *</label>
                  <input id="admin-profile" v-model="form.profile" class="form-control" required maxlength="160" />
                </div>
                <div class="col-md-6">
                  <label for="admin-family" class="form-label">Семейство *</label>
                  <input id="admin-family" v-model="form.family_name" class="form-control" required maxlength="255" />
                  <div class="form-text">Общее название без профиля.</div>
                </div>
                <div class="col-md-6">
                  <label for="admin-slug" class="form-label">Slug *</label>
                  <div class="input-group">
                    <input
                      id="admin-slug"
                      v-model="form.slug"
                      class="form-control"
                      required
                      maxlength="180"
                      pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                      aria-describedby="slug-help"
                    />
                    <button type="button" class="btn btn-outline-secondary" @click="generateSlug">Создать</button>
                  </div>
                  <div id="slug-help" class="form-text">Латиница, цифры и дефисы.</div>
                </div>
                <div class="col-md-6">
                  <label for="admin-organizer" class="form-label">Организатор</label>
                  <input id="admin-organizer" v-model="form.organizer" class="form-control" maxlength="255" />
                </div>
                <div class="col-md-3">
                  <label for="admin-geography" class="form-label">География</label>
                  <select id="admin-geography" v-model="form.geography" class="form-select">
                    <option value="russia">Россия</option>
                    <option value="moscow">Москва</option>
                    <option value="russia_moscow">Россия и Москва</option>
                  </select>
                </div>
                <div class="col-md-3">
                  <label for="admin-year" class="form-label">Учебный год *</label>
                  <input
                    id="admin-year"
                    v-model="form.academic_year"
                    class="form-control"
                    required
                    readonly
                    aria-describedby="admin-year-help"
                  />
                  <div id="admin-year-help" class="form-text">MVP работает только с этим учебным годом.</div>
                </div>
                <div class="col-md-6">
                  <label for="admin-cycle-label" class="form-label">Календарный цикл</label>
                  <input
                    id="admin-cycle-label"
                    v-model="form.cycle_label"
                    class="form-control"
                    maxlength="120"
                    placeholder="Например: Календарный цикл 2026"
                    aria-describedby="admin-cycle-label-help"
                  />
                  <div id="admin-cycle-label-help" class="form-text">
                    Необязательная метка, если цикл соревнования не совпадает с учебным годом каталога.
                  </div>
                </div>
                <div class="col-12">
                  <label for="admin-description" class="form-label">Описание</label>
                  <textarea id="admin-description" v-model="form.description" class="form-control" rows="4"></textarea>
                </div>
                <div class="col-md-6">
                  <label for="admin-website" class="form-label">Официальный сайт *</label>
                  <input id="admin-website" v-model="form.website_url" class="form-control" type="url" required maxlength="1000" placeholder="https://…" />
                </div>
                <div class="col-md-6">
                  <label for="admin-registration" class="form-label">Страница регистрации</label>
                  <input id="admin-registration" v-model="form.registration_url" class="form-control" type="url" maxlength="1000" placeholder="https://…" :required="form.registration_status === 'open'" />
                </div>
                <div class="col-md-6">
                  <label for="admin-registration-status" class="form-label">Статус регистрации</label>
                  <select id="admin-registration-status" v-model="form.registration_status" class="form-select">
                    <option value="open">Открыта</option>
                    <option value="announced">Анонсирована</option>
                    <option value="not_open">Пока закрыта</option>
                    <option value="not_found">Не опубликована</option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label for="admin-registration-checked-on" class="form-label">Регистрация проверена</label>
                  <input
                    id="admin-registration-checked-on"
                    v-model="form.registration_checked_on"
                    class="form-control"
                    type="date"
                  />
                </div>
                <div class="col-md-6">
                  <label for="admin-registration-closes-at" class="form-label">Регистрация открыта до</label>
                  <input
                    id="admin-registration-closes-at"
                    v-model="form.registration_closes_at"
                    class="form-control"
                    type="text"
                    maxlength="40"
                    pattern="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})"
                    placeholder="2026-08-26T11:50:00+03:00"
                    aria-describedby="admin-registration-closes-at-help"
                  />
                  <div id="admin-registration-closes-at-help" class="form-text">
                    ISO 8601 с часовым поясом. После этого момента ссылка регистрации исчезнет.
                  </div>
                </div>
                <div class="col-12">
                  <label for="admin-logo" class="form-label">URL логотипа</label>
                  <input id="admin-logo" v-model="form.logo_url" class="form-control" type="url" maxlength="1000" placeholder="https://…" />
                  <div class="form-text">В текущем публичном интерфейсе логотипы не загружаются.</div>
                </div>
                <div class="col-12">
                  <div class="form-check form-check-inline">
                    <input id="admin-team" v-model="form.is_team" class="form-check-input" type="checkbox" />
                    <label for="admin-team" class="form-check-label">Командная олимпиада</label>
                  </div>
                  <div class="form-check form-check-inline">
                    <input id="admin-popular" v-model="form.is_popular" class="form-check-input" type="checkbox" />
                    <label for="admin-popular" class="form-check-label">Отметить популярной</label>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="admin-section card border-0 shadow-sm">
            <div class="card-body p-4">
              <h2 class="h4 mb-4">Публикация и достоверность</h2>
              <div class="row g-3">
                <div class="col-md-4">
                  <label for="admin-status" class="form-label">Статус публикации</label>
                  <select id="admin-status" v-model="form.status" class="form-select">
                    <option value="draft">Черновик</option>
                    <option value="published">Опубликовано</option>
                    <option value="archived">В архиве</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label for="admin-data-status" class="form-label">Статус данных</label>
                  <select id="admin-data-status" v-model="form.data_status" class="form-select">
                    <option value="confirmed">Подтверждены</option>
                    <option value="partial">Подтверждены частично</option>
                    <option value="previous_year_estimate">Ориентир прошлого года</option>
                    <option value="announcement_pending">Ожидается объявление</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label for="admin-previous-year" class="form-label">Год-ориентир</label>
                  <input id="admin-previous-year" v-model="form.previous_year_reference" class="form-control" maxlength="9" placeholder="2025/26" pattern="\d{4}/\d{2}" />
                </div>
                <div class="col-md-5">
                  <label for="admin-registry-status" class="form-label">Статус перечня</label>
                  <select id="admin-registry-status" v-model="form.registry_status" class="form-select">
                    <option value="not_listed">Не в перечне</option>
                    <option value="approved">В утверждённом перечне</option>
                    <option value="draft">В проекте перечня</option>
                    <option value="previous_year">Была в перечне прошлого года</option>
                  </select>
                </div>
                <div class="col-md-3">
                  <label for="admin-registry-level" class="form-label">Уровень</label>
                  <select
                    id="admin-registry-level"
                    v-model="form.registry_level"
                    class="form-select"
                    :disabled="form.registry_status === 'not_listed'"
                  >
                    <option value="">Уточняется</option>
                    <option :value="1">1</option>
                    <option :value="2">2</option>
                    <option :value="3">3</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <span class="form-label d-block">Классы</span>
                  <div class="d-flex flex-wrap gap-2">
                    <div v-for="grade in gradeOptions" :key="grade" class="form-check grade-check">
                      <input
                        :id="'grade-' + grade"
                        class="form-check-input"
                        type="checkbox"
                        :checked="form.grades.includes(grade)"
                        @change="toggleGrade(grade, $event.target.checked)"
                      />
                      <label :for="'grade-' + grade" class="form-check-label">{{ grade }}</label>
                    </div>
                  </div>
                  <div class="form-text">Можно оставить пустым, если классы ещё не объявлены.</div>
                </div>
                <div class="col-12">
                  <label for="admin-eligibility-notes" class="form-label">Кто может участвовать</label>
                  <textarea
                    id="admin-eligibility-notes"
                    v-model="form.eligibility_notes"
                    class="form-control"
                    rows="3"
                    maxlength="4000"
                    placeholder="Например: учащиеся образовательных организаций и студенты колледжей"
                  ></textarea>
                  <div class="form-text">
                    Используйте, если условия участия нельзя точно выразить номерами классов.
                  </div>
                </div>
                <div class="col-12">
                  <label for="admin-notes" class="form-label">Примечание редактора для читателя</label>
                  <textarea id="admin-notes" v-model="form.notes" class="form-control" rows="3"></textarea>
                </div>
              </div>
            </div>
          </section>

          <AdminStagesEditor v-model="form.stages" />
          <AdminMaterialsEditor v-model="form.materials" />
          <AdminBenefitsEditor v-model="form.benefits" />
          <AdminSourcesEditor v-model="form.sources" />

          <div class="save-bar card border-0 shadow-lg">
            <div class="card-body p-3 d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3">
              <p class="small text-body-secondary mb-0">
                <template v-if="form.status === 'published'">После сохранения запись видна в каталоге.</template>
                <template v-else>Запись не видна в публичном каталоге.</template>
              </p>
              <div class="d-flex gap-2">
                <RouterLink class="btn btn-outline-secondary" :to="{ name: 'admin' }">Отмена</RouterLink>
                <button type="submit" class="btn btn-primary px-4" :disabled="saving">
                  <i v-if="saving" class="fa-solid fa-spinner fa-spin me-2" aria-hidden="true"></i>
                  {{ saving ? 'Сохраняем…' : 'Сохранить' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </form>
    </template>
  </div>
</template>
