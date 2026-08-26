const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const MONTH_RE = /^(\d{4})-(0[1-9]|1[0-2])$/

const MONTH_LABEL_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

function pad(value) {
  return String(value).padStart(2, '0')
}

function utcDate(value) {
  if (!ISO_DATE_RE.test(value || '')) return null
  const date = new Date(value + 'T00:00:00Z')
  return Number.isNaN(date.getTime()) ? null : date
}

function isoDate(date) {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`
}

function addDays(date, amount) {
  const result = new Date(date)
  result.setUTCDate(result.getUTCDate() + amount)
  return result
}

export function isValidMonthKey(value) {
  return MONTH_RE.test(value || '')
}

export function monthKeyFromDate(date = new Date()) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`
}

export function dateKeyFromDate(date = new Date()) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function shiftMonthKey(month, amount) {
  if (!isValidMonthKey(month)) return monthKeyFromDate()
  const [year, monthNumber] = month.split('-').map(Number)
  const date = new Date(Date.UTC(year, monthNumber - 1 + amount, 1))
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}`
}

export function formatMonthLabel(month) {
  if (!isValidMonthKey(month)) return ''
  const [year, monthNumber] = month.split('-').map(Number)
  const label = MONTH_LABEL_FORMATTER.format(new Date(Date.UTC(year, monthNumber - 1, 1)))
  return label.charAt(0).toLocaleUpperCase('ru-RU') + label.slice(1)
}

export function monthBounds(month) {
  if (!isValidMonthKey(month)) return null
  const [year, monthNumber] = month.split('-').map(Number)
  const startsOn = new Date(Date.UTC(year, monthNumber - 1, 1))
  const endsOn = new Date(Date.UTC(year, monthNumber, 0))
  return { startsOn: isoDate(startsOn), endsOn: isoDate(endsOn) }
}

export function normalizeCalendarEvents(records = []) {
  return records
    .map((record, index) => {
      const olympiad = record.olympiad || {}
      const stage = record.stage || {}
      const startsOn = stage.starts_on || stage.ends_on
      const endsOn = stage.ends_on || stage.starts_on
      if (!utcDate(startsOn) || !utcDate(endsOn) || endsOn < startsOn) return null

      const isConfirmed =
        stage.is_date_confirmed === true &&
        olympiad.data_status !== 'previous_year_estimate'
      const hasApproximatePrecision = ['approximate', 'month'].includes(stage.date_precision)

      return {
        id: String(record.id ?? stage.id ?? `${olympiad.slug || 'event'}-${index}`),
        olympiadSlug: olympiad.slug || '',
        olympiadName: olympiad.name || olympiad.family_name || 'Олимпиада',
        familyName: olympiad.family_name || olympiad.name || 'Олимпиада',
        profile: olympiad.profile || '',
        cycleLabel: olympiad.cycle_label || '',
        stageName: stage.name || 'Этап',
        startsOn,
        endsOn,
        isDeadline: !stage.starts_on && Boolean(stage.ends_on),
        isRange: startsOn !== endsOn,
        confidence: isConfirmed ? 'confirmed' : 'estimate',
        displayStatus: isConfirmed && !hasApproximatePrecision ? 'confirmed' : 'estimate',
        previousYearEstimate: olympiad.data_status === 'previous_year_estimate',
        datePrecision: stage.date_precision || 'tba',
        format: stage.format || 'unknown',
        raw: record,
      }
    })
    .filter(Boolean)
    .sort((left, right) =>
      left.startsOn.localeCompare(right.startsOn) ||
      left.endsOn.localeCompare(right.endsOn) ||
      left.olympiadName.localeCompare(right.olympiadName, 'ru'),
    )
}

export function groupCalendarEvents(events = []) {
  const groups = new Map()

  for (const event of events) {
    const key = [
      event.familyName,
      event.stageName,
      event.cycleLabel,
      event.startsOn,
      event.endsOn,
      event.isDeadline ? 'deadline' : 'event',
    ].join('\u0000')
    let group = groups.get(key)
    if (!group) {
      group = {
        ...event,
        id: key,
        olympiadName: event.familyName,
        profiles: [],
      }
      groups.set(key, group)
    }

    if (!group.profiles.some((profile) => profile.slug === event.olympiadSlug)) {
      group.profiles.push({
        slug: event.olympiadSlug,
        name: event.olympiadName,
        profile: event.profile,
      })
    }
    if (event.confidence === 'estimate') group.confidence = 'estimate'
    if (event.displayStatus === 'estimate') group.displayStatus = 'estimate'
    if (event.previousYearEstimate) group.previousYearEstimate = true
  }

  return [...groups.values()]
    .map((group) => ({
      ...group,
      olympiadSlug: group.profiles[0]?.slug || group.olympiadSlug,
      profiles: group.profiles.sort((left, right) =>
        (left.profile || left.name).localeCompare(right.profile || right.name, 'ru'),
      ),
    }))
    .sort((left, right) =>
      left.startsOn.localeCompare(right.startsOn) ||
      left.endsOn.localeCompare(right.endsOn) ||
      left.olympiadName.localeCompare(right.olympiadName, 'ru'),
    )
}

export function eventsOverlappingMonth(month, events) {
  const bounds = monthBounds(month)
  if (!bounds) return []
  return events.filter(
    (event) => event.startsOn <= bounds.endsOn && event.endsOn >= bounds.startsOn,
  )
}

export function buildMonthDays(month, events = [], today = dateKeyFromDate()) {
  const bounds = monthBounds(month)
  if (!bounds) return []

  const first = utcDate(bounds.startsOn)
  const last = utcDate(bounds.endsOn)
  const firstWeekday = (first.getUTCDay() + 6) % 7
  const lastWeekday = (last.getUTCDay() + 6) % 7
  const gridStart = addDays(first, -firstWeekday)
  const gridEnd = addDays(last, 6 - lastWeekday)
  const relevantEvents = eventsOverlappingMonth(month, events)
  const days = []

  for (let date = gridStart; date <= gridEnd; date = addDays(date, 1)) {
    const value = isoDate(date)
    const weekday = (date.getUTCDay() + 6) % 7
    const dayEvents = relevantEvents
      .filter((event) => event.startsOn <= value && event.endsOn >= value)
      .map((event) => {
        const segmentStarts = event.startsOn === value || weekday === 0 || value === isoDate(gridStart)
        const segmentEnds = event.endsOn === value || weekday === 6 || value === isoDate(gridEnd)
        return { ...event, segmentStarts, segmentEnds, showLabel: segmentStarts }
      })

    days.push({
      date: value,
      dayNumber: date.getUTCDate(),
      weekday,
      inMonth: value.slice(0, 7) === month,
      isToday: value === today,
      events: dayEvents,
    })
  }

  return days
}
