<script setup>
import AppNavbar from './components/AppNavbar.vue'
</script>

<template>
  <a class="skip-link" href="#main-content">Перейти к содержимому</a>
  <div class="app-shell d-flex flex-column min-vh-100">
    <AppNavbar />
    <main id="main-content" class="flex-grow-1" tabindex="-1">
      <RouterView />
    </main>
    <footer class="border-top py-4 mt-auto">
      <div class="container d-flex flex-column flex-sm-row gap-2 justify-content-between small text-body-secondary">
        <span>Календарь олимпиад · 2026/27 учебный год</span>
        <span>Проверяйте даты на официальных сайтах организаторов</span>
      </div>
    </footer>
  </div>
</template>
