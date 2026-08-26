<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  stage: { type: Object, required: true },
  progress: { type: Object, default: null },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['save', 'clear'])

const form = reactive({
  participated: false,
  advanced: '',
  result: '',
})

watch(
  () => props.progress,
  (value) => {
    form.participated = Boolean(value?.participated)
    form.advanced = value?.advanced === true ? 'yes' : value?.advanced === false ? 'no' : ''
    form.result = value?.result || ''
  },
  { immediate: true, deep: true },
)

function submit() {
  emit('save', {
    stage_id: props.stage.id,
    participated: form.participated,
    advanced: form.participated && form.advanced
      ? form.advanced === 'yes'
      : null,
    result: form.participated && form.result.trim() ? form.result.trim() : null,
  })
}
</script>

<template>
  <form class="stage-progress mt-4" @submit.prevent="submit">
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
      <div>
        <p class="fw-semibold mb-0">Мой результат</p>
        <p class="small text-body-secondary mb-0">Эти отметки видны только вам.</p>
      </div>
      <span v-if="progress?.updated_at" class="stage-progress-saved small">
        <i class="fa-solid fa-circle-check me-1" aria-hidden="true"></i>
        Сохранено
      </span>
    </div>

    <div class="d-flex flex-wrap gap-3 mb-3">
      <div class="form-check">
        <input
          :id="`participated-${stage.id}`"
          v-model="form.participated"
          class="form-check-input"
          type="checkbox"
          :disabled="saving"
        />
        <label class="form-check-label" :for="`participated-${stage.id}`">Участвовал</label>
      </div>
    </div>

    <div v-if="form.participated" class="row g-2 align-items-end">
      <div class="col-sm-5">
        <label class="form-label" :for="`advanced-${stage.id}`">Проход дальше</label>
        <select
          :id="`advanced-${stage.id}`"
          v-model="form.advanced"
          class="form-select form-select-sm"
          :disabled="saving"
        >
          <option value="">Не отмечено</option>
          <option value="yes">Прошёл</option>
          <option value="no">Не прошёл</option>
        </select>
      </div>
      <div class="col-sm">
        <label class="form-label" :for="`result-${stage.id}`">Результат или балл</label>
        <input
          :id="`result-${stage.id}`"
          v-model="form.result"
          class="form-control form-control-sm"
          type="text"
          maxlength="500"
          placeholder="Например: 72 балла, призёр"
          :disabled="saving"
        />
      </div>
      <div class="col-sm-auto">
        <button class="btn btn-sm btn-outline-primary w-100" type="submit" :disabled="saving">
          <i
            class="fa-solid me-1"
            :class="saving ? 'fa-spinner fa-spin' : 'fa-check'"
            aria-hidden="true"
          ></i>
          {{ saving ? 'Сохраняем…' : 'Сохранить' }}
        </button>
      </div>
    </div>
    <div v-else class="d-flex flex-wrap gap-2">
      <button class="btn btn-sm btn-outline-primary" type="submit" :disabled="saving">
        <i
          class="fa-solid me-1"
          :class="saving ? 'fa-spinner fa-spin' : 'fa-check'"
          aria-hidden="true"
        ></i>
        {{ saving ? 'Сохраняем…' : 'Сохранить отметку' }}
      </button>
      <button
        v-if="progress"
        class="btn btn-sm btn-link text-danger"
        type="button"
        :disabled="saving"
        @click="emit('clear', stage.id)"
      >
        Очистить
      </button>
    </div>
    <button
      v-if="form.participated && progress"
      class="btn btn-sm btn-link text-danger mt-2"
      type="button"
      :disabled="saving"
      @click="emit('clear', stage.id)"
    >
      Очистить отметку
    </button>
  </form>
</template>
