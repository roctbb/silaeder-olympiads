<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppPagination from '../components/AppPagination.vue'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import OlympiadCalendar from '../components/OlympiadCalendar.vue'
import OlympiadCard from '../components/OlympiadCard.vue'
import {
  addOlympiadToPlan,
  getCalendarEvents,
  getMetadata,
  getMyPlan,
  getOlympiads,
} from '../services/api'
import { useAuth } from '../services/auth'
import {
  groupCalendarEvents,
  isValidMonthKey,
  monthKeyFromDate,
  normalizeCalendarEvents,
  shiftMonthKey,
} from '../utils/calendar'
import { pluralize } from '../utils/format'

const ACADEMIC_YEAR = '2026/27'
const LEGACY_PROFILE_PREFIX = 'legacy-profile:'
const route = useRoute()
const router = useRouter()
const { state: auth, authenticated, refresh: refreshAuth, clear: clearAuth } = useAuth()

const filters = reactive({
  q: '',
  direction: '',
  profile: '',
  grade: '',
  registry_level: '',
  university: '',
})
const items = ref([])
const metadata = ref({
  academic_year: ACADEMIC_YEAR,
  profiles: [],
  grades: [5, 6, 7, 8, 9, 10, 11],
  registry_levels: [1, 2, 3],
  counts: { total: 0, popular: 0, registry: 0 },
})
const pagination = ref({ page: 1, per_page: 24, pages: 0, total: 0 })
const loading = ref(true)
const error = ref('')
const viewMode = ref('cards')
const calendarMonth = ref(monthKeyFromDate())
const calendarEvents = ref([])
const calendarTotal = ref(0)
const calendarLoading = ref(false)
const calendarError = ref('')
const plannedSlugs = ref(new Set())
const addingSlug = ref('')
const planActionError = ref('')
let requestSequence = 0
let calendarRequestSequence = 0
let previousCatalogKey = ''
let previousCalendarKey = ''

const supportsUniversityFilter = computed(
  () => Object.hasOwn(metadata.value, 'universities') && Array.isArray(metadata.value.universities),
)
const supportsDirectionFilter = computed(
  () => Object.hasOwn(metadata.value, 'categories') && Array.isArray(metadata.value.categories),
)
const directionOptions = computed(() => (
  supportsDirectionFilter.value
    ? metadata.value.categories.map((category) => ({
        value: category.slug,
        label: category.name,
        count: category.count,
      }))
    : metadata.value.profiles.map((profile) => ({
        value: profile,
        label: profile,
        count: null,
      }))
))
const legacyProfileOption = computed(
  () => `${LEGACY_PROFILE_PREFIX}${filters.profile}`,
)
const selectedDirection = computed({
  get: () => {
    if (!supportsDirectionFilter.value) return filters.profile
    if (filters.direction) return filters.direction
    return filters.profile ? legacyProfileOption.value : ''
  },
  set: (value) => {
    if (supportsDirectionFilter.value) {
      if (value === legacyProfileOption.value && filters.profile) return
      filters.direction = value
      filters.profile = ''
    } else {
      filters.profile = value
      filters.direction = ''
    }
  },
})
const filterSupportKey = computed(
  () => [
    supportsUniversityFilter.value,
    supportsDirectionFilter.value,
  ].join(':'),
)

const hasFilters = computed(() =>
  Object.values(filters).some((value) => value !== '' && value !== false),
)

function syncFiltersFromRoute() {
  filters.q = typeof route.query.q === 'string' ? route.query.q : ''
  filters.direction = typeof route.query.direction === 'string' ? route.query.direction : ''
  filters.profile = typeof route.query.profile === 'string' ? route.query.profile : ''
  filters.grade = typeof route.query.grade === 'string' ? route.query.grade : ''
  filters.registry_level =
    typeof route.query.registry_level === 'string' ? route.query.registry_level : ''
  filters.university =
    typeof route.query.university === 'string' ? route.query.university : ''
}

function syncViewFromRoute() {
  viewMode.value = route.query.view === 'calendar' ? 'calendar' : 'cards'
  calendarMonth.value = isValidMonthKey(route.query.month)
    ? route.query.month
    : monthKeyFromDate()
}

function filterQueryParams() {
  const query = { academic_year: ACADEMIC_YEAR }
  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value !== false) query[key] = String(value)
  }
  return query
}

