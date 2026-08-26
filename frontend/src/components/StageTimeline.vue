<script setup>
import DataStatusBadge from './DataStatusBadge.vue'
import StageProgressEditor from './StageProgressEditor.vue'
import { LABELS, formatDateRange, formatStageDate } from '../utils/format'

defineProps({
  stages: { type: Array, default: () => [] },
  dataStatus: { type: String, default: '' },
  showPersonalProgress: { type: Boolean, default: false },
  progressByStage: { type: Object, default: () => ({}) },
  savingStageId: { type: [Number, String], default: null },
})
defineEmits(['save-progress', 'clear-progress'])
</script>

<template>
  <ol v-if="stages.length" class="stage-timeline list-unstyled mb-0">
    <li v-for="(stage, index) in stages" :key="stage.id || index" class="stage-timeline-item">
      <div class="stage-marker" aria-hidden="true">{{ index + 1 }}</div>
      <article class="card border-0 shadow-sm">
        <div class="card-body p-4">
          <div class="d-flex flex-column flex-sm-row justify-content-between align-items-sm-start gap-2">
            <div>
              <p v-if="stage.stage_type" class="eyebrow mb-1">{{ stage.stage_type }}</p>
              <h3 class="h5 mb-2">{{ stage.name }}</h3>
            </div>
            <DataStatusBadge :stage="stage" :data-status="dataStatus" />
          </div>

          <p class="stage-date h6 mt-3 mb-3">
            {{ formatStageDate(stage) }}
          </p>

          <dl class="compact-facts compact-facts-grid mb-0">
            <div>
              <dt>Формат</dt>
              <dd>{{ LABELS.format[stage.format] || stage.format }}</dd>
            </div>
            <div v-if="stage.location">
              <dt>Место</dt>
              <dd>{{ stage.location }}</dd>
            </div>
            <div v-if="stage.registration_opens_on || stage.registration_closes_on">
              <dt>Регистрация</dt>
              <dd>
                {{ formatDateRange(stage.registration_opens_on, stage.registration_closes_on) }}
              </dd>
            </div>
          </dl>

          <p v-if="stage.details" class="mt-3 mb-0 text-body-secondary">{{ stage.details }}</p>
          <a
            v-if="stage.source_url"
            class="source-link d-inline-flex mt-3"
            :href="stage.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            Источник даты
            <i class="fa-solid fa-arrow-up-right-from-square external-link-icon" aria-hidden="true"></i>
          </a>
          <StageProgressEditor
            v-if="showPersonalProgress"
            :stage="stage"
            :progress="progressByStage[stage.id] || null"
            :saving="String(savingStageId) === String(stage.id)"
            @save="$emit('save-progress', $event)"
            @clear="$emit('clear-progress', $event)"
          />
        </div>
      </article>
    </li>
  </ol>
  <div v-else class="empty-state rounded-4 p-4">
    <div class="d-flex align-items-start gap-3">
      <i class="fa-solid fa-calendar-xmark empty-inline-icon" aria-hidden="true"></i>
      <div>
        <p class="mb-1 fw-semibold">Этапы пока не опубликованы</p>
        <p class="text-body-secondary mb-0">Добавим расписание, когда организатор объявит даты.</p>
      </div>
    </div>
  </div>
</template>
