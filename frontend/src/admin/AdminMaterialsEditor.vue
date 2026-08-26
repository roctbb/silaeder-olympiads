<script setup>
import { emptyMaterial } from './formDefaults'

const materials = defineModel({ type: Array, required: true })
</script>

<template>
  <section class="admin-section card border-0 shadow-sm">
    <div class="card-body p-4">
      <div class="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div>
          <h2 class="h4 mb-1">Материалы</h2>
          <p class="small text-body-secondary mb-0">Внешние ссылки на задания и подготовку.</p>
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="materials.push(emptyMaterial())">
          Добавить материал
        </button>
      </div>
      <div v-if="materials.length" class="vstack gap-3">
        <fieldset v-for="(material, index) in materials" :key="index" class="nested-editor rounded-3 p-3 p-md-4">
          <legend class="float-none w-auto px-2 h6">Материал {{ index + 1 }}</legend>
          <div class="row g-3">
            <div class="col-md-7">
              <label :for="'material-title-' + index" class="form-label">Название *</label>
              <input :id="'material-title-' + index" v-model="material.title" class="form-control" required maxlength="255" />
            </div>
            <div class="col-sm-7 col-md-3">
              <label :for="'material-type-' + index" class="form-label">Тип</label>
              <select :id="'material-type-' + index" v-model="material.material_type" class="form-select">
                <option value="tasks">Задания</option>
                <option value="solutions">Решения</option>
                <option value="video">Видео</option>
                <option value="course">Курс</option>
                <option value="archive">Архив</option>
                <option value="other">Другое</option>
              </select>
            </div>
            <div class="col-sm-5 col-md-2">
              <label :for="'material-year-' + index" class="form-label">Год</label>
              <input :id="'material-year-' + index" v-model.number="material.year" class="form-control" type="number" min="1990" max="2100" />
            </div>
            <div class="col-12">
              <label :for="'material-url-' + index" class="form-label">Ссылка *</label>
              <input :id="'material-url-' + index" v-model="material.url" class="form-control" type="url" required maxlength="1000" placeholder="https://…" />
            </div>
            <div class="col-12 d-flex flex-wrap justify-content-between gap-2">
              <div class="form-check">
                <input :id="'material-official-' + index" v-model="material.is_official" class="form-check-input" type="checkbox" />
                <label :for="'material-official-' + index" class="form-check-label">Официальный материал</label>
              </div>
              <button type="button" class="btn btn-sm btn-outline-danger" @click="materials.splice(index, 1)">Удалить</button>
            </div>
          </div>
        </fieldset>
      </div>
      <p v-else class="empty-admin-section mb-0">Материалов пока нет.</p>
    </div>
  </section>
</template>
