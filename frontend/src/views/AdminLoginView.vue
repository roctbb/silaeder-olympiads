<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminLogin, adminSession } from '../services/api'
import { loginUrl } from '../services/auth'

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

const crmLoginUrl = computed(() => loginUrl(destination()))

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
        <p class="text-body-secondary mb-4">
          Администраторы ЛК Силаэдр получают доступ автоматически.
        </p>

        <div v-if="checking" class="d-flex align-items-center gap-2" role="status">
          <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
          Проверяем сессию…
        </div>

        <template v-else>
          <a class="btn btn-primary btn-lg w-100" :href="crmLoginUrl">
            <i class="fa-solid fa-right-to-bracket me-2" aria-hidden="true"></i>
            Войти через ЛК Силаэдр
          </a>

          <div class="d-flex align-items-center gap-3 my-4" aria-hidden="true">
            <span class="border-top flex-grow-1"></span>
            <span class="small text-body-secondary">или локальная учётная запись</span>
            <span class="border-top flex-grow-1"></span>
          </div>

          <form @submit.prevent="login">
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
            <button class="btn btn-outline-primary btn-lg w-100" type="submit" :disabled="loading">
              <i v-if="loading" class="fa-solid fa-spinner fa-spin me-2" aria-hidden="true"></i>
              {{ loading ? 'Входим…' : 'Войти' }}
            </button>
          </form>
        </template>
      </div>
    </div>
  </div>
</template>
