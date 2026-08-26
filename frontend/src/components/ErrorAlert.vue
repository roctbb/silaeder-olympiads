<script setup>
defineProps({
  message: { type: String, default: 'Не удалось загрузить данные.' },
  retryable: { type: Boolean, default: true },
  retryLabel: { type: String, default: 'Повторить' },
})
defineEmits(['retry'])
</script>

<template>
  <div class="alert alert-danger d-flex flex-wrap align-items-center justify-content-between gap-3" role="alert">
    <span class="d-flex align-items-center gap-2">
      <i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
      <span>{{ message }}</span>
    </span>
    <button v-if="retryable" type="button" class="btn btn-sm btn-outline-danger" @click="$emit('retry')">
      <i class="fa-solid fa-arrow-rotate-right me-1" aria-hidden="true"></i>
      {{ retryLabel }}
    </button>
  </div>
</template>
