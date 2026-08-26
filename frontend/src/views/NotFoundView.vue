<template>
  <div class="container py-5">
    <div class="empty-state text-center rounded-4 p-5 mx-auto not-found">
      <div class="empty-state-icon" aria-hidden="true">
        <i class="fa-solid fa-compass"></i>
      </div>
      <p class="display-3 fw-bold text-primary mb-2">404</p>
      <h1 class="h3">Страница не найдена</h1>
      <p class="text-body-secondary">Возможно, адрес изменился или в нём есть опечатка.</p>
      <RouterLink class="btn btn-primary" to="/">Вернуться в каталог</RouterLink>
    </div>
  </div>
</template>
