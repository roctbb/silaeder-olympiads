# Локальный аудит интеграции с ЛК «Силаэдр»

Дата аудита: 2026-08-25. Аудит выполнен только чтением соседних проектов; их файлы не изменялись. Рабочие секреты из `.env` не читались.

## Краткий вывод

- ЛК уже является полноценным OpenID Connect Provider. Для будущего Flask-сервиса подходит стандартный `Authorization Code Flow` через Authlib с обязательными `state`, `nonce` и PKCE `S256`.
- ЛК уже предоставляет отдельный API внешних уведомлений. Он принимает по одному получателю, использует HTTP Basic с теми же `client_id`/`client_secret`, что и конфиденциальный OIDC-клиент, и требует `Idempotency-Key`.
- `CodingProjects` содержит рабочий пример OIDC-клиента, но написанный вручную для Laravel/PHP. Его полезно использовать как эталон поведения и тестов, а во Flask лучше следовать готовому примеру Authlib из документации `school-crm`.
- Готового внешнего клиента отправки уведомлений в просмотренных проектах нет: найдены серверная реализация, тесты и Python-пример в документации CRM.
- В текущем OIDC `userinfo` нет класса или года обучения. `profile` возвращает только имя и безопасный минимум CRM-объекта. Для фильтрации по классу потребуется локальное поле либо отдельное расширение CRM.

## Найденные проекты

### `school-crm`

Корень: `/Users/roctbb/PycharmProjects/school-crm`

Главные источники:

- `/Users/roctbb/PycharmProjects/school-crm/docs/oidc-integration.md` — самодостаточная инструкция по OIDC и пример Flask/Authlib.
- `/Users/roctbb/PycharmProjects/school-crm/docs/external-notifications-api.md` — контракт внешнего API уведомлений.
- `/Users/roctbb/PycharmProjects/school-crm/docs/notifications-integration.md` — настройка Telegram и краткое описание внешней интеграции.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/blueprints/oidc_blueprint.py` — discovery и OIDC endpoints.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/oidc.py` — выпуск/проверка токенов и состав claims.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/methods/oidc_methods.py` — клиенты, redirect URI, scopes, роли, согласия и PKCE.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/blueprints/notifications_blueprint.py` — HTTP endpoint внешних уведомлений.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/validators/notifications.py` — точные ограничения запроса.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/methods/notification_methods.py` — авторизация клиента, поиск получателя и идемпотентность.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/tasks/notifications.py` — фактическая доставка через email и Telegram.
- `/Users/roctbb/PycharmProjects/school-crm/backend/application/models/models.py` — модели `User`, `Object`, `OAuthClient`, `Notification`.
- `/Users/roctbb/PycharmProjects/school-crm/backend/tests/test_oidc.py` и `test_notifications.py` — проверка контрактов.

### `CodingProjects`

Корень: `/Users/roctbb/PhpstormProjects/CodingProjects`

Главные источники:

- `/Users/roctbb/PhpstormProjects/CodingProjects/docs/silaeder-oidc.md` — настройка интеграции.
- `/Users/roctbb/PhpstormProjects/CodingProjects/app/Services/SilaederOidcClient.php` — discovery, PKCE, обмен code, JWKS и проверка ID token.
- `/Users/roctbb/PhpstormProjects/CodingProjects/app/Http/Controllers/Auth/SilaederOidcController.php` — вход, привязка и синхронизация локального пользователя.
- `/Users/roctbb/PhpstormProjects/CodingProjects/app/Http/Controllers/Auth/LoginController.php` — единый выход.
- `/Users/roctbb/PhpstormProjects/CodingProjects/routes/web.php` — маршруты входа/callback/logout.
- `/Users/roctbb/PhpstormProjects/CodingProjects/config/services.php` и `.env.example` — переменные окружения.
- `/Users/roctbb/PhpstormProjects/CodingProjects/database/migrations/2026_08_08_120000_add_silaeder_oidc_identity_to_users_table.php` — локальная OIDC-идентичность.
- `/Users/roctbb/PhpstormProjects/CodingProjects/tests/Feature/SilaederOidcAuthenticationTest.php` — тесты полного потока.

## Контракт OIDC

### Production provider

Issuer:

```text
https://lk.silaeder.ru
```

Discovery необходимо использовать как источник endpoints:

```text
https://lk.silaeder.ru/.well-known/openid-configuration
```

Текущие значения discovery:

| Назначение | Endpoint |
| --- | --- |
| Authorization | `https://lk.silaeder.ru/oauth/authorize` |
| Token | `https://lk.silaeder.ru/api/oauth/token` |
| UserInfo | `https://lk.silaeder.ru/api/oauth/userinfo` |
| JWKS | `https://lk.silaeder.ru/api/oauth/jwks` |
| Revocation | `https://lk.silaeder.ru/api/oauth/revoke` |
| RP-Initiated Logout | `https://lk.silaeder.ru/oauth/logout` |

