import os
import time

from dotenv import load_dotenv

from api.swingfox_client import SwingfoxClient
from handlers.bot_handlers import BotHandlers
from telegram.client import TelegramClient

load_dotenv()


def run_polling() -> None:
    api = SwingfoxClient()
    handlers = BotHandlers(api)
    tg = TelegramClient()

    print('SwingFox Telegram bot started (polling)...')
    last_update_id = 0

    while True:
        try:
            updates = tg.get_updates(offset=last_update_id + 1 if last_update_id else None)
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
            time.sleep(5)


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_SECRET'):
        raise SystemExit('Set TELEGRAM_SECRET in .env')
    run_polling()
