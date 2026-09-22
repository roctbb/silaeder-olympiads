<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import LoadingState from '../components/LoadingState.vue'
import LoginPrompt from '../components/LoginPrompt.vue'
import { getMyClass, getClassCandidates, addClassStudent, removeClassStudent } from '../services/api'

const members = ref([])
const candidates = ref([])
const loading = ref(true)
const searching = ref(false)
const busy = ref(false)
const error = ref('')
const searchError = ref('')
const access = ref(true)
const notificationsAvailable = ref(true)
const csrfToken = ref('')
const query = ref('')
const grade = ref('')
let sequence = 0
let disposed = false
const statusLabels = { planned: 'В планах', registered: 'Зарегистрирован', participating: 'Участвует', completed: 'Завершено' }

async function search() {
  const current = ++sequence
  searching.value = true
  searchError.value = ''
  try {
    const result = await getClassCandidates({ q: query.value, grade: grade.value })
    if (current === sequence && !disposed) candidates.value = result.items
  } catch (caught) {
    if (current === sequence && !disposed) searchError.value = caught.message
  } finally {
    if (current === sequence && !disposed) searching.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getMyClass()
    if (disposed) return
    members.value = result.items
    notificationsAvailable.value = result.notifications_available
    csrfToken.value = result.csrf_token
    access.value = true
    await search()
  } catch (caught) {
    if (caught.status === 401 || caught.status === 403) access.value = false
    error.value = caught.message
  } finally {
    loading.value = false
  }
}

async function changeStudent(student, remove = false) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  // Discard a search started before this membership change.
  ++sequence
  try {
    if (remove) await removeClassStudent(student.id, csrfToken.value)
    else await addClassStudent(student.id, csrfToken.value)
    const result = await getMyClass()
    if (disposed) return
    members.value = result.items
    await search()
  } catch (caught) {
    error.value = caught.message
  } finally {
    busy.value = false
  }
}

onMounted(load)
onUnmounted(() => { disposed = true; ++sequence })
</script>

<template>
  <section class="my-plan-hero">
    <div class="container py-4 py-lg-5">
      <p class="eyebrow mb-2">Ученики и олимпиады</p>
      <h1 class="display-6 fw-bold mb-2">Мой класс</h1>
      <p class="text-body-secondary mb-0">
        Добавьте учеников, чтобы следить за их олимпиадами и получать общие уведомления.
      </p>
    </div>
  </section>
  <div class="container py-4 py-lg-5">
    <LoadingState v-if="loading" />
    <LoginPrompt v-else-if="!access" title="Раздел для учителей и администраторов"
      description="Войдите через ЛК с ролью учителя или администратора, чтобы собрать свой класс." />
    <template v-else>
      <div v-if="error" class="alert alert-danger" role="alert">
        {{ error }} <button class="btn btn-sm btn-outline-danger ms-2" @click="load">Повторить</button>
      </div>
      <p v-if="notificationsAvailable" class="alert alert-info">
        Напоминания приходят в ЛК за 7 дней и за день до подтверждённого этапа,
        а также при открытии регистрации. По каждой олимпиаде — одно сообщение за день
        со списком учеников, независимо от их личных настроек напоминаний.
      </p>
      <p v-else class="alert alert-warning">
        Вы вошли как локальный администратор. Для получения уведомлений создайте свой класс
        под учётной записью администратора или учителя из ЛК.
      </p>
      <div class="row g-4">
        <section class="col-lg-5" aria-labelledby="add-students-title">
          <div class="card border-0 shadow-sm">
            <div class="card-body p-4">
              <h2 id="add-students-title" class="h4">Добавить учеников</h2>
              <p class="small text-body-secondary">Здесь доступны ученики, уже вошедшие в календарь через ЛК.</p>
              <form class="row g-2 mb-3" @submit.prevent="search">
                <div class="col-8">
                  <label for="class-search" class="form-label">Имя ученика</label>
                  <input id="class-search" v-model="query" class="form-control" type="search" maxlength="100" />
                </div>
                <div class="col-4">
                  <label for="class-grade" class="form-label">Класс</label>
                  <select id="class-grade" v-model="grade" class="form-select">
                    <option value="">Все</option>
                    <option v-for="n in 7" :key="n" :value="n + 4">{{ n + 4 }}</option>
                  </select>
                </div>
                <div class="col-12"><button class="btn btn-outline-primary w-100" :disabled="busy || searching">Найти</button></div>
              </form>
              <p v-if="searchError" class="text-danger" role="alert">{{ searchError }}</p>
              <LoadingState v-if="searching" />
              <ul v-else-if="candidates.length" class="list-group list-group-flush">
                <li v-for="student in candidates" :key="student.id" class="list-group-item px-0 d-flex align-items-center justify-content-between gap-2">
                  <span>{{ student.name }}<small class="d-block text-body-secondary">{{ student.grade ? `${student.grade} класс` : 'Класс не указан' }}</small></span>
                  <button class="btn btn-sm btn-outline-primary" :disabled="busy" :aria-label="`Добавить: ${student.name}`" @click="changeStudent(student)">Добавить</button>
                </li>
              </ul>
              <p v-else-if="!searchError" class="text-body-secondary mb-0">Подходящих учеников нет. Попробуйте изменить поиск.</p>
              <p v-if="candidates.length === 100" class="small text-body-secondary mt-3 mb-0">Показаны первые 100 учеников. Уточните имя или класс.</p>
            </div>
          </div>
        </section>
        <section class="col-lg-7" aria-labelledby="class-students-title">
          <h2 id="class-students-title" class="h4 mb-3">Мои ученики · {{ members.length }}</h2>
          <p v-if="!members.length" class="empty-state rounded-4 p-4">В классе пока нет учеников. Добавьте их из списка.</p>
          <div class="vstack gap-3">
            <article v-for="student in members" :key="student.id" class="card border-0 shadow-sm">
              <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                  <div><h3 class="h5 mb-1">{{ student.name }}</h3><span class="text-body-secondary">{{ student.grade ? `${student.grade} класс` : 'Класс не указан' }}</span></div>
                  <button class="btn btn-sm btn-outline-secondary" :disabled="busy" :aria-label="`Убрать из класса: ${student.name}`" @click="changeStudent(student, true)">Убрать из класса</button>
                </div>
                <ul v-if="student.plans.length" class="list-unstyled mb-0">
                  <li v-for="plan in student.plans" :key="plan.id" class="mb-2">
                    <RouterLink v-if="plan.edition_status === 'published'" :to="{ name: 'olympiad', params: { slug: plan.olympiad.slug }, query: { academic_year: plan.academic_year } }">{{ plan.olympiad.name }}</RouterLink>
                    <span v-else>{{ plan.olympiad.name }} · Архив</span>
                    <small class="d-block text-body-secondary">{{ statusLabels[plan.status] }}</small>
                  </li>
                </ul>
                <p v-else class="text-body-secondary mb-0">В этом учебном году олимпиад в плане пока нет.</p>
              </div>
            </article>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