Endpoints не следует прописывать вручную: код должен читать discovery и проверять точное совпадение `issuer`.

### Поток и защита

- Только `response_type=code`.
- `state` обязателен, длина на стороне CRM — 16–512 символов.
- `nonce` обязателен, длина — 16–255 символов.
- PKCE обязателен даже конфиденциальному серверному клиенту; только `S256`.
- Redirect URI сравнивается точно, включая схему, порт, путь и завершающий `/`.
- В production redirect URI должен быть HTTPS; HTTP разрешён только для `localhost` и `127.0.0.1`.
- ID token — JWT/RS256; необходимо проверять подпись по JWKS, `iss`, `aud`, `exp`, `iat` и `nonce`.
- Access и refresh tokens — непрозрачные случайные значения; нельзя пытаться декодировать их как JWT.
- Authorization code одноразовый.
- Refresh token ротируется при каждом refresh. После успешного refresh нужно атомарно сохранить весь новый token response; старый refresh token становится недействительным.
- Секреты и токены должны оставаться только на backend; их нельзя отдавать Vue-приложению или писать в логи.

### Время жизни

| Объект | Срок |
| --- | --- |
| Authorization code | 5 минут |
| Access token | 15 минут |
| ID token | 15 минут |
| Refresh token | 30 дней, с ротацией |

### Scopes и claims

| Scope | Claims/назначение |
| --- | --- |
| `openid` | обязательный стабильный `sub` |
| `profile` | `name`, `preferred_username`, `object_id`, `object_type`, `crm_object` |
| `email` | `email`, `email_verified` |
| `roles` | `role`, `roles` |
| `avatar` | защищённый URL `picture` |
| `offline_access` | refresh token |

Важные детали:

- `sub` — UUID поля `Object.sso_subject`, то есть идентификатор CRM-объекта ученика/учителя, а не `users.id` и не `objects.id`.
- Сохранять связь нужно по `(issuer, sub)`. Нельзя связывать пользователей по email или `object_id`.
- `object_type` сейчас обычно `students` или `teachers`; доменный тип нужно брать отсюда, а не угадывать из роли.
- `crm_object` содержит только `{id, type, name}`. Произвольные `params`/`attributes` CRM в claim не попадают.
- Текущие роли учётной записи: `student`, `teacher`, `admin`. Сейчас `roles` фактически содержит один элемент — текущую роль.
- Аккаунт без связанного identity-объекта не может завершить OIDC-вход.
- `picture`, если он есть, защищён: изображение нужно загружать с `Authorization: Bearer ACCESS_TOKEN` и scope `avatar`.
- В текущей серверной реализации `email_verified` всегда возвращается как `false`. На этот claim нельзя опираться как на доказательство подтверждения почты без изменения CRM.

### Рекомендуемая конфигурация будущего Flask-клиента

Документация CRM предлагает Authlib, server-side Flask sessions и Redis:

```dotenv
FLASK_SECRET_KEY=<длинный случайный секрет>
REDIS_URL=redis://redis:6379/0

CRM_OIDC_ISSUER=https://lk.silaeder.ru
CRM_OIDC_CLIENT_ID=olympiads
CRM_OIDC_CLIENT_SECRET=<секрет из CRM>

APP_BASE_URL=https://olympiads.example.ru
```

Ожидаемые зарегистрированные URI будущего сервиса, если сохранить маршруты из Flask-примера:

