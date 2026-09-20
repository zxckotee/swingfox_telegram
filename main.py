import os
import time

from dotenv import load_dotenv
from requests.exceptions import RequestException

from api.swingfox_client import SwingfoxClient, SwingfoxAPIError
from config.backend import get_backend_config
from handlers.bot_handlers import BotHandlers
from telegram.client import (
    TelegramClient,
    _is_duplicate_poll_error,
    _is_transient_poll_error,
    _is_webhook_conflict_error,
)

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
            elif msg.get('photo'):
                handlers.handle_photo(chat_id, user_id, msg['photo'])

        elif 'callback_query' in update:
            callback = update['callback_query']
            data = callback.get('data', '')
            user_id = callback.get('from', {}).get('id')
            print(f"Callback: {data} from {user_id}")
            try:
                handlers.tg.answer_callback_query(callback['id'])
                print(f"Callback ack ok: {data}")
            except Exception as exc:
                print(f"Callback ack failed [{data}]: {exc}")
            handlers.handle_callback(callback, pre_acknowledged=True)
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
    backend = get_backend_config()
    api = SwingfoxClient()
    handlers = BotHandlers(api)
    tg = TelegramClient()

    env_label = 'production' if backend['production'] else 'staging'
    print('SwingFox Telegram bot started (polling)...')
    print(f'Backend: {env_label} → {backend["api_url"]}')
    if api._token_store.persistent and api._token_store.count():
        print(f'Restored {api._token_store.count()} persisted session(s) from SQLite')
    elif not api._token_store.persistent:
        print('WARNING: sessions are in-memory only until disk space is freed')
    print(f'Session DB: {api._token_store.db_path}')
    if not os.getenv('TELEGRAM_BOT_SHARED_SECRET'):
        print('WARNING: TELEGRAM_BOT_SHARED_SECRET is not set — session refresh will fail')

    try:
        me = tg.check_connection()
        username = me.get('username') or me.get('first_name') or 'bot'
        print(f'Connected to Telegram as @{username}')
    except Exception as exc:
        _print_startup_hints(exc)

    try:
        tg.ensure_polling_mode()
        print('Polling mode enabled (webhook cleared if it was set)')
    except Exception as exc:
        print(f'WARNING: could not switch bot to polling mode: {exc}')

    last_update_id = 0
    last_webhook_check = time.time()

    while True:
        try:
            if time.time() - last_webhook_check >= 60:
                try:
                    webhook_url = (tg.get_webhook_info().get('url') or '').strip()
                    if webhook_url:
                        print(f'Webhook re-appeared ({webhook_url}); clearing for polling...')
                        tg.delete_webhook()
                except Exception as exc:
                    print(f'Webhook check failed: {exc}')
                last_webhook_check = time.time()

            updates = tg.get_updates(offset=last_update_id + 1)
            if updates:
                callbacks = sum(1 for item in updates if 'callback_query' in item)
                if callbacks:
                    print(f'Polling batch: {len(updates)} update(s), {callbacks} callback(s)')

            for update in updates:
                uid = update.get('update_id', 0)
                if uid > last_update_id:
                    last_update_id = uid
                _process_update(handlers, update)

        except KeyboardInterrupt:
            print('Stopped.')
            break
        except RequestException as exc:
            if _is_duplicate_poll_error(exc):
                print(
                    'ERROR: Another process is polling the same bot token. '
                    'Stop duplicate swingfox_telegram containers.'
                )
                time.sleep(5)
                continue
            if _is_webhook_conflict_error(exc):
                print('Webhook conflict detected; clearing webhook and resuming polling...')
                try:
                    tg.delete_webhook()
                except Exception as clear_exc:
                    print(f'Failed to clear webhook: {clear_exc}')
                time.sleep(2)
                continue
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            print(f'Error: {exc}')
            time.sleep(5)
        except Exception as exc:
            if _is_duplicate_poll_error(exc):
                print(
                    'ERROR: Another process is polling the same bot token. '
                    'Stop duplicate swingfox_telegram containers.'
                )
                time.sleep(5)
                continue
            if _is_webhook_conflict_error(exc):
                print('Webhook conflict detected; clearing webhook and resuming polling...')
                try:
                    tg.delete_webhook()
                except Exception as clear_exc:
                    print(f'Failed to clear webhook: {clear_exc}')
                time.sleep(2)
                continue
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            print(f'Error: {exc}')
            time.sleep(5)


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_SECRET'):
        raise SystemExit('Set TELEGRAM_SECRET in .env')
    run_polling()
