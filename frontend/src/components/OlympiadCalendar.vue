<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import ErrorAlert from './ErrorAlert.vue'
import LoadingState from './LoadingState.vue'
import {
  buildMonthDays,
  eventsOverlappingMonth,
  formatMonthLabel,
} from '../utils/calendar'
import { formatDate, formatDateRange, pluralize } from '../utils/format'

const props = defineProps({
  month: { type: String, required: true },
  events: { type: Array, default: () => [] },
  sourceTotal: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['previous', 'today', 'next', 'retry'])

const MAX_EVENTS_PER_DAY = 4
const weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const days = computed(() => buildMonthDays(props.month, props.events))
const monthEvents = computed(() => eventsOverlappingMonth(props.month, props.events))
const selectedEventId = ref('')
const selectionPanel = ref(null)
let selectionTrigger = null

const selectedEvent = computed(() =>
  monthEvents.value.find((event) => event.id === selectedEventId.value) || null,
)

function eventRoute(event, profile = null) {
  return {
    name: 'olympiad',
    params: { slug: profile?.slug || event.olympiadSlug },
  }
}

function confidenceLabel(event) {
  if (event.previousYearEstimate) return 'Ориентир прошлого года'
  if (event.displayStatus !== 'confirmed') return 'Ориентировочно'
  if (event.isDeadline) return 'Подтверждённый крайний срок'
  if (event.isRange) {
    return 'Подтверждённый диапазон'
  }
  return 'Точная дата'
}

function profileLabel(profile) {
  return profile.profile || profile.name
}

function profileSummary(event) {
  const labels = event.profiles.slice(0, 2).map(profileLabel)
  const hidden = event.profiles.length - labels.length
  return labels.join(', ') + (hidden > 0 ? ` · ещё ${hidden}` : '')
}

function eventDateLabel(event, short = false) {
  return formatDateRange(event.isDeadline ? null : event.startsOn, event.endsOn, short)
}

function accessibleEventLabel(event) {
  return [
    event.olympiadName,
    event.cycleLabel,
    event.stageName,
    profileSummary(event),
    eventDateLabel(event),
    confidenceLabel(event),
  ].filter(Boolean).join('. ')
}

function hasProfileChoice(event) {
  return event.profiles.length > 1
}

function profileChoiceLabel(event) {
  const count = event.profiles.length
  return `${accessibleEventLabel(event)}. Открыть список: ${count} ${pluralize(count, 'направление', 'направления', 'направлений')}`
}

async function closeProfileChoice(trigger = selectionTrigger) {
  selectedEventId.value = ''
  selectionTrigger = null
  await nextTick()
  trigger?.focus?.()
}

async function toggleProfileChoice(event, domEvent) {
  if (selectedEventId.value === event.id) {
    await closeProfileChoice(domEvent?.currentTarget)
    return
  }

  selectedEventId.value = event.id
  selectionTrigger = domEvent?.currentTarget || null
  await nextTick()
  selectionPanel.value?.scrollIntoView?.({ block: 'nearest' })
  selectionPanel.value?.focus({ preventScroll: true })
}

watch([() => props.month, () => props.events], () => {
  selectedEventId.value = ''
  selectionTrigger = null
})
</script>

<template>
  <section class="calendar-panel card border-0 shadow-sm" aria-labelledby="calendar-month-title">
    <div class="card-body p-3 p-lg-4">
      <header class="calendar-toolbar">
        <div>
          <p class="eyebrow mb-1">Расписание этапов</p>
          <h3 id="calendar-month-title" class="h4 mb-0">{{ formatMonthLabel(month) }}</h3>
        </div>
        <div class="btn-group calendar-navigation" role="group" aria-label="Навигация по месяцам">
          <button type="button" class="btn btn-outline-secondary" aria-label="Предыдущий месяц" @click="$emit('previous')">
            <i class="fa-solid fa-chevron-left" aria-hidden="true"></i>
          </button>
          <button type="button" class="btn btn-outline-secondary" @click="$emit('today')">
            <i class="fa-solid fa-calendar-day me-1" aria-hidden="true"></i>
            Сегодня
          </button>
          <button type="button" class="btn btn-outline-secondary" aria-label="Следующий месяц" @click="$emit('next')">
            <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
          </button>
        </div>
      </header>

      <div class="calendar-legend" aria-label="Обозначения дат">
        <span class="calendar-legend-confirmed">
          <i class="fa-solid fa-circle-check" aria-hidden="true"></i>
          Подтверждённая дата или диапазон
        </span>
        <span class="calendar-legend-estimate">
          <i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>
          Ориентировочно
        </span>
        <span class="calendar-legend-previous">
          <i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>
          Ориентир прошлого года
        </span>
      </div>

      <LoadingState v-if="loading" />
      <ErrorAlert v-else-if="error" :message="error" @retry="$emit('retry')" />

      <template v-else-if="monthEvents.length">
        <div class="calendar-desktop d-none d-md-block">
          <div class="calendar-weekdays" role="row">
            <div v-for="weekday in weekdays" :key="weekday" role="columnheader">{{ weekday }}</div>
          </div>
          <div class="calendar-grid" role="grid" :aria-label="`Календарь на ${formatMonthLabel(month)}`">
            <section
              v-for="day in days"
              :key="day.date"
              class="calendar-day"
              :class="{
                'calendar-day-outside': !day.inMonth,
                'calendar-day-today': day.isToday,
              }"
              role="gridcell"
              :aria-label="formatDate(day.date)"
            >
              <time :datetime="day.date" class="calendar-day-number">{{ day.dayNumber }}</time>
              <div class="calendar-day-events">
                <template
                  v-for="event in day.events.slice(0, MAX_EVENTS_PER_DAY)"
                  :key="event.id"
                >
                  <button
                    v-if="hasProfileChoice(event)"
                    type="button"
                    class="calendar-event"
                    :class="[
                      `calendar-event-${event.displayStatus}`,
                      {
                        'calendar-event-previous-year': event.previousYearEstimate,
                        'calendar-event-segment-start': event.segmentStarts,
                        'calendar-event-segment-end': event.segmentEnds,
                        'calendar-event-selected': selectedEvent?.id === event.id,
                      },
                    ]"
                    :aria-label="profileChoiceLabel(event)"
                    :aria-expanded="selectedEvent?.id === event.id"
                    aria-controls="calendar-profile-choice"
                    :title="profileChoiceLabel(event)"
                    @click="toggleProfileChoice(event, $event)"
                  >
                    <template v-if="event.showLabel">
                      <span class="calendar-event-title">
                        <i
                          class="fa-solid"
                          :class="event.displayStatus === 'confirmed' ? 'fa-circle-check' : 'fa-clock-rotate-left'"
                          aria-hidden="true"
                        ></i>
                        {{ event.olympiadName }}
                      </span>
                      <span class="calendar-event-meta">{{ event.stageName }}</span>
                      <span v-if="event.cycleLabel" class="calendar-event-flag">
                        {{ event.cycleLabel }}
                      </span>
                      <span class="calendar-event-profiles">
                        {{ profileSummary(event) }}
                      </span>
                      <span v-if="event.previousYearEstimate" class="calendar-event-flag">
                        Ориентир прошлого года
                      </span>
                    </template>
                    <span v-else class="visually-hidden">{{ profileChoiceLabel(event) }}</span>
                  </button>

                  <RouterLink
                    v-else
                    :to="eventRoute(event)"
                    class="calendar-event"
                    :class="[
                      `calendar-event-${event.displayStatus}`,
                      {
                        'calendar-event-previous-year': event.previousYearEstimate,
                        'calendar-event-segment-start': event.segmentStarts,
                        'calendar-event-segment-end': event.segmentEnds,
                      },
                    ]"
                    :aria-label="accessibleEventLabel(event)"
                    :title="accessibleEventLabel(event)"
                  >
                    <template v-if="event.showLabel">
                      <span class="calendar-event-title">
                        <i
                          class="fa-solid"
                          :class="event.displayStatus === 'confirmed' ? 'fa-circle-check' : 'fa-clock-rotate-left'"
                          aria-hidden="true"
                        ></i>
                        {{ event.olympiadName }}
                      </span>
                      <span class="calendar-event-meta">{{ event.stageName }}</span>
                      <span v-if="event.cycleLabel" class="calendar-event-flag">
                        {{ event.cycleLabel }}
                      </span>
                      <span v-if="event.profiles.length" class="calendar-event-profiles">
                        {{ profileSummary(event) }}
                      </span>
                      <span v-if="event.previousYearEstimate" class="calendar-event-flag">
                        Ориентир прошлого года
                      </span>
                    </template>
                    <span v-else class="visually-hidden">{{ accessibleEventLabel(event) }}</span>
                  </RouterLink>
                </template>

                <details v-if="day.events.length > MAX_EVENTS_PER_DAY" class="calendar-more">
                  <summary>Ещё {{ day.events.length - MAX_EVENTS_PER_DAY }}</summary>
                  <div class="calendar-more-list">
                    <template
                      v-for="event in day.events.slice(MAX_EVENTS_PER_DAY)"
                      :key="event.id"
                    >
                      <button
                        v-if="hasProfileChoice(event)"
                        type="button"
                        class="calendar-more-event"
                        :aria-expanded="selectedEvent?.id === event.id"
                        aria-controls="calendar-profile-choice"
                        @click="toggleProfileChoice(event, $event)"
                      >
                        {{ event.olympiadName }} — {{ event.stageName }} ·
                        {{ event.profiles.length }}
                        {{ pluralize(event.profiles.length, 'направление', 'направления', 'направлений') }}
                      </button>
                      <RouterLink v-else :to="eventRoute(event)">
                        {{ event.olympiadName }} — {{ event.stageName }}
                      </RouterLink>
                    </template>
                  </div>
                </details>
              </div>
            </section>
          </div>

          <section
            v-if="selectedEvent"
            id="calendar-profile-choice"
            ref="selectionPanel"
            class="calendar-event-selection"
            role="region"
            aria-labelledby="calendar-profile-choice-title"
            tabindex="-1"
            @keydown.esc="closeProfileChoice()"
          >
            <header class="calendar-event-selection-header">
              <div>
                <p class="eyebrow mb-1">Выберите направление</p>
                <h4 id="calendar-profile-choice-title" class="h5 mb-1">
                  {{ selectedEvent.olympiadName }}
                </h4>
                <p class="text-body-secondary small mb-0">
                  {{ selectedEvent.stageName }} ·
                  {{ eventDateLabel(selectedEvent, true) }} ·
                  {{ selectedEvent.profiles.length }}
                  {{ pluralize(selectedEvent.profiles.length, 'направление', 'направления', 'направлений') }}
                </p>
              </div>
              <button
                type="button"
                class="btn btn-sm btn-outline-secondary"
                aria-label="Закрыть выбор направления"
                @click="closeProfileChoice()"
              >
                <i class="fa-solid fa-xmark" aria-hidden="true"></i>
              </button>
            </header>

            <div class="calendar-profile-grid">
              <RouterLink
                v-for="profile in selectedEvent.profiles"
                :key="profile.slug"
                :to="eventRoute(selectedEvent, profile)"
                class="calendar-profile-card"
                :aria-label="`Открыть направление «${profileLabel(profile)}»`"
              >
                <span class="calendar-profile-card-icon" aria-hidden="true">
                  <i class="fa-solid fa-book-open"></i>
                </span>
                <span class="calendar-profile-card-copy">
                  <strong>{{ profileLabel(profile) }}</strong>
                  <small>Открыть карточку</small>
                </span>
                <i class="fa-solid fa-arrow-right calendar-profile-card-arrow" aria-hidden="true"></i>
              </RouterLink>
            </div>
          </section>
        </div>

        <div class="calendar-agenda d-md-none" aria-label="События месяца">
          <article v-for="event in monthEvents" :key="event.id" class="calendar-agenda-item">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
              <time class="calendar-agenda-date" :datetime="event.startsOn">
                {{ eventDateLabel(event, true) }}
              </time>
              <span
                class="calendar-confidence"
                :class="`calendar-confidence-${event.displayStatus}`"
              >
                <i
                  class="fa-solid"
                  :class="event.displayStatus === 'confirmed' ? 'fa-circle-check' : 'fa-clock-rotate-left'"
                  aria-hidden="true"
                ></i>
                {{ confidenceLabel(event) }}
              </span>
              <span v-if="event.cycleLabel" class="badge text-bg-secondary">
                {{ event.cycleLabel }}
              </span>
            </div>
            <h4 class="h6 mb-1">{{ event.olympiadName }}</h4>
            <p class="small text-body-secondary mb-2">{{ event.stageName }}</p>
            <div class="d-flex flex-wrap gap-2">
              <RouterLink
                v-for="profile in event.profiles.slice(0, 3)"
                :key="profile.slug"
                :to="eventRoute(event, profile)"
                class="calendar-profile-link"
              >
                {{ profileLabel(profile) }}
              </RouterLink>
              <details v-if="event.profiles.length > 3" class="calendar-profile-more">
                <summary>Ещё {{ event.profiles.length - 3 }}</summary>
                <div class="d-flex flex-wrap gap-2 mt-2">
                  <RouterLink
                    v-for="profile in event.profiles.slice(3)"
                    :key="profile.slug"
                    :to="eventRoute(event, profile)"
                    class="calendar-profile-link"
                  >
                    {{ profileLabel(profile) }}
                  </RouterLink>
                </div>
              </details>
            </div>
          </article>
        </div>
      </template>

      <div v-else class="empty-state rounded-4 p-4 text-center">
        <div class="empty-state-icon" aria-hidden="true">
          <i class="fa-solid fa-calendar-xmark"></i>
        </div>
        <h4 class="h6 mt-3">В этом месяце событий не найдено</h4>
        <p class="text-body-secondary mb-0">Перейдите к соседнему месяцу или измените фильтры.</p>
      </div>

      <footer v-if="!loading && !error" class="calendar-note">
        <i class="fa-solid fa-circle-info" aria-hidden="true"></i>
        <span>
          Календарь показывает только этапы с опубликованными датами.
          Совпадающие этапы разных профилей объединены
          <template v-if="sourceTotal > events.length">
            ({{ sourceTotal }} записей в {{ events.length }}
            {{ pluralize(events.length, 'событие', 'события', 'событий') }})
          </template>.
          <span class="d-none d-md-inline">
            Нажмите на объединённое событие, чтобы выбрать направление.
          </span>
          <span class="d-md-none">
            Выберите нужное направление в списке события.
          </span>
        </span>
      </footer>
    </div>
  </section>
</template>