```text
https://olympiads.example.ru/auth/crm/callback
https://olympiads.example.ru/auth/crm/logout/callback
```

Для обычной локальной сессии можно ограничиться `openid profile email roles`. `offline_access` следует запрашивать только если действительно нужен долгоживущий refresh token. `avatar` также необязателен.

Для Vue + Flask безопаснее держать OAuth callback и сессию на Flask-backend и обслуживать frontend с того же внешнего origin. Рекомендуемые cookie-флаги: `HttpOnly`, `Secure`, `SameSite=Lax`; URL за reverse proxy лучше собирать из фиксированного `APP_BASE_URL` либо корректно и узко настроить доверие к forwarded headers.

## Как OIDC сделан в `CodingProjects`

Маршруты:

```text
GET /auth/silaeder
GET /auth/silaeder/link
GET /auth/silaeder/link/confirm/{token}
GET /auth/silaeder/callback
GET /auth/silaeder/logout/callback
POST /logout
```

Переменные окружения:

```dotenv
APP_URL=https://example.ru
CRM_OIDC_ENABLED=true
CRM_OIDC_ISSUER=https://lk.silaeder.ru
CRM_OIDC_CLIENT_ID=coding-projects
CRM_OIDC_CLIENT_SECRET=<secret>
CRM_OIDC_REDIRECT_URI=https://example.ru/auth/silaeder/callback
CRM_OIDC_POST_LOGOUT_REDIRECT_URI=https://example.ru/auth/silaeder/logout/callback
```

Поведение реализации:

- Запрашивает `openid profile email roles`, без `offline_access`; токены нужны только во время callback, затем используется локальная Laravel-сессия.
- Генерирует криптографические `state`, `nonce`, `code_verifier`; в сессии хранит хэш `state`, verifier, nonce, redirect URI и время создания.
- Проверяет callback state до обращения к token endpoint.
- Получает discovery и JWKS с кэшем 5 минут, требует RS256 и PKCE S256, повторно загружает JWKS при ошибке подписи.
- Обменивает code через `client_secret_basic`, проверяет ID token и дополнительно требует совпадения `userinfo.sub` с `id_token.sub`.
- Внешняя идентичность хранится в `users.oidc_issuer` и `users.oidc_subject` с уникальным составным индексом; поля скрыты при сериализации модели.
- Если `(issuer, sub)` уже известна, локальный профиль синхронизируется при входе.
- Если email новый, создаётся локальный пользователь со случайным паролем.
- Если email уже занят непривязанным локальным аккаунтом, автоматической склейки нет: отправляется одноразовая подписанная ссылка на email, действующая 30 минут.
- Внешний `admin` намеренно преобразуется в локального `teacher`; `student` и `teacher` сохраняются без изменения.
- При OIDC-входе выход запускает RP-Initiated Logout и проверяет возвращённый `state`. Реализация использует `client_id`, без `id_token_hint`; CRM поддерживает оба варианта.

Что можно перенести концептуально в `olympiads`:

- уникальность `(issuer, sub)`;
- синхронизацию имени/email/роли при каждом входе;
- строгие state/nonce/PKCE проверки;
- явное безопасное разрешение конфликтов email;
- интеграционные тесты с фальшивыми discovery, JWKS, token и userinfo endpoints.

Что не стоит переносить буквально:

- собственную реализацию OIDC на PHP; для Flask уже есть официальный пример на Authlib;
- преобразование `admin -> teacher`, если в олимпиадном сервисе нужна собственная административная роль. Лучше хранить внешний `crm_role` отдельно, а локальный `is_admin` выдавать явно.
- модель класса из `CodingProjects`: там `grade_year` — собственное локальное поле и оно не приходит из CRM.

## Контракт внешних уведомлений

### Настройка клиента в CRM

Администратор CRM должен создать или изменить OIDC-клиента `olympiads`:

- клиент активный;
- клиент конфиденциальный;
- включено `can_send_notifications` («Разрешить отправку уведомлений»);
- в `allowed_roles` присутствуют роли получателей, как минимум `student`;
- backend получает `client_id` и показанный один раз `client_secret`.

Используются те же credentials, что и для OIDC. Получать отдельный access token для API уведомлений не нужно.

