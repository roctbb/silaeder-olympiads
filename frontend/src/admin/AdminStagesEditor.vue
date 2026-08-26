<script setup>
import { emptyStage } from './formDefaults'

const stages = defineModel({ type: Array, required: true })

function add() {
  stages.value.push(emptyStage(stages.value.length))
}

function remove(index) {
  stages.value.splice(index, 1)
  stages.value.forEach((stage, position) => {
    stage.position = position
  })
}
</script>

<template>
  <section class="admin-section card border-0 shadow-sm">
    <div class="card-body p-4">
      <div class="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div>
          <h2 class="h4 mb-1">Этапы</h2>
          <p class="small text-body-secondary mb-0">Даты, регистрация, формат и первоисточник.</p>
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="add">Добавить этап</button>
      </div>

      <div v-if="stages.length" class="vstack gap-3">
        <fieldset v-for="(stage, index) in stages" :key="index" class="nested-editor rounded-3 p-3 p-md-4">
          <legend class="float-none w-auto px-2 h6">Этап {{ index + 1 }}</legend>
          <div class="row g-3">
            <div class="col-md-8">
              <label :for="'stage-name-' + index" class="form-label">Название *</label>
              <input :id="'stage-name-' + index" v-model="stage.name" class="form-control" required maxlength="180" />
            </div>
            <div class="col-md-4">
              <label :for="'stage-type-' + index" class="form-label">Тип этапа</label>
              <input :id="'stage-type-' + index" v-model="stage.stage_type" class="form-control" maxlength="80" placeholder="отборочный" />
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'stage-start-' + index" class="form-label">Начало</label>
              <input :id="'stage-start-' + index" v-model="stage.starts_on" class="form-control" type="date" />
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'stage-end-' + index" class="form-label">Окончание</label>
              <input :id="'stage-end-' + index" v-model="stage.ends_on" class="form-control" type="date" />
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'stage-precision-' + index" class="form-label">Точность</label>
              <select :id="'stage-precision-' + index" v-model="stage.date_precision" class="form-select">
                <option value="exact">Точная дата</option>
                <option value="range">Диапазон</option>
                <option value="month">Месяц</option>
                <option value="approximate">Примерно</option>
                <option value="tba">Уточняется</option>
              </select>
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'stage-format-' + index" class="form-label">Формат</label>
              <select :id="'stage-format-' + index" v-model="stage.format" class="form-select">
                <option value="online">Онлайн</option>
                <option value="offline">Очно</option>
                <option value="hybrid">Гибридный</option>
                <option value="unknown">Уточняется</option>
              </select>
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'reg-open-' + index" class="form-label">Открытие регистрации</label>
              <input :id="'reg-open-' + index" v-model="stage.registration_opens_on" class="form-control" type="date" />
            </div>
            <div class="col-sm-6 col-md-3">
              <label :for="'reg-close-' + index" class="form-label">Закрытие регистрации</label>
              <input :id="'reg-close-' + index" v-model="stage.registration_closes_on" class="form-control" type="date" />
            </div>
            <div class="col-md-6">
              <label :for="'stage-location-' + index" class="form-label">Место</label>
              <input :id="'stage-location-' + index" v-model="stage.location" class="form-control" maxlength="500" />
            </div>
            <div class="col-12">
              <label :for="'stage-source-' + index" class="form-label">Источник даты</label>
              <input :id="'stage-source-' + index" v-model="stage.source_url" class="form-control" type="url" maxlength="1000" placeholder="https://…" />
            </div>
            <div class="col-12">
              <label :for="'stage-details-' + index" class="form-label">Пояснение</label>
              <textarea :id="'stage-details-' + index" v-model="stage.details" class="form-control" rows="2"></textarea>
            </div>
            <div class="col-12 d-flex flex-wrap justify-content-between gap-2 align-items-center">
              <div class="form-check">
                <input :id="'stage-confirmed-' + index" v-model="stage.is_date_confirmed" class="form-check-input" type="checkbox" />
                <label :for="'stage-confirmed-' + index" class="form-check-label">Дата подтверждена источником</label>
              </div>
              <button type="button" class="btn btn-sm btn-outline-danger" @click="remove(index)">Удалить этап</button>
            </div>
          </div>
        </fieldset>
      </div>
      <p v-else class="empty-admin-section mb-0">Этапов пока нет.</p>
    </div>
  </section>
</template>
