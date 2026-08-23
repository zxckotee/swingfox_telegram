# Секреты и деплой Telegram-бота

Бот и сайт живут на **одном сервере**. Staging и production используют **одни и те же GitHub Secrets** (токен бота, shared secret, SSH). Отличаются только URL сайта — они зашиты в CI/CD workflow каждого окружения.

## Порядок деплоя

1. **swingfox** — backend + frontend + postgres (миграции, Docker-сеть)
2. **swingfox_telegram** — контейнер бота (та же Docker-сеть)

---

## GitHub Secrets — репозиторий `swingfox`

**Settings → Secrets and variables → Actions**

### Уже есть

| Secret | Назначение |
|--------|------------|
| `SSH_HOST` | IP/hostname сервера |
| `SSH_USER` | SSH-пользователь |
| `SSH_PRIVATE_KEY` | Ключ для деплоя |
| `SSL_CERT` | SSL (base64) |
| `SSL_KEY` | SSL key (base64) |
| `OPENROUTER_API_KEY` | chat-bots (prod) |

### Telegram (prod **и** staging — одни secrets)

| Secret | Описание |
|--------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен @BotFather |
| `TELEGRAM_BOT_SHARED_SECRET` | Случайная строка 32+ символов; **одинаковая** в swingfox и swingfox_telegram |
| `TELEGRAM_BOT_USERNAME` | Имя бота без `@` |

Используются в:
- `cicd.yml` (ветка `prod3`) — backend prod
- `cicd-staging.yml` (ветка `stagging`) — backend staging

---

## GitHub Secrets — репозиторий `swingfox_telegram`

### SSH (те же, что swingfox)

| Secret |
|--------|
| `SSH_HOST` |
| `SSH_USER` |
| `SSH_PRIVATE_KEY` |

### Telegram (prod **и** staging — одни secrets)

| Secret | = в swingfox |
|--------|----------------|
| `TELEGRAM_SECRET` | `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_BOT_SHARED_SECRET` | `TELEGRAM_BOT_SHARED_SECRET` |

Используются в `cicd.yml` и `cicd-staging.yml`.

### URL (не secrets — в workflow)

| Окружение | SWINGFOX_API_URL | SWINGFOX_UPLOADS_URL | PUBLIC_WEB_URL |
|-----------|------------------|----------------------|----------------|
| Production | `http://backend:3001/api` | `https://swingfox.ru/uploads` | `https://swingfox.ru` |
| Staging | `http://backend:3001/api` | `https://swingfox.ru/stagging/uploads` | `https://swingfox.ru/stagging` |

---

## Сводка совпадений

```
swingfox.TELEGRAM_BOT_TOKEN         =  swingfox_telegram.TELEGRAM_SECRET
swingfox.TELEGRAM_BOT_SHARED_SECRET =  swingfox_telegram.TELEGRAM_BOT_SHARED_SECRET
```

Один бот @BotFather на оба окружения: backend шлёт уведомления, контейнер бота принимает сообщения.

---

## Пути на сервере

| Окружение | swingfox | swingfox_telegram |
|-----------|----------|-------------------|
| Production | `/root/swingfox` | `/root/swingfox_telegram` |
| Staging | `/root/swingfox-staging` | `/root/swingfox_telegram-staging` |

---

## Минимальный набор secrets (оба репо)

**swingfox:** `SSH_*`, `SSL_*`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_SHARED_SECRET`, `TELEGRAM_BOT_USERNAME`

**swingfox_telegram:** `SSH_*`, `TELEGRAM_SECRET`, `TELEGRAM_BOT_SHARED_SECRET`

---

## Проверка

```bash
docker ps | grep telegram
docker logs swingfox_telegram_bot --tail 30
docker compose exec backend printenv | grep TELEGRAM
```

Сначала деплой swingfox, затем swingfox_telegram.
