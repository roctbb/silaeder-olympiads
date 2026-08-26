<script setup>
import { emptyBenefit, slugify } from './formDefaults'

const benefits = defineModel({ type: Array, required: true })

function fillUniversitySlug(benefit) {
  if (!benefit.university.slug) benefit.university.slug = slugify(benefit.university.name)
}

function applyBenefitTypeDefaults(benefit) {
  if (benefit.benefit_type === 'bvi') benefit.has_bvi = true
  if (benefit.benefit_type === 'hundred_points') benefit.has_hundred_points = true
}
</script>

<template>
  <section class="admin-section card border-0 shadow-sm">
    <div class="card-body p-4">
      <div class="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div>
          <h2 class="h4 mb-1">Льготы и награды</h2>
          <p class="small text-body-secondary mb-0">Добавляйте только подтверждённые условия со ссылкой.</p>
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="benefits.push(emptyBenefit())">
          Добавить запись
        </button>
      </div>

      <div v-if="benefits.length" class="vstack gap-3">
        <fieldset v-for="(benefit, index) in benefits" :key="index" class="nested-editor rounded-3 p-3 p-md-4">
          <legend class="float-none w-auto px-2 h6">Условие или награда {{ index + 1 }}</legend>
          <div class="row g-3">
            <div class="col-md-4">
              <label :for="'benefit-type-' + index" class="form-label">Тип</label>
              <select
                :id="'benefit-type-' + index"
                v-model="benefit.benefit_type"
                class="form-select"
                @change="applyBenefitTypeDefaults(benefit)"
              >
                <option value="bvi">БВИ</option>
                <option value="hundred_points">100 баллов</option>
                <option value="grant">Грант</option>
                <option value="prize">Приз</option>
                <option value="other">Другое</option>
              </select>
            </div>
            <div class="col-md-8">
              <label :for="'benefit-title-' + index" class="form-label">Название *</label>
              <input :id="'benefit-title-' + index" v-model="benefit.title" class="form-control" required maxlength="255" />
            </div>
            <div class="col-12">
              <fieldset>
                <legend class="form-label mb-2">Какие права подтверждены</legend>
                <div class="d-flex flex-wrap gap-3">
                  <div class="form-check">
                    <input
                      :id="'benefit-has-bvi-' + index"
                      v-model="benefit.has_bvi"
                      class="form-check-input"
                      type="checkbox"
                      :disabled="benefit.benefit_type === 'bvi'"
                    />
                    <label class="form-check-label" :for="'benefit-has-bvi-' + index">
                      Есть вариант БВИ
                    </label>
                  </div>
                  <div class="form-check">
                    <input
                      :id="'benefit-has-hundred-points-' + index"
                      v-model="benefit.has_hundred_points"
                      class="form-check-input"
                      type="checkbox"
                      :disabled="benefit.benefit_type === 'hundred_points'"
                    />
                    <label class="form-check-label" :for="'benefit-has-hundred-points-' + index">
                      Есть вариант 100 баллов
                    </label>
                  </div>
                </div>
                <p class="small text-body-secondary mb-0 mt-2">
                  Отметьте оба варианта, если вуз выбирает право по программе или степени диплома.
                </p>
              </fieldset>
            </div>
            <div class="col-12">
              <label :for="'benefit-description-' + index" class="form-label">Описание</label>
              <textarea :id="'benefit-description-' + index" v-model="benefit.description" class="form-control" rows="2"></textarea>
            </div>
            <div class="col-md-6">
              <label :for="'benefit-requirement-' + index" class="form-label">Требование к диплому</label>
              <input :id="'benefit-requirement-' + index" v-model="benefit.diploma_requirement" class="form-control" maxlength="255" />
            </div>
            <div class="col-sm-8 col-md-4">
              <label :for="'benefit-ege-' + index" class="form-label">Предмет ЕГЭ</label>
              <input :id="'benefit-ege-' + index" v-model="benefit.ege_subject" class="form-control" maxlength="160" />
            </div>
            <div class="col-sm-4 col-md-2">
              <label :for="'benefit-score-' + index" class="form-label">Мин. балл</label>
              <input :id="'benefit-score-' + index" v-model.number="benefit.ege_min_score" class="form-control" type="number" min="0" max="100" />
            </div>
            <div v-if="benefit.benefit_type !== 'prize'" class="col-sm-4">
              <label :for="'benefit-year-' + index" class="form-label">Год приёма</label>
              <input :id="'benefit-year-' + index" v-model.number="benefit.admission_year" class="form-control" type="number" min="2000" max="2100" />
            </div>
            <div v-else class="col-sm-4 d-flex align-items-end">
              <p class="small text-body-secondary mb-2">
                Год сезона награды пока не хранится отдельно.
              </p>
            </div>
            <div class="col-sm-8">
              <label :for="'benefit-source-' + index" class="form-label">Источник условий</label>
              <input :id="'benefit-source-' + index" v-model="benefit.source_url" class="form-control" type="url" maxlength="1000" placeholder="https://…" />
            </div>
          </div>

          <fieldset class="mt-4 university-fields">
            <legend class="h6">Вуз <span class="fw-normal text-body-secondary">(необязательно)</span></legend>
            <div class="row g-3">
              <div class="col-md-7">
                <label :for="'university-name-' + index" class="form-label">Название</label>
                <input
                  :id="'university-name-' + index"
                  v-model="benefit.university.name"
                  class="form-control"
                  maxlength="255"
                  @blur="fillUniversitySlug(benefit)"
                />
              </div>
              <div class="col-md-5">
                <label :for="'university-short-' + index" class="form-label">Сокращение</label>
                <input :id="'university-short-' + index" v-model="benefit.university.short_name" class="form-control" maxlength="100" />
              </div>
              <div class="col-md-6">
                <label :for="'university-slug-' + index" class="form-label">Slug</label>
                <input
                  :id="'university-slug-' + index"
                  v-model="benefit.university.slug"
                  class="form-control"
                  :required="Boolean(benefit.university.name)"
                  pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                  maxlength="180"
                />
              </div>
              <div class="col-md-6">
                <label :for="'university-url-' + index" class="form-label">Сайт вуза</label>
                <input :id="'university-url-' + index" v-model="benefit.university.website_url" class="form-control" type="url" maxlength="1000" />
              </div>
            </div>
          </fieldset>

          <div class="text-end mt-3">
            <button type="button" class="btn btn-sm btn-outline-danger" @click="benefits.splice(index, 1)">
              Удалить льготу
            </button>
          </div>
        </fieldset>
      </div>
      <p v-else class="empty-admin-section mb-0">Льгот и наград пока нет.</p>
    </div>
  </section>
</template>
