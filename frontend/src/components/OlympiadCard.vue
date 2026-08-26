<script setup>
import { computed } from 'vue'
import DataStatusBadge from './DataStatusBadge.vue'
import {
  LABELS,
  admissionYearLabel,
  benefitDisplayType,
  benefitHasRight,
  formatStageDate,
  gradesLabel,
} from '../utils/format'

const props = defineProps({
  olympiad: { type: Object, required: true },
  activeBenefitType: { type: String, default: '' },
  activeUniversity: { type: String, default: '' },
  authenticated: { type: Boolean, default: false },
  inPlan: { type: Boolean, default: false },
  addingToPlan: { type: Boolean, default: false },
})
const emit = defineEmits(['add-to-plan'])

function selectionRank(benefit) {
  const typeMatch = Boolean(props.activeBenefitType)
    && benefitHasRight(benefit, props.activeBenefitType)
  const universityMatch = Boolean(props.activeUniversity)
    && benefit.university?.slug === props.activeUniversity

  if (props.activeBenefitType && props.activeUniversity) {
    if (typeMatch && universityMatch) return 4
    if (universityMatch) return 2
    if (typeMatch) return 1
    return 0
  }
  if (universityMatch || typeMatch) return 2
  return 0
}

const benefitSummary = computed(() => {
  const seen = new Set()
  return (Array.isArray(props.olympiad.benefit_summary)
    ? props.olympiad.benefit_summary
    : [])
    .filter((benefit) => (
      LABELS.benefitFilterType[benefit?.benefit_type]
      && (
        !benefit.university
        || (benefit.university.slug && (benefit.university.short_name || benefit.university.name))
      )
    ))
    .filter((benefit) => {
      const key = [
        benefit.benefit_type,
        benefit.has_bvi ?? 'legacy-bvi',
        benefit.has_hundred_points ?? 'legacy-100',
        benefit.university?.slug || 'general',
        benefit.admission_year || 'any-year',
      ].join(':')
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .map((benefit, index) => ({ benefit, index, rank: selectionRank(benefit) }))
    .sort((left, right) => right.rank - left.rank || left.index - right.index)
    .map(({ benefit }) => benefit)
})

const visibleBenefits = computed(() => benefitSummary.value.slice(0, 2))
const hiddenBenefitCount = computed(() => Math.max(benefitSummary.value.length - 2, 0))

function universityLabel(benefit) {
  if (benefit.university) return benefit.university.short_name || benefit.university.name
  return benefitHasRight(benefit, 'bvi') ? 'общее право' : ''
}

function benefitBadgeLabel(benefit) {
  const parts = [benefitDisplayType(benefit)]
  const university = universityLabel(benefit)
  const admissionYear = admissionYearLabel(benefit, true)
  if (university) parts.push(university)
  if (admissionYear) parts.push(admissionYear)
  return parts.join(' · ')
}
</script>

<template>
  <article class="card olympiad-card h-100 border-0 shadow-sm">
    <div class="card-body d-flex flex-column p-4">
      <button
        v-if="authenticated"
        type="button"
        class="btn olympiad-card-plan-action"
        :class="inPlan ? 'is-added' : 'btn-outline-primary'"
        :disabled="inPlan || addingToPlan"
        :aria-label="inPlan ? 'Олимпиада уже в вашем плане' : 'Добавить олимпиаду в мой план'"
        :title="inPlan ? 'Уже в плане' : 'Добавить в план'"
        @click.stop="emit('add-to-plan')"
      >
        <i
          class="fa-solid"
          :class="addingToPlan ? 'fa-spinner fa-spin' : inPlan ? 'fa-check' : 'fa-plus'"
          aria-hidden="true"
        ></i>
      </button>

      <div class="d-flex flex-wrap gap-2 mb-3" :class="{ 'pe-5': authenticated }">
        <span v-if="olympiad.is_popular" class="badge badge-popular">Популярная</span>
        <span
          v-if="olympiad.registry_status && olympiad.registry_status !== 'not_listed'"
          class="badge"
          :class="olympiad.registry_status === 'approved' ? 'text-bg-primary' : 'badge-registry-pending'"
        >
          {{ LABELS.registryStatus[olympiad.registry_status] }}
          <span v-if="olympiad.registry_level"> · {{ olympiad.registry_level }} уровень</span>
        </span>
        <span v-if="olympiad.is_team" class="badge text-bg-info">Командная</span>
        <span
          v-if="['open', 'announced'].includes(olympiad.registration_status)"
          class="badge"
          :class="olympiad.registration_status === 'open' ? 'text-bg-success' : 'text-bg-warning'"
        >
          <i class="fa-solid fa-pen-to-square me-1" aria-hidden="true"></i>
          {{ LABELS.registrationStatus[olympiad.registration_status] }}
        </span>
        <span v-if="olympiad.cycle_label" class="badge text-bg-secondary badge-cycle">
          <i class="fa-solid fa-calendar-days me-1" aria-hidden="true"></i>
          {{ olympiad.cycle_label }}
        </span>
      </div>

      <p class="eyebrow mb-2">{{ olympiad.profile }}</p>
      <h2 class="h5 card-title">
        <RouterLink
          class="stretched-link text-decoration-none"
          :to="{ name: 'olympiad', params: { slug: olympiad.slug } }"
        >
          {{ olympiad.name }}
        </RouterLink>
      </h2>

      <p v-if="olympiad.description" class="card-description text-body-secondary mb-3">
        {{ olympiad.description }}
      </p>

      <div
        v-if="benefitSummary.length"
        class="olympiad-card-benefits mb-3"
        aria-label="Подтверждённые льготы и награды"
      >
        <p class="small fw-semibold mb-2">
          <i class="fa-solid fa-building-columns me-1" aria-hidden="true"></i>
          Льготы и награды
        </p>
        <div class="d-flex flex-wrap gap-1">
          <span
            v-for="benefit in visibleBenefits"
            :key="[
              benefit.benefit_type,
              benefit.has_bvi ?? 'legacy-bvi',
              benefit.has_hundred_points ?? 'legacy-100',
              benefit.university?.slug || 'general',
              benefit.admission_year || 'any-year',
            ].join(':')"
            class="benefit-summary-badge"
          >
            {{ benefitBadgeLabel(benefit) }}
          </span>
          <span v-if="hiddenBenefitCount" class="benefit-summary-more">
            ещё {{ hiddenBenefitCount }}
          </span>
        </div>
      </div>

      <dl class="compact-facts mb-4">
        <div>
          <dt>{{ olympiad.grades?.length ? 'Классы' : olympiad.eligibility_notes ? 'Кто может участвовать' : 'Классы' }}</dt>
          <dd>
            {{ olympiad.grades?.length
              ? gradesLabel(olympiad.grades)
              : olympiad.eligibility_notes || gradesLabel(olympiad.grades) }}
          </dd>
        </div>
        <div>
          <dt>География</dt>
          <dd>{{ LABELS.geography[olympiad.geography] || olympiad.geography }}</dd>
        </div>
        <div v-if="olympiad.participant_count !== undefined">
          <dt>В планах</dt>
          <dd>
            <i class="fa-solid fa-users me-1 text-primary" aria-hidden="true"></i>
            {{ olympiad.participant_count }}
          </dd>
        </div>
      </dl>

      <div class="mt-auto pt-3 border-top position-relative olympiad-card-stage">
        <template v-if="olympiad.next_stage">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
            <span class="small fw-semibold">{{ olympiad.next_stage.name }}</span>
            <span class="small text-body-secondary text-nowrap">
              {{ LABELS.format[olympiad.next_stage.format] }}
            </span>
          </div>
          <p class="mb-2 fw-semibold">
            {{ formatStageDate(olympiad.next_stage, true) }}
          </p>
          <DataStatusBadge :stage="olympiad.next_stage" :data-status="olympiad.data_status" />
        </template>
        <template
          v-else-if="olympiad.stages_count > 0 && olympiad.data_status === 'previous_year_estimate'"
        >
          <span class="status-badge status-estimate">
            <i class="fa-solid fa-clock-rotate-left status-icon" aria-hidden="true"></i>
            Даты нового сезона уточняются
          </span>
        </template>
        <template v-else-if="olympiad.stages_count > 0">
          <span class="status-badge status-completed">
            <i class="fa-solid fa-circle-check status-icon" aria-hidden="true"></i>
            Этапы завершены
          </span>
        </template>
        <template v-else>
          <DataStatusBadge :stage="null" :data-status="olympiad.data_status" />
        </template>
      </div>
    </div>
  </article>
</template>
