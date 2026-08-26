<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorAlert from '../components/ErrorAlert.vue'
import LoadingState from '../components/LoadingState.vue'
import { adminLogout, adminSession, deleteAdminOlympiad, getAdminOlympiads } from '../services/api'
import { LABELS, gradesLabel } from '../utils/format'

const router = useRouter()
const items = ref([])
const username = ref('')
const search = ref('')
const loading = ref(true)
const error = ref('')
const deletingSlug = ref('')

const filteredItems = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('ru')
  if (!query) return items.value
  return items.value.filter((item) =>
    [item.name, item.family_name, item.profile, item.organizer, item.slug]
      .filter(Boolean)
      .some((value) => value.toLocaleLowerCase('ru').includes(query)),
  )
})

const counts = computed(() => ({
  total: items.value.length,
  published: items.value.filter((item) => item.status === 'published').length,
  drafts: items.value.filter((item) => item.status === 'draft').length,
}))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [session, result] = await Promise.all([adminSession(), getAdminOlympiads()])
    username.value = session.username
    items.value = result.items
  } catch (caught) {
    if (caught.status === 401) {
      await router.replace({ name: 'admin-login' })
      return
    }
    error.value = caught.message || 'Не удалось загрузить записи.'
  } finally {
    loading.value = false
  }
}

async function logout() {
  await adminLogout()
  await router.replace({ name: 'admin-login' })
}

async function remove(item) {
  if (!window.confirm('Удалить «' + item.name + '» вместе со всеми этапами и материалами?')) return
  deletingSlug.value = item.slug
  error.value = ''
  try {
    await deleteAdminOlympiad(item.slug)
    items.value = items.value.filter((candidate) => candidate.slug !== item.slug)
  } catch (caught) {
    error.value = caught.message || 'Не удалось удалить запись.'
  } finally {
    deletingSlug.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="container py-4 py-lg-5">
    <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3 mb-4">
      <div>
        <p class="eyebrow mb-1">Редактор · {{ username || '…' }}</p>
        <h1 class="h2 mb-2">Олимпиады</h1>
        <p class="text-body-secondary mb-0">Управление каталогом на 2026/27 учебный год.</p>
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button type="button" class="btn btn-outline-secondary" @click="logout">Выйти</button>
        <RouterLink class="btn btn-primary" :to="{ name: 'admin-new' }">Добавить олимпиаду</RouterLink>
      </div>
    </header>

    <LoadingState v-if="loading" />
    <template v-else>
      <ErrorAlert v-if="error" :message="error" @retry="load" />

      <div class="row g-3 mb-4" aria-label="Сводка">
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ counts.total }}</strong><span>всего</span>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ counts.published }}</strong><span>опубликовано</span>
          </div>
        </div>
        <div class="col-sm-4">
          <div class="admin-stat card border-0 shadow-sm p-3">
            <strong>{{ counts.drafts }}</strong><span>черновиков</span>
          </div>
        </div>
      </div>

      <div class="card border-0 shadow-sm">
        <div class="card-body border-bottom p-3 p-md-4">
          <label for="admin-search" class="form-label visually-hidden">Поиск по записям</label>
          <input
            id="admin-search"
            v-model="search"
            class="form-control"
            type="search"
            placeholder="Поиск по названию, профилю или slug"
          />
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0 admin-table">
            <caption class="visually-hidden">Список олимпиад</caption>
            <thead>
              <tr>
                <th scope="col">Олимпиада</th>
                <th scope="col">Классы</th>
                <th scope="col">Статус</th>
                <th scope="col">Перечень</th>
                <th scope="col"><span class="visually-hidden">Действия</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredItems" :key="item.edition_id">
                <td>
                  <strong class="d-block">{{ item.name }}</strong>
                  <small class="text-body-secondary">{{ item.profile }} · {{ item.slug }}</small>
                </td>
                <td class="text-nowrap">{{ gradesLabel(item.grades) }}</td>
                <td>
                  <span
                    class="badge"
                    :class="item.status === 'published' ? 'text-bg-success' : 'text-bg-secondary'"
                  >
                    {{ LABELS.editionStatus[item.status] || item.status }}
                  </span>
                </td>
                <td>
                  <span
                    v-if="item.registry_status !== 'not_listed'"
                    class="small"
                    :class="{ 'text-warning-emphasis': item.registry_status === 'draft' }"
                  >
                    {{ LABELS.registryStatus[item.registry_status] }}
                    <template v-if="item.registry_level"> · {{ item.registry_level }}</template>
                  </span>
                  <span v-else class="text-body-secondary">—</span>
                </td>
                <td>
                  <div class="d-flex justify-content-end gap-2">
                    <RouterLink
                      v-if="item.status === 'published'"
                      class="btn btn-sm btn-outline-secondary"
                      :to="{ name: 'olympiad', params: { slug: item.slug } }"
                      title="Открыть в каталоге"
                    >
                      Открыть
                    </RouterLink>
                    <RouterLink
                      class="btn btn-sm btn-outline-primary"
                      :to="{ name: 'admin-edit', params: { slug: item.slug } }"
                    >
                      Изменить
                    </RouterLink>
                    <button
                      type="button"
                      class="btn btn-sm btn-outline-danger"
                      :disabled="deletingSlug === item.slug"
                      @click="remove(item)"
                    >
                      {{ deletingSlug === item.slug ? 'Удаляем…' : 'Удалить' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!filteredItems.length">
                <td colspan="5" class="text-center text-body-secondary py-5">
                  {{ items.length ? 'По запросу ничего не найдено.' : 'Записей пока нет.' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
