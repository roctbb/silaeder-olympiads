<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pages: { type: Number, required: true },
})

defineEmits(['change'])

const visiblePages = computed(() => {
  if (props.pages <= 7) return Array.from({ length: props.pages }, (_, index) => index + 1)
  const values = new Set([1, props.pages])
  for (let value = props.page - 2; value <= props.page + 2; value += 1) {
    if (value > 1 && value < props.pages) values.add(value)
  }
  return [...values].sort((a, b) => a - b)
})
</script>

<template>
  <nav v-if="pages > 1" aria-label="Страницы каталога">
    <ul class="pagination justify-content-center flex-wrap">
      <li class="page-item" :class="{ disabled: page <= 1 }">
        <button
          type="button"
          class="page-link"
          :disabled="page <= 1"
          aria-label="Предыдущая страница"
          @click="$emit('change', page - 1)"
        >
          Назад
        </button>
      </li>

      <template v-for="(value, index) in visiblePages" :key="value">
        <li
          v-if="index > 0 && value - visiblePages[index - 1] > 1"
          class="page-item disabled"
          aria-hidden="true"
        >
          <span class="page-link">…</span>
        </li>
        <li class="page-item" :class="{ active: value === page }">
          <button
            type="button"
            class="page-link"
            :aria-current="value === page ? 'page' : undefined"
            :aria-label="'Страница ' + value"
            @click="$emit('change', value)"
          >
            {{ value }}
          </button>
        </li>
      </template>

      <li class="page-item" :class="{ disabled: page >= pages }">
        <button
          type="button"
          class="page-link"
          :disabled="page >= pages"
          aria-label="Следующая страница"
          @click="$emit('change', page + 1)"
        >
          Вперёд
        </button>
      </li>
    </ul>
  </nav>
</template>
