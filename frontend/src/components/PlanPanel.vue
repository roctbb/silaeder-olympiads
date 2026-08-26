<script setup>
import { computed, reactive, watch } from 'vue'
import LoginPrompt from './LoginPrompt.vue'

const props = defineProps({
  authenticated: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  planning: { type: Object, default: null },
  error: { type: String, default: '' },
  notice: { type: String, default: '' },
  savingAction: { type: String, default: '' },
})
const emit = defineEmits(['add', 'remove', 'save-settings', 'retry'])

const settings = reactive({
  status: 'planned',
  is_name_public: true,
  reminders_enabled: true,
  reminder_days_before: [7, 3, 1],
})

const participantCount = computed(() => Number(props.planning?.participant_count || 0))
const inPlan = computed(() => Boolean(props.planning?.plan))
const settingsValid = computed(() => (
  !settings.reminders_enabled || settings.reminder_days_before.length > 0
))

watch(
  () => props.planning?.plan,
  (plan) => {
    settings.status = plan?.status || 'planned'
    settings.is_name_public = plan ? Boolean(plan.is_name_public) : true
    settings.reminders_enabled = plan?.reminders_enabled !== false
    settings.reminder_days_before = Array.isArray(plan?.reminder_days_before)
      ? [...plan.reminder_days_before]
      : [7, 3, 1]
  },
  { immediate: true, deep: true },
)

function saveSettings() {
  emit('save-settings', {
    status: settings.status,
    is_name_public: settings.is_name_public,
    reminders_enabled: settings.reminders_enabled,
    reminder_days_before: [...settings.reminder_days_before].map(Number).sort((a, b) => b - a),
  })
}
</script>

<template>
  <section class="card plan-panel border-0 shadow-sm mb-4" aria-labelledby="plan-panel-title">
    <div class="card-body p-4">
      <div class="d-flex align-items-start justify-content-between gap-3 mb-3">
        <div>
          <p class="eyebrow mb-1">Личный календарь</p>
          <h2 id="plan-panel-title" class="h5 mb-1">План участия</h2>
          <p class="small text-body-secondary mb-0">
            <i class="fa-solid fa-users me-1" aria-hidden="true"></i>
            {{ participantCount }} выбрали эту олимпиаду
          </p>
        </div>
        <span v-if="inPlan" class="plan-added-icon" title="Добавлено в план" aria-label="Добавлено в план">
          <i class="fa-solid fa-calendar-check" aria-hidden="true"></i>
        </span>
      </div>

      <div v-if="loading" class="d-flex align-items-center gap-2 py-2" role="status">
        <i class="fa-solid fa-spinner fa-spin text-primary" aria-hidden="true"></i>
        <span class="small">Загружаем ваш план…</span>
      </div>

      <div v-else-if="error" class="alert alert-danger py-2 px-3 small" role="alert">
        <p class="mb-2">{{ error }}</p>
        <button type="button" class="btn btn-sm btn-outline-danger" @click="$emit('retry')">
          Повторить
        </button>
      </div>

      <div v-else-if="notice" class="alert alert-success py-2 px-3 small" role="status">
        <i class="fa-solid fa-circle-check me-1" aria-hidden="true"></i>{{ notice }}
      </div>

      <LoginPrompt
        v-if="!loading && !error && !authenticated"
        compact
        title="Войдите, чтобы добавить в план"
        description="Просмотр олимпиады останется доступен без входа."
      />

      <template v-else-if="!loading && !error && authenticated && !inPlan">
        <button
          type="button"
          class="btn btn-primary w-100"
          :disabled="Boolean(savingAction)"
          @click="$emit('add')"
        >
          <i
            class="fa-solid me-2"
            :class="savingAction === 'add' ? 'fa-spinner fa-spin' : 'fa-calendar-plus'"
            aria-hidden="true"
          ></i>
          {{ savingAction === 'add' ? 'Добавляем…' : 'Добавить в мой план' }}
        </button>
      </template>

      <form v-else-if="!loading && !error && authenticated" @submit.prevent="saveSettings">
        <div class="mb-3">
          <label class="form-label" for="plan-status">Статус участия</label>
          <select
            id="plan-status"
            v-model="settings.status"
            class="form-select form-select-sm"
            :disabled="Boolean(savingAction)"
          >
            <option value="planned">В планах</option>
            <option value="registered">Зарегистрирован</option>
            <option value="participating">Участвую</option>
            <option value="completed">Завершено</option>
          </select>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            id="plan-public-name"
            v-model="settings.is_name_public"
            class="form-check-input"
            type="checkbox"
            role="switch"
            :disabled="Boolean(savingAction)"
          />
          <label class="form-check-label" for="plan-public-name">
            Показывать моё имя в публичном списке участников
          </label>
          <div class="form-text">По умолчанию включено. Вы можете скрыть имя в любой момент.</div>
        </div>

        <div class="form-check form-switch mb-2">
          <input
            id="plan-reminders"
            v-model="settings.reminders_enabled"
            class="form-check-input"
            type="checkbox"
            role="switch"
            :disabled="Boolean(savingAction)"
          />
          <label class="form-check-label" for="plan-reminders">Напоминать через ЛК</label>
        </div>

        <fieldset v-if="settings.reminders_enabled" class="reminder-days mb-3">
          <legend class="small fw-semibold mb-2">За сколько дней</legend>
          <div class="d-flex flex-wrap gap-2">
            <div v-for="day in [7, 3, 1]" :key="day" class="form-check reminder-day-check">
              <input
                :id="`reminder-day-${day}`"
                v-model="settings.reminder_days_before"
                class="form-check-input"
                type="checkbox"
                :value="day"
                :disabled="Boolean(savingAction)"
              />
              <label class="form-check-label" :for="`reminder-day-${day}`">{{ day }}</label>
            </div>
          </div>
          <p v-if="!settingsValid" class="small text-danger mt-2 mb-0" role="alert">
            Выберите хотя бы один срок напоминания.
          </p>
        </fieldset>

        <div class="d-flex flex-column gap-2">
          <button
            class="btn btn-sm btn-primary"
            type="submit"
            :disabled="Boolean(savingAction) || !settingsValid"
          >
            <i
              class="fa-solid me-1"
              :class="savingAction === 'settings' ? 'fa-spinner fa-spin' : 'fa-check'"
              aria-hidden="true"
            ></i>
            {{ savingAction === 'settings' ? 'Сохраняем…' : 'Сохранить настройки' }}
          </button>
          <button
            class="btn btn-sm btn-link text-danger"
            type="button"
            :disabled="Boolean(savingAction)"
            @click="$emit('remove')"
          >
            <i class="fa-solid fa-trash-can me-1" aria-hidden="true"></i>
            Убрать из плана
          </button>
        </div>
      </form>

      <details v-if="planning?.public_participants?.length" class="public-participants mt-3">
        <summary>
          Кто участвует · {{ planning.public_participants.length }}
        </summary>
        <ul class="list-unstyled mb-0 mt-2">
          <li v-for="participant in planning.public_participants" :key="participant.id || participant.name">
            <i class="fa-solid fa-user me-2" aria-hidden="true"></i>{{ participant.name }}
          </li>
        </ul>
      </details>
    </div>
  </section>
</template>
