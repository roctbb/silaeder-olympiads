<script setup>
import { computed } from 'vue'
import { dateConfidence } from '../utils/format'

const props = defineProps({
  stage: { type: Object, default: null },
  dataStatus: { type: String, default: '' },
})

const status = computed(() => dateConfidence(props.stage, props.dataStatus))
const view = computed(() => {
  if (status.value === 'confirmed') {
    return { label: 'Дата подтверждена', className: 'status-confirmed', iconClass: 'fa-circle-check' }
  }
  if (status.value === 'previous_year_estimate') {
    return {
      label: 'Ориентир по прошлому году',
      className: 'status-estimate',
      iconClass: 'fa-clock-rotate-left',
    }
  }
  return { label: 'Дата уточняется', className: 'status-tba', iconClass: 'fa-circle-question' }
})
</script>

<template>
  <span class="status-badge" :class="view.className">
    <i class="fa-solid status-icon" :class="view.iconClass" aria-hidden="true"></i>
    {{ view.label }}
  </span>
</template>
