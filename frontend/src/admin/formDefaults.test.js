import { describe, expect, it } from 'vitest'
import { emptyOlympiad, olympiadFromApi, payloadFromForm, slugify } from './formDefaults'

describe('данные административной формы', () => {
  it('транслитерирует читаемый slug', () => {
    expect(slugify('Высшая проба — Математика')).toBe('vysshaya-proba-matematika')
  })

  it('сохраняет отдельный статус проекта перечня и допускает неизвестные классы', () => {
    const form = emptyOlympiad()
    Object.assign(form, {
      slug: 'test-math',
      name: 'Тест — Математика',
      family_name: 'Тест',
      profile: 'Математика',
      website_url: 'https://example.test',
      registry_status: 'draft',
      is_in_registry: true,
      registry_level: 1,
      updated_at: '2026-08-25T18:30:00+00:00',
      grades: [],
      eligibility_notes: '  Учащиеся музыкальных школ  ',
    })
    const payload = payloadFromForm(form)
    expect(payload.registry_status).toBe('draft')
    expect(payload.registry_level).toBe(1)
    expect(payload.updated_at).toBe('2026-08-25T18:30:00+00:00')
    expect(payload.grades).toEqual([])
    expect(payload.eligibility_notes).toBe('Учащиеся музыкальных школ')
  })

  it('загружает текстовые условия участия и отправляет null для пустого значения', () => {
    const populated = olympiadFromApi({
      ...emptyOlympiad(),
      eligibility_notes: 'Участники до 18 лет',
    })
    expect(populated.eligibility_notes).toBe('Участники до 18 лет')
    expect(payloadFromForm(populated).eligibility_notes).toBe('Участники до 18 лет')

    expect(payloadFromForm(emptyOlympiad()).eligibility_notes).toBeNull()
  })

  it('сохраняет необязательную метку календарного цикла отдельно от учебного года', () => {
    const populated = olympiadFromApi({
      ...emptyOlympiad(),
      academic_year: '2026/27',
      cycle_label: 'Календарный цикл 2026',
    })

    const payload = payloadFromForm(populated)
    expect(payload.academic_year).toBe('2026/27')
    expect(payload.cycle_label).toBe('Календарный цикл 2026')
    expect(payloadFromForm(emptyOlympiad()).cycle_label).toBeNull()
  })

  it('сохраняет срок регистрации как timezone-aware ISO строку при редактировании', () => {
    const closesAt = '2026-08-26T11:50:00+03:00'
    const populated = olympiadFromApi({
      ...emptyOlympiad(),
      registration_closes_at: closesAt,
    })

    expect(populated.registration_closes_at).toBe(closesAt)
    expect(payloadFromForm(populated).registration_closes_at).toBe(closesAt)
    expect(payloadFromForm(emptyOlympiad()).registration_closes_at).toBeNull()
  })

  it('сохраняет результат и дату ручной проверки регистрации', () => {
    const populated = olympiadFromApi({
      ...emptyOlympiad(),
      registration_status: 'announced',
      registration_checked_on: '2026-08-26',
    })

    const payload = payloadFromForm(populated)
    expect(payload.registration_status).toBe('announced')
    expect(payload.registration_checked_on).toBe('2026-08-26')
    expect(payloadFromForm(emptyOlympiad()).registration_checked_on).toBeNull()
  })

  it('нормализует null в данных вуза перед повторным сохранением', () => {
    const apiItem = {
      ...emptyOlympiad(),
      slug: 'test-math',
      name: 'Тест — Математика',
      family_name: 'Тест',
      profile: 'Математика',
      website_url: 'https://example.test',
      benefits: [
        {
          title: 'БВИ',
          benefit_type: 'bvi',
          university: {
            slug: 'test-university',
            name: 'Тестовый университет',
            short_name: null,
            website_url: null,
          },
        },
      ],
    }
    const payload = payloadFromForm(olympiadFromApi(apiItem))
    expect(payload.benefits[0].university.short_name).toBeNull()
    expect(payload.benefits[0].university.website_url).toBeNull()
    expect(payload.benefits[0].has_bvi).toBe(true)
    expect(payload.benefits[0].has_hundred_points).toBe(false)
  })

  it('сохраняет оба подтверждённых права у mixed-записи', () => {
    const populated = olympiadFromApi({
      ...emptyOlympiad(),
      benefits: [{
        benefit_type: 'other',
        has_bvi: true,
        has_hundred_points: true,
        title: 'БВИ или 100 баллов',
        university: null,
      }],
    })

    expect(populated.benefits[0]).toMatchObject({
      benefit_type: 'other',
      has_bvi: true,
      has_hundred_points: true,
    })
    expect(payloadFromForm(populated).benefits[0]).toMatchObject({
      benefit_type: 'other',
      has_bvi: true,
      has_hundred_points: true,
    })
  })

  it('не отправляет admission_year приза как будто это год приёма', () => {
    const form = emptyOlympiad()
    form.benefits = [{
      ...olympiadFromApi({ benefits: [{
        benefit_type: 'prize',
        admission_year: 2025,
        title: 'Награда',
      }] }).benefits[0],
    }]

    expect(payloadFromForm(form).benefits[0].admission_year).toBeNull()
  })

  it('не позволяет типам БВИ и 100 баллов потерять обязательный флаг', () => {
    const form = emptyOlympiad()
    form.benefits = [
      { ...form.benefits[0], ...olympiadFromApi({ benefits: [{
        benefit_type: 'bvi',
        has_bvi: false,
        title: 'БВИ',
      }] }).benefits[0] },
      olympiadFromApi({ benefits: [{
        benefit_type: 'hundred_points',
        has_hundred_points: false,
        title: '100 баллов',
      }] }).benefits[0],
    ]

    const payload = payloadFromForm(form)
    expect(payload.benefits[0].has_bvi).toBe(true)
    expect(payload.benefits[1].has_hundred_points).toBe(true)
  })
})