function apiParams() {
  const query = { ...filterQueryParams(), registration_available: 'true' }
  if (!supportsDirectionFilter.value) delete query.direction
  else if (query.direction) delete query.profile
  if (!supportsUniversityFilter.value) delete query.university
  return query
}

function queryFor(page = 1, mode = viewMode.value, month = calendarMonth.value) {
  const query = filterQueryParams()
  if (mode === 'calendar') {
    query.view = 'calendar'
    query.month = month
  } else if (page > 1) {
    query.page = String(page)
  }
  return query
}

async function loadCatalog() {
  const sequence = ++requestSequence
  loading.value = true
  error.value = ''
  try {
    const result = await getOlympiads({
      ...apiParams(),
      page: Number(route.query.page) || 1,
      per_page: 18,
    })
    if (sequence !== requestSequence) return
    items.value = result.items
    pagination.value = result.pagination
  } catch (caught) {
    if (sequence !== requestSequence) return
    error.value = caught.message || 'Не удалось загрузить каталог.'
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

async function loadCalendar() {
  const sequence = ++calendarRequestSequence
  calendarLoading.value = true
  calendarError.value = ''
  try {
    const result = await getCalendarEvents({
      ...apiParams(),
      month: calendarMonth.value,
    })
    if (sequence !== calendarRequestSequence) return
    calendarEvents.value = groupCalendarEvents(normalizeCalendarEvents(result.events || []))
    calendarTotal.value = Number(result.total ?? result.events?.length ?? 0)
  } catch (caught) {
    if (sequence !== calendarRequestSequence) return
    calendarError.value = caught.message || 'Не удалось загрузить календарь.'
  } finally {
    if (sequence === calendarRequestSequence) calendarLoading.value = false
  }
}

async function loadMetadata() {
  try {
    metadata.value = await getMetadata(ACADEMIC_YEAR, { registration_available: 'true' })
  } catch {
    // Каталог остаётся работоспособным с базовыми значениями фильтров.
  }
}

async function loadPlanMembership() {
  if (!authenticated.value) {
    plannedSlugs.value = new Set()
    return
  }
  try {
    const result = await getMyPlan(ACADEMIC_YEAR)
    plannedSlugs.value = new Set(
      (result.items || []).map((item) => item.olympiad?.slug).filter(Boolean),
    )
  } catch (caught) {
    if (caught.status === 401) clearAuth()
  }
}

function isInPlan(slug) {
  return plannedSlugs.value.has(slug)
}

async function addFromCard(olympiad) {
  if (!authenticated.value || addingSlug.value || isInPlan(olympiad.slug)) return
  addingSlug.value = olympiad.slug
  planActionError.value = ''
  try {
    await addOlympiadToPlan(olympiad.slug, {
      status: 'planned',
      is_name_public: true,
      reminders_enabled: true,
      reminder_days_before: [7, 3, 1],
    }, auth.csrfToken, ACADEMIC_YEAR)
    plannedSlugs.value = new Set([...plannedSlugs.value, olympiad.slug])
    items.value = items.value.map((item) => (
      item.slug === olympiad.slug
        ? { ...item, participant_count: Number(item.participant_count || 0) + 1 }
        : item
    ))
  } catch (caught) {
    if (caught.status === 401) {
      clearAuth()
    } else if (caught.status === 409) {
      plannedSlugs.value = new Set([...plannedSlugs.value, olympiad.slug])
    } else {
      planActionError.value = caught.message || 'Не удалось добавить олимпиаду в план.'
    }
  } finally {
    addingSlug.value = ''
  }
}

function applyFilters() {
  router.push({ name: 'catalog', query: queryFor(1) })
}

function clearFilters() {
  Object.assign(filters, {
    q: '',
    direction: '',
    profile: '',
    grade: '',
    registry_level: '',
    university: '',
  })
  router.push({ name: 'catalog', query: queryFor(1) })
}

function changePage(page) {
  if (page < 1 || page > pagination.value.pages || page === pagination.value.page) return
  router.push({ name: 'catalog', query: queryFor(page) })
}

function setView(mode) {
  if (mode === viewMode.value) return
  router.push({
    name: 'catalog',
    query: queryFor(1, mode, calendarMonth.value),
  })
}

function setCalendarMonth(month) {
  router.push({
    name: 'catalog',
    query: queryFor(1, 'calendar', month),
  })
}

function moveCalendar(amount) {
  setCalendarMonth(shiftMonthKey(calendarMonth.value, amount))
}

function moveCalendarToToday() {
  setCalendarMonth(monthKeyFromDate())
}

watch(
  [() => route.query, filterSupportKey],
  () => {
    syncFiltersFromRoute()
    syncViewFromRoute()

    const catalogKey = viewMode.value === 'cards'
      ? JSON.stringify({
          ...apiParams(),
          page: Number(route.query.page) || 1,
        })
      : ''
    if (catalogKey && catalogKey !== previousCatalogKey) {
      previousCatalogKey = catalogKey
      loadCatalog()
    }

    const calendarKey = viewMode.value === 'calendar'
      ? JSON.stringify({ ...apiParams(), month: calendarMonth.value })
      : ''
    if (calendarKey && calendarKey !== previousCalendarKey) {
      previousCalendarKey = calendarKey
      loadCalendar()
    }
  },
  { immediate: true },
)

watch(
  () => [auth.initialized, authenticated.value],
  ([initialized]) => {
    if (initialized) loadPlanMembership()
  },
  { immediate: true },
)

onMounted(() => {
  loadMetadata()
  refreshAuth()
})
</script>

<template>
  <section class="catalog-hero">
    <div class="container py-5 py-lg-6">
      <div class="row align-items-end g-4">
        <div class="col-lg-8">
          <p class="eyebrow mb-2">2026/27 учебный год</p>
          <h1 class="display-5 fw-bold mb-3">Найдите свою олимпиаду</h1>
          <p class="lead text-body-secondary mb-0">
            Олимпиады для школьников 5–11 классов, участие в которых ещё не завершено.
          </p>
        </div>
        <div class="col-lg-4">
          <div class="hero-stat-grid" aria-label="Статистика каталога">
            <div>
              <strong>{{ metadata.counts.total }}</strong>
              <span>{{ pluralize(metadata.counts.total, 'профиль', 'профиля', 'профилей') }}</span>
            </div>
            <div>
              <strong>{{ metadata.counts.registry }}</strong>
              <span>связаны с перечнем</span>
            </div>
            <div>
              <strong>{{ metadata.counts.popular }}</strong>
              <span>{{ pluralize(metadata.counts.popular, 'популярная', 'популярные', 'популярных') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="container py-4 py-lg-5" aria-labelledby="catalog-title">
    <form class="filter-panel card border-0 shadow-sm mb-5" role="search" @submit.prevent="applyFilters">
      <div class="card-body p-3 p-lg-4">
        <div class="row g-3 align-items-end">
          <div class="col-xl-3">
            <label for="catalog-search" class="form-label fw-semibold">Поиск</label>
            <div class="input-group">
              <span class="input-group-text" aria-hidden="true">
                <i class="fa-solid fa-magnifying-glass input-icon"></i>
              </span>
              <input
                id="catalog-search"
                v-model.trim="filters.q"
                class="form-control"
                type="search"
                placeholder="Название, профиль, организатор"
              />
            </div>
          </div>
          <div class="col-md-6 col-xl-3">
            <label for="direction-filter" class="form-label fw-semibold">Направление</label>
            <select
              id="direction-filter"
              v-model="selectedDirection"
              class="form-select"
              @change="applyFilters"
            >
              <option value="">Все направления</option>
              <option
                v-if="supportsDirectionFilter && filters.profile && !filters.direction"
                :value="legacyProfileOption"
              >
                Точный профиль: {{ filters.profile }}
              </option>
              <option
                v-for="option in directionOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}{{ option.count == null ? '' : ` · ${option.count}` }}
              </option>
            </select>
          </div>
          <div class="col-6 col-md-3 col-xl-1">
            <label for="grade-filter" class="form-label fw-semibold">Класс</label>
            <select id="grade-filter" v-model="filters.grade" class="form-select" @change="applyFilters">
              <option value="">Любой</option>
              <option v-for="grade in metadata.grades" :key="grade" :value="String(grade)">
                {{ grade }}
              </option>
            </select>
          </div>
          <div class="col-6 col-md-3 col-xl-1">
            <label for="level-filter" class="form-label fw-semibold">Уровень</label>
            <select
              id="level-filter"
              v-model="filters.registry_level"
              class="form-select"
              @change="applyFilters"
            >
              <option value="">Любой</option>
              <option v-for="level in metadata.registry_levels" :key="level" :value="String(level)">
                {{ level }}
              </option>
            </select>
          </div>
          <div v-if="supportsUniversityFilter" class="col-md-6 col-xl-3">
            <label for="university-filter" class="form-label fw-semibold">Льготы в вузе</label>
            <select
              id="university-filter"
              v-model="filters.university"
              class="form-select"
              @change="applyFilters"
            >
              <option value="">Любой вуз</option>
              <option
                v-for="university in metadata.universities"
                :key="university.slug"
                :value="university.slug"
              >
                {{ university.short_name || university.name }} · {{ university.count }}
              </option>
            </select>
          </div>
        </div>

        <div class="d-flex justify-content-end mt-4 pt-3 border-top">
          <div class="d-flex gap-2">
            <button v-if="hasFilters" type="button" class="btn btn-link text-decoration-none" @click="clearFilters">
              Сбросить
            </button>
            <button type="submit" class="btn btn-primary px-4">Найти</button>
          </div>
        </div>
      </div>
    </form>

    <div class="catalog-view-heading mb-4">
      <div>
        <h2 id="catalog-title" class="h3 mb-1">Каталог</h2>
        <p
          v-if="viewMode === 'cards' && !loading && !error"
          class="text-body-secondary mb-0"
          aria-live="polite"
        >
          Найдено: {{ pagination.total }}
        </p>
        <p
          v-else-if="viewMode === 'calendar' && !calendarLoading && !calendarError"
          class="text-body-secondary mb-0"
          aria-live="polite"
        >
          Событий в месяце: {{ calendarEvents.length }}
        </p>
      </div>
      <div class="btn-group catalog-view-switch" role="group" aria-label="Вид каталога">
        <button
          type="button"
          class="btn btn-outline-secondary"
          :class="{ active: viewMode === 'cards' }"
          :aria-pressed="viewMode === 'cards'"
          @click="setView('cards')"
        >
          <i class="fa-solid fa-table-cells-large me-1" aria-hidden="true"></i>
          Карточки
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :class="{ active: viewMode === 'calendar' }"
          :aria-pressed="viewMode === 'calendar'"
          @click="setView('calendar')"
        >
          <i class="fa-solid fa-calendar-days me-1" aria-hidden="true"></i>
          Календарь
        </button>
      </div>
    </div>

    <div
      v-if="filters.grade"
      class="alert alert-info d-flex align-items-start gap-2 py-2 px-3 mb-4"
      role="note"
    >
      <i class="fa-solid fa-circle-info mt-1" aria-hidden="true"></i>
      <span>
        Сначала показаны олимпиады, где {{ filters.grade }} класс входит в опубликованный
        или проверенный диапазон. Карточки без числового диапазона тоже сохранены:
        для них показаны условия участия организатора, а если их ещё нет —
        «Классы уточняются».
      </span>
    </div>

    <template v-if="viewMode === 'cards'">
      <div v-if="planActionError" class="alert alert-danger" role="alert">
        {{ planActionError }}
      </div>
      <LoadingState v-if="loading" />
      <ErrorAlert v-else-if="error" :message="error" @retry="loadCatalog" />
      <div v-else-if="items.length" class="row g-4">
        <div v-for="item in items" :key="item.edition_id" class="col-md-6 col-xl-4">
          <OlympiadCard
            :olympiad="item"
            :active-university="filters.university"
            :authenticated="authenticated"
            :in-plan="isInPlan(item.slug)"
            :adding-to-plan="addingSlug === item.slug"
            @add-to-plan="addFromCard(item)"
          />
        </div>
      </div>
      <div v-else class="empty-state text-center rounded-4 p-5">
        <div class="empty-state-icon" aria-hidden="true">
          <i class="fa-solid fa-filter-circle-xmark"></i>
        </div>
        <h3 class="h5 mt-3">Ничего не найдено</h3>
        <p class="text-body-secondary">Попробуйте убрать часть фильтров или изменить запрос.</p>
        <button type="button" class="btn btn-outline-primary" @click="clearFilters">Сбросить фильтры</button>
      </div>

      <div v-if="!loading && !error" class="mt-5">
        <AppPagination
          :page="pagination.page"
          :pages="pagination.pages"
          @change="changePage"
        />
      </div>
    </template>

    <OlympiadCalendar
      v-else
      :month="calendarMonth"
      :events="calendarEvents"
      :source-total="calendarTotal"
      :loading="calendarLoading"
      :error="calendarError"
      @previous="moveCalendar(-1)"
      @today="moveCalendarToToday"
      @next="moveCalendar(1)"
      @retry="loadCalendar"
    />
  </section>
</template>
