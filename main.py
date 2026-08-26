import os
import time

from dotenv import load_dotenv

from api.swingfox_client import SwingfoxClient
from handlers.bot_handlers import BotHandlers
from telegram.client import TelegramClient

load_dotenv()

POLL_TIMEOUT = int(os.getenv('TELEGRAM_POLL_TIMEOUT', '30'))
INITIAL_BACKOFF = int(os.getenv('TELEGRAM_ERROR_BACKOFF', '5'))
MAX_BACKOFF = int(os.getenv('TELEGRAM_MAX_BACKOFF', '120'))


def _print_startup_hints(error: Exception) -> None:
    print(f'WARNING: Telegram API is not reachable: {error}')
    print('If the server blocks api.telegram.org, set TELEGRAM_PROXY in .env, e.g.:')
    print('  TELEGRAM_PROXY=socks5://127.0.0.1:1080')
    print('Optional custom API gateway:')
    print('  TELEGRAM_API_BASE_URL=https://api.telegram.org')


def run_polling() -> None:
    api = SwingfoxClient()
    handlers = BotHandlers(api)
    tg = TelegramClient()

    print('SwingFox Telegram bot started (polling)...')

    try:
        me = tg.check_connection()
        username = me.get('username') or me.get('first_name') or 'bot'
        print(f'Connected to Telegram as @{username}')
    except Exception as exc:
        _print_startup_hints(exc)

    last_update_id = 0
    backoff = INITIAL_BACKOFF

    while True:
        try:
            updates = tg.get_updates(offset=last_update_id + 1 if last_update_id else None, timeout=POLL_TIMEOUT)
            backoff = INITIAL_BACKOFF

            for update in updates:
                uid = update.get('update_id', 0)
                if uid > last_update_id:
                    last_update_id = uid

                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_id = msg['from']['id']
                    username = msg.get('from', {}).get('username')
                    text = msg.get('text', '')

                    if text.startswith('/start'):
                        handlers.handle_start(chat_id, user_id, text.strip(), username)
                    elif text:
                        handlers.handle_text(chat_id, user_id, text.strip())

                elif 'callback_query' in update:
                    handlers.handle_callback(update['callback_query'])

        except KeyboardInterrupt:
            print('Stopped.')
            break
        except Exception as exc:
            print(f'Error: {exc}')
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_SECRET'):
        raise SystemExit('Set TELEGRAM_SECRET in .env')
    run_polling()
