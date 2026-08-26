# Покрытие каталога регистрациями

Срез проверен **26 августа 2026 года** для учебного года **2026/27**. Все 357
карточки каталога имеют зафиксированный результат ручной проверки на первичном
сайте организатора:

| Статус исследования | Карточек | Что видит пользователь |
|---|---:|---|
| `open` | 50 | Кнопку «Перейти к регистрации» |
| `announced` | 29 | Только официальный сайт; форма ещё не считается открытой |
| `not_open` | 58 | Только официальный сайт |
| `not_found` | 220 | Только официальный сайт |

В seed переносятся все 357 результатов проверки и дата среза, но URL кнопки —
только для 50 значений со статусом `open`. Это семь уникальных действующих
маршрутов:

- 21 профиль НТО — [предварительная регистрация сезона 2026/27](https://talent.kruzhok.org/registration?event=10334);
- 24 обычных профиля «Высшей пробы» — [кабинет участника](https://myolymp.hse.ru/school.html);
- «Промышленное программирование» «Высшей пробы» — [профильная форма 26/27](https://olympiads.lms.yandex.ru/new-candidate/admission-devcode-26-27);
- олимпиада по искусственному интеллекту — [All Cups](https://cups.online/ru/contests/vserosii_2026);
- ОПК — [создание учётной записи](https://opk.pravolimp.ru/users/new);
- «Физтех. Старт в науку» — [форма МФТИ](https://start.mipt.ru/signup/);
- Интернет-олимпиада СПбГУ по физике — [анкета участника 2026/27](https://distolymp.spbu.ru/phys/olymp/registration/user/).

Предварительная регистрация НТО была реально открыта во время проверки в
02:46 UTC, но опубликованное окно заканчивается **26.08.2026 в 08:50 UTC**.
Этот момент сохранён в `registration_closes_at`: после него публичный API и
интерфейс автоматически скроют 21 CTA НТО. Статический срез всё равно нужно
обновить при следующей проверке; отчёт не выдаёт моментальное состояние за
бессрочную гарантию.

## Правило публикации

HTTP 200 недостаточен. Общая главная страница, закрытая Google-форма, вход в
кабинет без подтверждённой заявки, форма прошлого цикла и текст «регистрация
скоро» не создают CTA. Для каждого slug сохранены дата проверки, URL
подтверждающей официальной страницы и краткое наблюдаемое обоснование.

Исходные непересекающиеся пакеты:

- [`current_registration_popular.json`](current_registration_popular.json) — 60 карточек ВсОШ и МОШ;
- [`current_registration_confirmed.json`](current_registration_confirmed.json) — 31 карточка с подтверждённым расписанием;
- [`current_registration_lifecycle.json`](current_registration_lifecycle.json) — 42 ранее заполненные ссылки;
- [`current_registration_remaining_a.json`](current_registration_remaining_a.json) — 77 карточек;
- [`current_registration_remaining_b.json`](current_registration_remaining_b.json) — 94 карточки;
- [`current_registration_remaining_c.json`](current_registration_remaining_c.json) — 49 карточек.
- [`current_registration_bmstu_biology.json`](current_registration_bmstu_biology.json) — биологический профиль «Шага в будущее»;
- [`current_registration_bmstu_gazprom.json`](current_registration_bmstu_gazprom.json) — три дополнительных профиля олимпиады «Газпром».

Их множества slug не пересекаются и в сумме равны всем 357 карточкам. Сборщик
завершается ошибкой, если хотя бы одна карточка не получила проверенный статус,
а backend-тест фиксирует точные количества и равенство всех опубликованных CTA
множеству `open`.
