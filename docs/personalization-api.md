# Авторизация и личный календарь

Каталог, карточки олимпиад, календарь и публичная статистика доступны без входа.
Изменение класса, личного плана и результатов требует сессии ЛК «Силаэдр» и
заголовка `X-CSRF-Token`.

## Настройка OIDC

Backend использует Authlib, discovery, Authorization Code, `state`, `nonce` и
PKCE `S256`. Для production задаются:

```dotenv
REDIS_URL=redis://redis:6379/2
APP_BASE_URL=https://olympiads.example.ru
FRONTEND_BASE_URL=https://olympiads.example.ru
CRM_OIDC_ISSUER=https://lk.silaeder.ru
CRM_OIDC_CLIENT_ID=olympiads
CRM_OIDC_CLIENT_SECRET=...
CRM_OIDC_SCOPES=openid profile email roles
SESSION_COOKIE_SECURE=true
```

В OIDC-клиенте CRM регистрируются точные адреса:

```text
https://olympiads.example.ru/auth/crm/callback
https://olympiads.example.ru/auth/crm/logout/callback
```

Локальная личность связывается только по уникальной паре `(issuer, sub)`. Email,
роль и имя синхронизируются при входе, а локальный класс сохраняется отдельно,
поскольку CRM его не возвращает. Токены не передаются Vue; сессии хранятся в Redis.

## Auth и профиль

- `GET /api/v1/auth/session` — всегда `200`; возвращает `authenticated`, `user`,
  `csrf_token` и `login_url`.
- `GET /api/v1/auth/login?next=/relative/path` — перенаправляет в CRM. Внешние и
  protocol-relative значения `next` отклоняются.
- `GET /auth/crm/callback` — OIDC callback и переход на безопасный `next`.
- `POST /api/v1/auth/logout` — требует сессию и CSRF; возвращает `logout_url` для
  перехода на RP-Initiated Logout CRM.
- `GET /api/v1/me` — локальный профиль.
- `PATCH /api/v1/me` с `{"grade": 5..11 | null}` — меняет класс.

Ответ авторизованной сессии:

```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "name": "Иван Иванов",
    "email": "ivan@example.ru",
    "preferred_username": "ivan",
    "role": "student",
    "object_type": "students",
    "grade": 9
  },
  "csrf_token": "...",
  "login_url": "/api/v1/auth/login"
}
```

## Личный план

- `GET /api/v1/me/plan?academic_year=2026/27` — все записи плана и ближайшие
  датированные этапы. Собственные архивные планы также входят в `items` с
  `edition_status=archived`, но не входят в `upcoming_stages`.
- `GET /api/v1/olympiads/{slug}/planning?academic_year=2026/27` — публичный
  `participant_count`, добровольно опубликованные имена и `plan` текущего
  пользователя либо `null`.
- `POST /api/v1/olympiads/{slug}/planning` — добавить, ответ `201`.
- `PATCH /api/v1/olympiads/{slug}/planning` — изменить настройки.
- `DELETE /api/v1/olympiads/{slug}/planning` — удалить план и его прогресс.

Поля записи плана:

```json
{
  "status": "planned",
  "is_name_public": false,
  "reminders_enabled": true,
  "reminder_days_before": [7, 1]
}
```

`status`: `planned`, `registered`, `participating` или `completed`. Имя по
умолчанию скрыто. Пустой список дней допустим только при выключенных напоминаниях.
`edition_status` имеет значение `published` или `archived`. Новую архивную
карточку добавить нельзя, а её публичные detail/planning endpoints возвращают
`404`; уже существующий собственный архивный план разрешено изменить или удалить,
чтобы отозвать публикацию имени и очистить сохранённые результаты.

## Прогресс этапа

- `PUT /api/v1/olympiads/{slug}/stages/{stage_id}/progress` — создать или заменить
  отметку.
- `DELETE /api/v1/olympiads/{slug}/stages/{stage_id}/progress` — сбросить отметку.

```json
{
  "participated": true,
  "advanced": true,
  "result": "Диплом II степени"
}
```

Если `participated=false`, backend канонически сбрасывает `advanced` и `result` в
`null`. У этапов есть стабильный `key`: повторный импорт сопоставляет этапы по нему,
а исчезнувшие из источника этапы архивируются вместо удаления. Поэтому вставка или
перестановка этапов не переносит и не стирает пользовательские результаты.

Все state-changing endpoints сначала возвращают `401` анонимному клиенту. Для
авторизованного клиента отсутствующий или неверный CSRF-токен даёт `403`.
