<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { logoutUser } from '../services/api'
import { loginUrl, useAuth } from '../services/auth'
import { useTheme } from '../services/theme'

const { theme, toggleTheme } = useTheme()
const { state: auth, refresh: refreshAuth, clear: clearAuth } = useAuth()
const route = useRoute()
const menuOpen = ref(false)
const loggingOut = ref(false)
const navbarLoginUrl = computed(() => loginUrl(route.fullPath))
const logoutError = ref('')

onMounted(refreshAuth)

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    const result = await logoutUser(auth.csrfToken)
    clearAuth()
    if (result?.logout_url) window.location.assign(result.logout_url)
  } catch (error) {
    if (error.status === 401) {
      clearAuth()
    } else {
      logoutError.value = error.message || 'Не удалось выйти.'
    }
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <header class="sticky-top">
    <nav class="navbar navbar-expand-lg navbar-dark bg-brand shadow-sm" aria-label="Главная навигация">
      <div class="container">
        <RouterLink class="navbar-brand d-flex align-items-center gap-2 fw-bold" to="/">
          <span class="brand-mark" aria-hidden="true">О</span>
          <span>Календарь олимпиад</span>
        </RouterLink>

        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#main-navigation"
          aria-controls="main-navigation"
          aria-expanded="false"
          :aria-label="menuOpen ? 'Закрыть меню' : 'Открыть меню'"
          @click="menuOpen = !menuOpen"
        >
          <i
            class="fa-solid"
            :class="menuOpen ? 'fa-xmark' : 'fa-bars'"
            aria-hidden="true"
          ></i>
        </button>

        <div id="main-navigation" class="collapse navbar-collapse">
          <ul class="navbar-nav ms-auto align-items-md-center gap-md-1">
            <li class="nav-item">
              <RouterLink class="nav-link" to="/">Каталог</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/my-plan">Мой план</RouterLink>
            </li>
            <li v-if="auth.loading && !auth.initialized" class="nav-item ms-lg-2">
              <span class="navbar-user" role="status">
                <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
                <span>Проверяем вход…</span>
              </span>
            </li>
            <template v-else-if="auth.user">
              <li class="nav-item ms-lg-2">
                <span class="navbar-user" :title="auth.user.name">
                  <i class="fa-solid fa-circle-user" aria-hidden="true"></i>
                  <span>{{ auth.user.name }}</span>
                </span>
              </li>
              <li class="nav-item">
                <button
                  class="btn btn-sm btn-outline-light"
                  type="button"
                  :disabled="loggingOut"
                  @click="logout"
                >
                  <i
                    class="fa-solid me-1"
                    :class="loggingOut ? 'fa-spinner fa-spin' : 'fa-right-from-bracket'"
                    aria-hidden="true"
                  ></i>
                  Выйти
                </button>
              </li>
              <li v-if="logoutError" class="nav-item px-lg-2" aria-live="polite">
                <span class="small text-warning">
                  <i class="fa-solid fa-triangle-exclamation me-1" aria-hidden="true"></i>
                  {{ logoutError }}
                </span>
              </li>
            </template>
            <li v-else class="nav-item ms-lg-2">
              <a class="btn btn-sm navbar-login" :href="navbarLoginUrl">
                <i class="fa-solid fa-right-to-bracket me-1" aria-hidden="true"></i>
                Войти через ЛК
              </a>
            </li>
            <li class="nav-item ms-lg-2">
              <button
                class="btn btn-sm btn-outline-secondary theme-toggle"
                type="button"
                :aria-label="theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'"
                :title="theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'"
                @click="toggleTheme"
              >
                <i
                  class="fa-solid"
                  :class="theme === 'dark' ? 'fa-sun' : 'fa-moon'"
                  aria-hidden="true"
                ></i>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  </header>
</template>
