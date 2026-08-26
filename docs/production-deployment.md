# Развёртывание на сервере

Проект использует один файл `compose.yaml`. Он собирает production-образы,
применяет миграции и запускает PostgreSQL, Redis, Flask/Gunicorn, Celery worker,
один Celery beat и статический Vue frontend. Внешний nginx и TLS находятся на
хосте и проксируют только на loopback-порты Compose.

## 1. Подготовка окружения

```bash
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
```

Первый результат укажите как `SECRET_KEY`, второй — как `POSTGRES_PASSWORD`.
Затем замените домен и реквизиты OIDC в `.env`. Для домена
`olympiads.example.ru` ключевые значения выглядят так:

```dotenv
APP_BASE_URL=https://olympiads.example.ru
FRONTEND_BASE_URL=https://olympiads.example.ru
CORS_ORIGINS=https://olympiads.example.ru
SESSION_COOKIE_SECURE=true

CRM_OIDC_ISSUER=https://lk.silaeder.ru
CRM_OIDC_CLIENT_ID=olympiads
CRM_OIDC_CLIENT_SECRET=<секрет клиента ЛК>
```

В ЛК зарегистрируйте точные callback URL:

```text
https://olympiads.example.ru/auth/crm/callback
https://olympiads.example.ru/auth/crm/logout/callback
```

Redis не нужно описывать в `.env`: Compose использует базу `/0` для Celery
broker, `/1` для результатов Celery и `/2` для пользовательских сессий.
PostgreSQL и Redis не публикуют порты на хост.

## 2. Запуск

```bash
docker compose config
docker compose up --build -d
docker compose ps
```

Сервис `migrate` выполняет `flask db upgrade` один раз. API, worker и beat
запускаются только после успешной миграции и готовности PostgreSQL/Redis.

При первом развёртывании импортируйте каталог и создайте редактора:

```bash
docker compose exec api flask --app wsgi import-catalog --sync /data/seed/catalog.json
docker compose exec api flask --app wsgi create-admin
```

Seed-каталог хранится в `data/seed/catalog.json`. Пользовательские планы,
результаты и настройки живут только в PostgreSQL volume и в JSON не выгружаются.

## 3. Внешний nginx

Возьмите за основу `deploy/nginx/olympiads.conf.example`, замените домен и пути
сертификатов, затем подключите файл в системный nginx. Compose слушает только:

- `127.0.0.1:5050` — Flask API и OIDC callback;
- `127.0.0.1:5188` — собранный Vue frontend.

Проверка после перезагрузки nginx:

```bash
curl -fsS https://olympiads.example.ru/api/live
curl -fsS https://olympiads.example.ru/api/health
curl -I https://olympiads.example.ru/
```

## 4. Обновление и резервная копия

Перед обновлением сохраните PostgreSQL:

```bash
docker compose exec -T db pg_dump -U olympiads -d olympiads -Fc > olympiads.dump
```

Если изменены `POSTGRES_USER` или `POSTGRES_DB`, используйте их значения в
команде. После получения новой версии:

```bash
docker compose build
docker compose up -d
docker compose exec api flask --app wsgi import-catalog --sync /data/seed/catalog.json
```

Миграции применятся автоматически через одноразовый `migrate`. Не запускайте
несколько экземпляров `beat`: расписание должно обслуживаться ровно одним
процессом.
