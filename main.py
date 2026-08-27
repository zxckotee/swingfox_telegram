import os
import time

from dotenv import load_dotenv
from requests.exceptions import RequestException

from api.swingfox_client import SwingfoxClient, SwingfoxAPIError
from handlers.bot_handlers import BotHandlers
from telegram.client import TelegramClient, _is_transient_poll_error

load_dotenv()


def _print_startup_hints(error: Exception) -> None:
    print(f'WARNING: Telegram API is not reachable: {error}')
    print('If api.telegram.org is blocked, set TELEGRAM_PROXY in .env')


def _process_update(handlers: BotHandlers, update: dict) -> None:
    try:
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
    except SwingfoxAPIError as exc:
        chat_id = None
        if 'message' in update:
            chat_id = update['message']['chat']['id']
        elif 'callback_query' in update:
            chat_id = update['callback_query']['message']['chat']['id']
        if chat_id is not None:
            handlers.tg.send_message(chat_id, f"❌ {exc.message}")
        print(f'API error while handling update: {exc.message}')
    except Exception as exc:
        print(f'Handler error: {exc}')


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
            updates = tg.get_updates(offset=last_update_id + 1)

            for update in updates:
                uid = update.get('update_id', 0)
                if uid > last_update_id:
                    last_update_id = uid
                _process_update(handlers, update)

        except KeyboardInterrupt:
            print('Stopped.')
            break
        except RequestException as exc:
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            print(f'Error: {exc}')
            time.sleep(5)
        except Exception as exc:
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            print(f'Error: {exc}')
            time.sleep(5)


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_SECRET'):
        raise SystemExit('Set TELEGRAM_SECRET in .env')
    run_polling()
