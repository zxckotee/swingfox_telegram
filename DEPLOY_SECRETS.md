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
2. Если с хоста работает, а из контейнера нет — в `docker-compose.yml` раскомментируйте `network_mode: host` и задайте `SWINGFOX_API_URL=http://127.0.0.1:3001/api`
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

## Проверка на сервере

```bash
docker ps | grep telegram
docker logs swingfox_telegram_bot --tail 30
```
