const DATE_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

const SHORT_DATE_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})

const MONTH_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

const SHORT_MONTH_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

function parseIsoDate(value) {
  return value ? new Date(value + 'T00:00:00Z') : null
}

export function formatDate(value, short = false) {
  const date = parseIsoDate(value)
  if (!date || Number.isNaN(date.getTime())) return 'Дата уточняется'
  return (short ? SHORT_DATE_FORMATTER : DATE_FORMATTER).format(date)
}

export function formatDateRange(start, end, short = false) {
  if (!start && !end) return 'Дата уточняется'
  if (!start) return 'до ' + formatDate(end, short)
  if (!end || start === end) return formatDate(start, short)
  return formatDate(start, short) + ' — ' + formatDate(end, short)
}

export function formatStageDate(stage, short = false) {
  if (
    !stage ||
    stage.date_precision === 'tba' ||
    (!stage.starts_on && !stage.ends_on)
  ) {
    return 'Дата уточняется'
  }
  if (stage.date_precision === 'month') {
    const formatter = short ? SHORT_MONTH_FORMATTER : MONTH_FORMATTER
    const start = parseIsoDate(stage.starts_on || stage.ends_on)
    const end = parseIsoDate(stage.ends_on)
    if (!start) return 'Дата уточняется'
    const startLabel = formatter.format(start)
    if (!end || start.getUTCFullYear() === end.getUTCFullYear() && start.getUTCMonth() === end.getUTCMonth()) {
      return startLabel
    }
    return startLabel + ' — ' + formatter.format(end)
  }
  const value = formatDateRange(stage.starts_on, stage.ends_on, short)
  return stage.date_precision === 'approximate' ? 'примерно ' + value : value
}

export function gradesLabel(grades = []) {
  if (!grades.length) return 'Классы уточняются'
  const sorted = [...grades].sort((a, b) => a - b)
  const continuous = sorted.every((grade, index) => index === 0 || grade === sorted[index - 1] + 1)
  if (continuous && sorted.length > 2) {
    return sorted[0] + '–' + sorted.at(-1) + ' классы'
  }
  return sorted.join(', ') + (sorted.length === 1 ? ' класс' : ' классы')
}

export function pluralize(count, one, few, many) {
  const absolute = Math.abs(Number(count)) % 100
  const last = absolute % 10
  if (absolute > 10 && absolute < 20) return many
  if (last === 1) return one
  if (last >= 2 && last <= 4) return few
  return many
}

const UNIVERSITY_ADMISSION_BENEFIT_TYPES = new Set(['bvi', 'hundred_points', 'other'])

export function benefitHasRight(benefit, benefitType) {
  if (benefitType === 'bvi') {
    return benefit?.has_bvi === true
      || (benefit?.has_bvi == null && benefit?.benefit_type === 'bvi')
  }
  if (benefitType === 'hundred_points') {
    return benefit?.has_hundred_points === true
      || (benefit?.has_hundred_points == null && benefit?.benefit_type === 'hundred_points')
  }
  return benefit?.benefit_type === benefitType
}

export function benefitDisplayType(benefit) {
  const rights = []
  if (benefitHasRight(benefit, 'bvi')) rights.push('БВИ')
  if (benefitHasRight(benefit, 'hundred_points')) rights.push('100 баллов')
  if (rights.length) return rights.join(' / ')
  return LABELS.benefitFilterType[benefit?.benefit_type]
    || LABELS.benefitType[benefit?.benefit_type]
    || ''
}

export function admissionYearLabel(benefit, lowercase = false) {
  if (
    !benefit?.admission_year
    || !benefit.university
    || !UNIVERSITY_ADMISSION_BENEFIT_TYPES.has(benefit.benefit_type)
  ) {
    return ''
  }
  return `${lowercase ? 'приём' : 'Приём'} ${benefit.admission_year}`
}

export const LABELS = {
  geography: {
    russia: 'Россия',
    moscow: 'Москва',
    russia_moscow: 'Россия и Москва',
  },
  format: {
    online: 'Онлайн',
    offline: 'Очно',
    hybrid: 'Гибридный формат',
    unknown: 'Формат уточняется',
  },
  materialType: {
    tasks: 'Задания',
    solutions: 'Решения',
    video: 'Видео',
    course: 'Курс',
    archive: 'Архив',
    other: 'Материал',
  },
  benefitType: {
    bvi: 'БВИ',
    hundred_points: '100 баллов',
    grant: 'Грант',
    prize: 'Приз',
    other: 'Информация',
  },
  benefitFilterType: {
    bvi: 'Есть вариант БВИ',
    hundred_points: 'Есть вариант 100 баллов',
    other: 'Иные условия',
    prize: 'Призы',
  },
  editionStatus: {
    draft: 'Черновик',
    published: 'Опубликовано',
    archived: 'В архиве',
  },
  dataStatus: {
    confirmed: 'Расписание подтверждено',
    partial: 'Данные подтверждены частично',
    previous_year_estimate: 'Ориентир по прошлому году',
    announcement_pending: 'Ожидается объявление',
  },
  registryStatus: {
    approved: 'В перечне',
    draft: 'Проект перечня',
    previous_year: 'По перечню прошлого года',
    not_listed: 'Не в перечне',
  },
  registrationStatus: {
    open: 'Регистрация открыта',
    announced: 'Регистрация анонсирована',
    not_open: 'Регистрация пока закрыта',
    not_found: 'Регистрация не опубликована',
  },
}

export function dateConfidence(stage, dataStatus) {
  if (
    !stage ||
    stage.date_precision === 'tba' ||
    (!stage.starts_on && !stage.ends_on)
  ) {
    return 'tba'
  }
  if (stage.is_date_confirmed) return 'confirmed'
  if (dataStatus === 'previous_year_estimate') {
    return 'previous_year_estimate'
  }
  return 'tba'
}
