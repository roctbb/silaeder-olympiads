<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminLogin, adminSession } from '../services/api'

const route = useRoute()
const router = useRouter()
const credentials = reactive({ username: '', password: '' })
const loading = ref(false)
const checking = ref(true)
const error = ref('')

function destination() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/admin'
  return redirect.startsWith('/admin') ? redirect : '/admin'
}

async function login() {
  loading.value = true
  error.value = ''
  try {
    await adminLogin(credentials)
    await router.replace(destination())
  } catch (caught) {
    error.value = caught.message || 'Не удалось войти.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await adminSession()
    await router.replace(destination())
  } catch {
    checking.value = false
  }
})
</script>

<template>
  <div class="admin-login container py-5">
    <div class="card border-0 shadow-lg mx-auto">
      <div class="card-body p-4 p-md-5">
        <p class="eyebrow mb-2">Администрирование</p>
        <h1 class="h2 mb-2">Вход редактора</h1>
        <p class="text-body-secondary mb-4">Доступ к редактированию каталога олимпиад.</p>

        <div v-if="checking" class="d-flex align-items-center gap-2" role="status">
          <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
          Проверяем сессию…
        </div>

        <form v-else @submit.prevent="login">
          <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
          <div class="mb-3">
            <label for="admin-username" class="form-label">Логин</label>
            <input
              id="admin-username"
              v-model.trim="credentials.username"
              class="form-control form-control-lg"
              autocomplete="username"
              required
              autofocus
            />
          </div>
          <div class="mb-4">
            <label for="admin-password" class="form-label">Пароль</label>
            <input
              id="admin-password"
              v-model="credentials.password"
              class="form-control form-control-lg"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <button class="btn btn-primary btn-lg w-100" type="submit" :disabled="loading">
            <i v-if="loading" class="fa-solid fa-spinner fa-spin me-2" aria-hidden="true"></i>
            {{ loading ? 'Входим…' : 'Войти' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