Рекомендуемые переменные окружения можно унифицировать так:

```dotenv
CRM_BASE_URL=https://lk.silaeder.ru
CRM_OIDC_ISSUER=https://lk.silaeder.ru
CRM_OIDC_CLIENT_ID=olympiads
CRM_OIDC_CLIENT_SECRET=<secret>
```

В документации уведомлений имена приведены как `CRM_CLIENT_ID`/`CRM_CLIENT_SECRET`; это тот же секрет. В новом сервисе лучше не заводить вторую копию и использовать единый набор `CRM_OIDC_*`.

### Запрос

```http
POST https://lk.silaeder.ru/api/external/notifications
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/json
Idempotency-Key: olympiads.reminder.<stable-event-id>

{
  "recipient_sub": "790be3dd-4b7a-4ab4-94ce-82d44bcfd06f",
  "title": "Скоро отборочный этап",
  "message": "Отборочный этап начнётся через 7 дней.",
  "url": "https://olympiads.example.ru/olympiads/42"
}
```

Ограничения:

| Элемент | Ограничение |
| --- | --- |
| `Idempotency-Key` | обязателен; 8–128 символов; только `A-Z`, `a-z`, цифры, `.`, `_`, `:`, `-` |
| `recipient_sub` | обязательный UUID из OIDC `sub` |
| `title` | 1–200 символов после trim, без `\r`/`\n` |
| `message` | 1–10 000 символов после trim |
| `url` | необязательный абсолютный HTTPS URL до 2 000 символов; без username/password; HTTP только для localhost |

Неизвестные JSON-поля отклоняются с `422`.

### Идемпотентность и ответы

`Idempotency-Key` уникален в пределах одного CRM API-клиента. Один бизнес-факт должен всегда отправляться с одним ключом и одинаковыми нормализованными значениями `recipient_sub`, `title`, `message` и `url`.

| Код | Значение |
| --- | --- |
| `202` | уведомление создано и поставлено в очередь |
| `200` | безопасный повтор того же ключа и тела (`idempotent_replay=true`) |
| `401` | неверные credentials, клиент отключён/публичный или нет права уведомлять |
| `403` | роль получателя не разрешена клиенту |
| `404` | `sub` не найден, объект удалён или не привязан к аккаунту |
| `409` | тот же ключ использован с другим телом |
| `422` | неверный заголовок или JSON |
| `429` | лимит 600 запросов в минуту с одного IP |
| `503` | запись сохранена, но постановка в очередь не удалась |

При таймауте, `429` или `5xx` повторяется тот же JSON с тем же ключом. Нужны exponential backoff, jitter и поддержка `Retry-After`. `200` и `202` считаются успехом. Ошибки остальных `4xx` автоматически не повторяются.

### Фактическая доставка

- CRM сначала сохраняет `Notification`, затем ставит две Celery-задачи: email и Telegram.
- Задача email-доставки всегда ставится в очередь и пытается отправить письмо на `User.email`.
- Telegram отправляется только при существующей `TelegramConnection`; пользователь сам подключает бота в ЛК.
- Задачи используют автоматические повторы с backoff/jitter, максимум 5 retries.
- `202` означает только «сохранено и поставлено в очередь», а не успешную доставку.
- Внешний API не предоставляет callback или endpoint чтения статуса доставки. Ошибки каналов остаются в полях `email_error`/`telegram_error` CRM.
- Получатель ищется по `Object.sso_subject`, затем по связи identity object → user. Если связь исчезла, будет `404`.
- Имя внешнего OIDC-клиента записывается как источник и показывается в email/Telegram.

## Модель личности в CRM и будущая локальная модель

В CRM разделены:

- `User`: учётная запись (`id`, `name`, `email`, `role`);
- `Object`: доменная личность (`sso_subject` UUID, `name`, `type`, `params`, `attributes`);
- `user_identity_objects`: однозначная связь учётной записи с identity-объектом.

OIDC `sub` принадлежит `Object`, благодаря чему он сохраняет смысл при изменении email/имени учётной записи.

Для будущей таблицы пользователя в `olympiads` достаточно подготовить nullable-поля:

