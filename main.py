import os
import time

from dotenv import load_dotenv

from api.swingfox_client import SwingfoxClient
from handlers.bot_handlers import BotHandlers
from telegram.client import TelegramClient

load_dotenv()


def _print_startup_hints(error: Exception) -> None:
    print(f'WARNING: Telegram API is not reachable: {error}')
    print('If api.telegram.org is blocked from Docker, try either:')
    print('  1) TELEGRAM_PROXY=socks5://127.0.0.1:1080 in .env')
    print('  2) network_mode: host in docker-compose + SWINGFOX_API_URL=http://127.0.0.1:3001/api')


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

    while True:
        try:
            # Same offset logic as legacy main.py / tg_methods.py
            updates = tg.get_updates(offset=last_update_id + 1)

            for update in updates:
                if update.get('update_id', 0) > last_update_id:
                    last_update_id = update['update_id']

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
            time.sleep(5)


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_SECRET'):
        raise SystemExit('Set TELEGRAM_SECRET in .env')
    run_polling()
