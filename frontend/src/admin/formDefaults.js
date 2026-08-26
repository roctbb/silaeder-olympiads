export const gradeOptions = [5, 6, 7, 8, 9, 10, 11]

export function emptyStage(position = 0) {
  return {
    name: '',
    stage_type: '',
    position,
    starts_on: '',
    ends_on: '',
    registration_opens_on: '',
    registration_closes_on: '',
    date_precision: 'tba',
    is_date_confirmed: false,
    format: 'unknown',
    location: '',
    details: '',
    source_url: '',
  }
}

export function emptyMaterial() {
  return {
    title: '',
    material_type: 'other',
    year: '',
    url: '',
    is_official: true,
  }
}

export function emptyBenefit() {
  return {
    benefit_type: 'other',
    has_bvi: false,
    has_hundred_points: false,
    title: '',
    description: '',
    diploma_requirement: '',
    ege_subject: '',
    ege_min_score: '',
    admission_year: '',
    source_url: '',
    university: {
      slug: '',
      name: '',
      short_name: '',
      website_url: '',
    },
  }
}

export function emptySource() {
  return {
    title: '',
    url: '',
    publisher: '',
    source_type: '',
    source_year: '',
    accessed_on: '',
  }
}

export function emptyOlympiad() {
  return {
    slug: '',
    name: '',
    family_name: '',
    profile: '',
    description: '',
    organizer: '',
    website_url: '',
    logo_url: '',
    geography: 'russia',
    is_team: false,
    academic_year: '2026/27',
    cycle_label: '',
    updated_at: null,
    status: 'draft',
    data_status: 'announcement_pending',
    registry_status: 'not_listed',
    is_in_registry: false,
    registry_level: '',
    is_popular: false,
    registration_status: 'not_found',
    registration_checked_on: '',
    registration_url: '',
    registration_closes_at: '',
    previous_year_reference: '',
    notes: '',
    eligibility_notes: '',
    grades: [],
    stages: [],
    materials: [],
    benefits: [],
    sources: [],
  }
}

function text(value) {
  return value ?? ''
}

export function olympiadFromApi(item) {
  const form = emptyOlympiad()
  for (const key of [
    'slug',
    'name',
    'family_name',
    'profile',
    'description',
    'organizer',
    'website_url',
    'logo_url',
    'geography',
    'is_team',
    'academic_year',
    'cycle_label',
    'updated_at',
    'status',
    'data_status',
    'registry_status',
    'is_in_registry',
    'registry_level',
    'is_popular',
    'registration_status',
    'registration_checked_on',
    'registration_url',
    'registration_closes_at',
    'previous_year_reference',
    'notes',
    'eligibility_notes',
  ]) {
    form[key] = item[key] ?? form[key]
  }
  form.grades = [...(item.grades || [])]
  form.stages = (item.stages || []).map((stage, index) => ({
    ...emptyStage(index),
    ...Object.fromEntries(Object.entries(stage).map(([key, value]) => [key, text(value)])),
    position: stage.position ?? index,
    is_date_confirmed: Boolean(stage.is_date_confirmed),
  }))
  form.materials = (item.materials || []).map((material) => ({
    ...emptyMaterial(),
    ...Object.fromEntries(Object.entries(material).map(([key, value]) => [key, text(value)])),
    is_official: Boolean(material.is_official),
  }))
  form.benefits = (item.benefits || []).map((benefit) => {
    const result = {
      ...emptyBenefit(),
      ...Object.fromEntries(
        Object.entries(benefit)
          .filter(([key]) => key !== 'university')
          .map(([key, value]) => [key, text(value)]),
      ),
      university: {
        ...emptyBenefit().university,
        ...Object.fromEntries(
          Object.entries(benefit.university || {}).map(([key, value]) => [key, text(value)]),
        ),
      },
    }
    result.has_bvi = Boolean(result.has_bvi || result.benefit_type === 'bvi')
    result.has_hundred_points = Boolean(
      result.has_hundred_points || result.benefit_type === 'hundred_points',
    )
    return result
  })
  form.sources = (item.sources || []).map((source) => ({
    ...emptySource(),
    ...Object.fromEntries(Object.entries(source).map(([key, value]) => [key, text(value)])),
  }))
  return form
}