```text
id
oidc_issuer
oidc_subject
name
email
crm_role
object_type
grade_year / current_grade      # локально, пока CRM этого не отдаёт
participants_visibility         # отдельное согласие на показ имени
last_login_at
created_at / updated_at
```

Ограничение: уникальный индекс `(oidc_issuer, oidc_subject)`. Для MVP без авторизации таблицу можно не активировать, но схема олимпиад/этапов не должна зависеть от числовых CRM ID.

## Интеграционные риски и решения

1. **Класс ученика отсутствует в claims.** Ни `grade`, ни `grade_year`, ни произвольные CRM attributes не выдаются. На первом этапе хранить класс локально. Позже либо добавить в CRM отдельный минимальный claim/scope, либо сделать защищённый API. Не расширять `crm_object` всеми attributes: там могут быть лишние персональные данные.

2. **Публичный показ имён участников — отдельный вопрос приватности.** OIDC-согласие на `profile` не является согласием на публикацию участия. Нужна настройка видимости/opt-in, разумный default и доступ к списку только авторизованным пользователям, если не решено иначе.

3. **`sub`, а не email.** Отправка напоминаний невозможна до первого входа пользователя через CRM. Email и `object_id` не подходят как запасной идентификатор.

4. **Неизменность idempotency payload.** После изменения даты/текста повтор старого reminder key с новым телом даст `409`. В собственной БД нужен устойчивый `NotificationDispatch`/outbox с версией расписания. Пример ключа: `olympiads.reminder.<dispatch_uuid>`. При retry тело берётся из сохранённой записи, а не строится заново.

5. **Нет bulk endpoint.** Напоминание сотням учеников — сотни POST-запросов. Отправлять их Celery-задачами с ограничением ниже 600/min/IP, backoff и jitter.

6. **`202` не подтверждает доставку.** В локальной модели различать как минимум `pending`, `accepted`, `permanent_failure`; нельзя показывать `accepted` как «прочитано» или «доставлено». Канальный статус извне недоступен.

7. **Роль может измениться.** При входе получать свежий userinfo и обновлять локальный `crm_role`; для критичных операций не полагаться бесконечно на старое значение сессии. Локальные права админа лучше хранить отдельно.

8. **`email_verified=false`.** Не блокировать вход только из-за этого claim и не помечать CRM-email подтверждённым без отдельного решения.

9. **Секрет общий для OIDC и уведомлений.** Компрометация даёт обе возможности. Хранить только на backend, не включать в Vue build, не логировать Basic header, токены или authorization code. После ротации secret все старые codes/tokens клиента отзываются — обновление конфигурации должно быть согласованным.

10. **Exact redirect URI и reverse proxy.** Ошибка внешней схемы/host за proxy приведёт к `invalid_redirect_uri`. Использовать фиксированный `APP_BASE_URL` и доверять forwarded headers только от известного proxy.

11. **Сессии и refresh token.** Для нескольких Flask-инстансов нужны server-side sessions в Redis. При `offline_access` обновление rotating refresh token должно быть атомарным, иначе параллельные запросы инвалидируют сессию.

12. **Удалённый или отвязанный CRM-объект.** OIDC refresh перестанет работать, а уведомления вернут `404`. Это постоянная ошибка для конкретной связи до повторного входа/исправления CRM; бесконечно retry делать нельзя.

## Практическая последовательность интеграции после MVP

1. В CRM создать конфиденциального клиента `olympiads`, зарегистрировать точные callback/logout URI, разрешить нужные roles/scopes и `can_send_notifications`.
2. Добавить локального пользователя с уникальным `(issuer, sub)`; не связывать его с числовым `object_id`.
3. Реализовать Flask/Authlib login callback и server-side Redis session; написать интеграционные тесты по образцу `CodingProjects`.
4. Добавить локальный класс/год обучения и отдельную настройку видимости участия.
5. Добавить пользовательский план и статусы этапов.
6. Добавить outbox `NotificationDispatch`, Celery beat для планирования и Celery worker для вызова CRM API.
7. Проверить сценарии `200`, `202`, `403`, `404`, `409`, `422`, `429`, `503`, таймаут и ротацию client secret.
