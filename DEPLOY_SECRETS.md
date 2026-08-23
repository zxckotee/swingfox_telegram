# Секреты и деплой Telegram-бота

Бот и сайт могут жить на **одном сервере**. Сайт поднимает Docker-сеть `swingfox_default` (prod) или `swingfox-staging_default` (staging). Бот подключается к этой сети и ходит в API по внутреннему адресу `http://backend:3001/api`.

## Порядок деплоя на сервере

1. **swingfox** — backend + frontend + postgres (создаёт Docker-сеть и применяет миграции с полями Telegram).
2. **swingfox_telegram** — контейнер бота (подключается к той же сети).

---

## GitHub Secrets: репозиторий `swingfox`

**Settings → Secrets and variables → Actions → Repository secrets**

### Уже используются (без изменений)

| Secret | Назначение |
|--------|------------|
| `SSH_HOST` | IP или hostname сервера |
| `SSH_USER` | SSH-пользователь (например `root`) |
| `SSH_PRIVATE_KEY` | Приватный ключ для деплоя |
| `SSL_CERT` | SSL-сертификат (base64) |
| `SSL_KEY` | SSL-ключ (base64) |
| `OPENROUTER_API_KEY` | Ключ для chat-bots (prod) |

### Новые — для Telegram на **backend** (prod, ветка `prod3`)

| Secret | Пример / описание |
|--------|-------------------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather (тот же, что у бота) |
| `TELEGRAM_BOT_SHARED_SECRET` | Случайная строка 32+ символов; **одинаковая** в swingfox и swingfox_telegram |
| `TELEGRAM_BOT_USERNAME` | Имя бота без `@`, например `SwingFoxBot` |

Backend использует их для:
- отправки push-уведомлений в Telegram (`telegramNotificationService`);
- генерации ссылок `t.me/<username>?start=link_...` в профиле.

### Новые — staging (ветка `stagging`)

| Secret | Описание |
|--------|----------|
| `TELEGRAM_BOT_TOKEN_STAGING` | Токен **staging-бота** (рекомендуется отдельный бот) |
| `TELEGRAM_BOT_SHARED_SECRET_STAGING` | Shared secret для staging |
| `TELEGRAM_BOT_USERNAME_STAGING` | Username staging-бота |

Если staging и prod на одном сервере с одним ботом — можно продублировать prod-значения, но лучше отдельный test-бот.

---

## GitHub Secrets: репозиторий `swingfox_telegram`

### Общие для деплоя (prod + staging)

| Secret | Назначение |
|--------|------------|
| `SSH_HOST` | **Тот же сервер**, что и у swingfox |
| `SSH_USER` | **Тот же**, что у swingfox |
| `SSH_PRIVATE_KEY` | **Тот же**, что у swingfox |

### Production (workflow `cicd.yml`, ветки `master` / `prod3`)

| Secret | Значение |
|--------|----------|
| `TELEGRAM_SECRET` | = `TELEGRAM_BOT_TOKEN` из swingfox (токен @BotFather) |
| `TELEGRAM_BOT_SHARED_SECRET` | = **тот же** `TELEGRAM_BOT_SHARED_SECRET`, что в swingfox |
| `SWINGFOX_API_URL` | `http://backend:3001/api` (внутри Docker-сети на том же хосте) |
| `SWINGFOX_UPLOADS_URL` | `https://swingfox.ru/uploads` (публичные URL для фото в Telegram) |
| `PUBLIC_WEB_URL` | `https://swingfox.ru` (ссылки «Открыть ЛК») |

### Staging (workflow `cicd-staging.yml`, ветка `stagging`)

| Secret | Значение |
|--------|----------|
| `TELEGRAM_SECRET_STAGING` | Staging bot token |
| `TELEGRAM_BOT_SHARED_SECRET_STAGING` | = staging shared secret из swingfox |
| `SWINGFOX_API_URL_STAGING` | `http://backend:3001/api` (backend staging в сети `swingfox-staging_default`) |
| `SWINGFOX_UPLOADS_URL_STAGING` | `https://swingfox.ru/stagging/uploads` |
| `PUBLIC_WEB_URL_STAGING` | `https://swingfox.ru/stagging` |

---

## Сводка: что должно совпадать

```
TELEGRAM_BOT_TOKEN (swingfox)  ===  TELEGRAM_SECRET (swingfox_telegram)
TELEGRAM_BOT_SHARED_SECRET     ===  TELEGRAM_BOT_SHARED_SECRET
```

Один и тот же `@BotFather` токен нужен:
- **backend** — чтобы слать уведомления через Bot API;
- **бот** — чтобы принимать сообщения и polling.

Shared secret нужен обоим для HMAC-эндпоинтов `/api/telegram/link/complete`, `/token/refresh`, `/web-login-code`.

---

## Пути на сервере

| Окружение | swingfox | swingfox_telegram |
|-----------|----------|-------------------|
| Production | `/root/swingfox` | `/root/swingfox_telegram` |
| Staging | `/root/swingfox-staging` | `/root/swingfox_telegram-staging` |

---

## Локальный Docker (разработка)

```bash
# 1. Поднять swingfox
cd swingfox && docker compose up -d

# 2. Создать .env в swingfox_telegram (из .env.example)
# 3. Поднять бота
cd swingfox_telegram && docker compose up -d --build
```

В `.env` для локалки:
```env
TELEGRAM_SECRET=...
TELEGRAM_BOT_SHARED_SECRET=...
SWINGFOX_API_URL=http://backend:3001/api
SWINGFOX_UPLOADS_URL=https://swingfox.ru/uploads
PUBLIC_WEB_URL=https://swingfox.ru
```

---

## Проверка после деплоя

```bash
# Prod
docker ps | grep telegram
docker logs swingfox_telegram_bot --tail 50

# Backend видит Telegram
docker compose exec backend printenv | grep TELEGRAM
```

В профиле на сайте: «Получить ссылку для привязки» → открыть в Telegram → меню бота.

---

## Важно

- Не коммитьте `.env` с реальными токенами.
- При смене `TELEGRAM_BOT_SHARED_SECRET` нужно обновить secret **в обоих** репозиториях и передеплоить backend и bot.
- Сначала всегда деплой **swingfox** (миграции + сеть), затем **swingfox_telegram**.
