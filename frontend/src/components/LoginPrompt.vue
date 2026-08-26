<script setup>
import { loginUrl } from '../services/auth'

defineProps({
  title: { type: String, default: 'Войдите через ЛК «Силаэдр»' },
  description: {
    type: String,
    default: 'После входа можно составить личный план и отмечать результаты этапов.',
  },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div
    class="login-prompt"
    :class="{ 'login-prompt-compact': compact }"
    role="region"
    aria-label="Вход в личный кабинет"
  >
    <span class="login-prompt-icon" aria-hidden="true">
      <i class="fa-solid fa-user-lock"></i>
    </span>
    <div class="flex-grow-1">
      <h2 :class="compact ? 'h6' : 'h4'" class="mb-1">{{ title }}</h2>
      <p class="text-body-secondary mb-0">{{ description }}</p>
    </div>
    <a class="btn btn-primary flex-shrink-0" :href="loginUrl()">
      <i class="fa-solid fa-right-to-bracket me-2" aria-hidden="true"></i>
      Войти через ЛК
    </a>
  </div>
</template>
