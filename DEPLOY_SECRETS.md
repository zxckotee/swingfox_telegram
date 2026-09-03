# Секреты и деплой Telegram-бота

Один production-бот на том же сервере, что и сайт. Staging для бота **не используется**.

## Порядок деплоя

1. **swingfox** (prod) — backend + сеть `swingfox_default`
2. **swingfox_telegram** — контейнер бота в `/root/swingfox_telegram`

---

## GitHub Secrets — `swingfox`

| Secret | Описание |
|--------|----------|
| `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` | Деплой на сервер |
| `TELEGRAM_BOT_TOKEN` | Токен @BotFather |
| `TELEGRAM_BOT_SHARED_SECRET` | Ваш сгенерированный ключ (32+ символов) |
| `TELEGRAM_BOT_USERNAME` | Username бота без `@` |

---

## GitHub Secrets — `swingfox_telegram`

| Secret | = в swingfox |
|--------|----------------|
| `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` | те же |
| `TELEGRAM_SECRET` | `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_BOT_SHARED_SECRET` | тот же shared secret |
| `TELEGRAM_PROXY` *(optional)* | SOCKS5/HTTP proxy если `api.telegram.org` недоступен с сервера, напр. `socks5://127.0.0.1:1080` |
| `TELEGRAM_API_BASE_URL` *(optional)* | Альтернативный gateway, по умолчанию `https://api.telegram.org` |

---

## Если бот не видит Telegram API

Ошибки вида `Network is unreachable`, `Read timed out`, `Connection reset` означают, что контейнер не может достучаться до `api.telegram.org`.

1. На сервере проверьте с **хоста** и **из контейнера**:
   ```bash
   curl -I --max-time 10 https://api.telegram.org
   docker exec swingfox_telegram_bot curl -I --max-time 10 https://api.telegram.org
   ```
2. Если с хоста работает, а из контейнера нет — в `docker-compose.yml` раскомментируйте `network_mode: host` и задайте `SWINGFOX_API_URL=https://127.0.0.1:3001/api`
3. Если нигде не открывается — добавьте **`TELEGRAM_PROXY`**
4. Перезапустите деплой бота

Старый бот (`tg_methods.py`) использовал простой `requests.get` **без timeout** для long polling — новый клиент приведён к тому же паттерну.

## Workflow

Один pipeline: **CI/CD Telegram Bot** (файл `.github/workflows/cicd.yml`)

- Автозапуск при push в `master` или `prod3`
- Ручной запуск: **Actions → CI/CD Telegram Bot → Run workflow**

### Почему не видно workflow в Actions?

GitHub показывает workflow только если файл **есть в default-ветке (`master`)**.  
Смержите PR #1 в `master` — появится один pipeline «CI/CD Telegram Bot».

---

## Ручной запуск

1. **Actions** → **CI/CD Telegram Bot** → **Run workflow**
2. Параметры:
   - **branch** — ветка для деплоя (по умолчанию `master`)
   - **skip_build** — без пересборки образа

---

## Backend: prod / staging

Переключатель **`PRODUCTION`** в `.env`:

| `PRODUCTION` | Backend API | Сайт |
|---|---|---|
| `on` *(default)* | `https://127.0.0.1:3001/api` (prod) | `https://swingfox.ru` |
| `off` | `https://127.0.0.1:3002/api` (staging) | `https://swingfox.ru/stagging` |

```bash
# production (по умолчанию)
PRODUCTION=on

# staging (ручной деплой через workflow_dispatch)
PRODUCTION=off
```

Явные `SWINGFOX_API_URL`, `SWINGFOX_UPLOADS_URL`, `PUBLIC_WEB_URL` переопределяют значения по умолчанию.

Сессии бота хранятся в SQLite (Docker volume `bot_sessions` → `/app/data/sessions.db`) и переживают перезапуск контейнера. Если в `.env` остался `SESSION_DB_PATH=/data/sessions.db`, удалите эту строку — иначе бот может не стартовать из‑за прав на `./data`.

Если на сервере закончилось место (`No space left on device`), освободите диск:

```bash
df -h
docker system prune -af
docker volume prune -f
```

После освобождения места перезапустите бот. Пока диск полон, бот может работать с сессиями в памяти (не переживают рестарт).

---

## Сеть

Бот использует **`network_mode: host`** (как старый `python main.py` на сервере):
- Telegram API — через сеть хоста
- SwingFox backend — loopback HTTPS (`3002` staging, `3001` prod)

Если Telegram API недоступен даже с хоста — добавьте **`TELEGRAM_PROXY`**.

## Проверка на сервере

```bash
curl -I --max-time 10 https://api.telegram.org
curl -sk https://127.0.0.1:3002/api/status   # staging
curl -sk https://127.0.0.1:3001/api/status   # prod
docker-compose -f /root/swingfox_telegram/docker-compose.yml up -d --build
docker logs swingfox_telegram_bot --tail 30
```

Ожидаем в логах:
```
Backend: staging → https://127.0.0.1:3002/api
Connected to Telegram as @YourBot
```