function nullable(value) {
  return value === '' ? null : value
}

export function payloadFromForm(form) {
  return {
    slug: form.slug.trim(),
    name: form.name.trim(),
    family_name: form.family_name.trim(),
    profile: form.profile.trim(),
    description: nullable(form.description.trim()),
    organizer: nullable(form.organizer.trim()),
    website_url: form.website_url.trim(),
    logo_url: nullable(form.logo_url.trim()),
    geography: form.geography,
    is_team: Boolean(form.is_team),
    academic_year: form.academic_year.trim(),
    cycle_label: nullable(form.cycle_label.trim()),
    updated_at: form.updated_at || null,
    status: form.status,
    data_status: form.data_status,
    registry_status: form.registry_status,
    is_in_registry: Boolean(form.is_in_registry),
    registry_level: nullable(form.registry_level),
    is_popular: Boolean(form.is_popular),
    registration_status: form.registration_status,
    registration_checked_on: nullable(form.registration_checked_on),
    registration_url: nullable(form.registration_url.trim()),
    registration_closes_at: nullable(form.registration_closes_at.trim()),
    previous_year_reference: nullable(form.previous_year_reference.trim()),
    notes: nullable(form.notes.trim()),
    eligibility_notes: nullable(form.eligibility_notes.trim()),
    grades: [...form.grades].sort((a, b) => a - b),
    stages: form.stages.map((stage, index) => ({
      name: stage.name.trim(),
      stage_type: nullable(stage.stage_type.trim()),
      position: Number(stage.position ?? index),
      starts_on: nullable(stage.starts_on),
      ends_on: nullable(stage.ends_on),
      registration_opens_on: nullable(stage.registration_opens_on),
      registration_closes_on: nullable(stage.registration_closes_on),
      date_precision: stage.date_precision,
      is_date_confirmed: Boolean(stage.is_date_confirmed),
      format: stage.format,
      location: nullable(stage.location.trim()),
      details: nullable(stage.details.trim()),
      source_url: nullable(stage.source_url.trim()),
    })),
    materials: form.materials.map((material) => ({
      title: material.title.trim(),
      material_type: material.material_type,
      year: nullable(material.year),
      url: material.url.trim(),
      is_official: Boolean(material.is_official),
    })),
    benefits: form.benefits.map((benefit) => {
      const result = {
        benefit_type: benefit.benefit_type,
        has_bvi: Boolean(benefit.has_bvi || benefit.benefit_type === 'bvi'),
        has_hundred_points: Boolean(
          benefit.has_hundred_points || benefit.benefit_type === 'hundred_points'
        ),
        title: benefit.title.trim(),
        description: nullable(benefit.description.trim()),
        diploma_requirement: nullable(benefit.diploma_requirement.trim()),
        ege_subject: nullable(benefit.ege_subject.trim()),
        ege_min_score: nullable(benefit.ege_min_score),
        admission_year: benefit.benefit_type === 'prize'
          ? null
          : nullable(benefit.admission_year),
        source_url: nullable(benefit.source_url.trim()),
      }
      if (benefit.university.name.trim() || benefit.university.slug.trim()) {
        result.university = {
          slug: benefit.university.slug.trim(),
          name: benefit.university.name.trim(),
          short_name: nullable(benefit.university.short_name.trim()),
          website_url: nullable(benefit.university.website_url.trim()),
        }
      }
      return result
    }),
    sources: form.sources.map((source) => ({
      title: source.title.trim(),
      url: source.url.trim(),
      publisher: nullable(source.publisher.trim()),
      source_type: nullable(source.source_type.trim()),
      source_year: nullable(source.source_year.trim()),
      accessed_on: nullable(source.accessed_on),
    })),
  }
}

export function slugify(value) {
  const map = {
    а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z',
    и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r',
    с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'ts', ч: 'ch', ш: 'sh',
    щ: 'sch', ы: 'y', э: 'e', ю: 'yu', я: 'ya',
  }
  return value
    .toLowerCase()
    .split('')
    .map((char) => map[char] || char)
    .join('')
    .replace(/ъ|ь/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 180)
}
