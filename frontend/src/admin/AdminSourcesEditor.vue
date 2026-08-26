<script setup>
import { emptySource } from './formDefaults'

const sources = defineModel({ type: Array, required: true })
</script>

<template>
  <section class="admin-section card border-0 shadow-sm">
    <div class="card-body p-4">
      <div class="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div>
          <h2 class="h4 mb-1">Источники</h2>
          <p class="small text-body-secondary mb-0">Документы и официальные страницы, на которых основана запись.</p>
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="sources.push(emptySource())">
          Добавить источник
        </button>
      </div>

      <div v-if="sources.length" class="vstack gap-3">
        <fieldset v-for="(source, index) in sources" :key="index" class="nested-editor rounded-3 p-3 p-md-4">
          <legend class="float-none w-auto px-2 h6">Источник {{ index + 1 }}</legend>
          <div class="row g-3">
            <div class="col-md-7">
              <label :for="'source-title-' + index" class="form-label">Название *</label>
              <input :id="'source-title-' + index" v-model="source.title" class="form-control" required maxlength="255" />
            </div>
            <div class="col-md-5">
              <label :for="'source-publisher-' + index" class="form-label">Издатель</label>
              <input :id="'source-publisher-' + index" v-model="source.publisher" class="form-control" maxlength="255" />
            </div>
            <div class="col-12">
              <label :for="'source-url-' + index" class="form-label">Ссылка *</label>
              <input :id="'source-url-' + index" v-model="source.url" class="form-control" type="url" required maxlength="1000" placeholder="https://…" />
            </div>
            <div class="col-sm-4">
              <label :for="'source-type-' + index" class="form-label">Тип</label>
              <input :id="'source-type-' + index" v-model="source.source_type" class="form-control" maxlength="80" placeholder="calendar, regulation" />
            </div>
            <div class="col-sm-4">
              <label :for="'source-year-' + index" class="form-label">Учебный год</label>
              <input :id="'source-year-' + index" v-model="source.source_year" class="form-control" maxlength="9" placeholder="2025/26" />
            </div>
            <div class="col-sm-4">
              <label :for="'source-accessed-' + index" class="form-label">Проверено</label>
              <input :id="'source-accessed-' + index" v-model="source.accessed_on" class="form-control" type="date" />
            </div>
            <div class="col-12 text-end">
              <button type="button" class="btn btn-sm btn-outline-danger" @click="sources.splice(index, 1)">Удалить</button>
            </div>
          </div>
        </fieldset>
      </div>
      <p v-else class="empty-admin-section mb-0">Источников пока нет.</p>
    </div>
  </section>
</template>
