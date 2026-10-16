import faulthandler
import logging
import os
import resource
import signal
import sys
import time

from dotenv import load_dotenv
from requests.exceptions import RequestException

from api.swingfox_client import SwingfoxClient, SwingfoxAPIError
from config.backend import get_backend_config
from handlers.bot_handlers import BotHandlers
from state.session_store import session_store
from telegram.client import (
    TelegramClient,
    _is_duplicate_poll_error,
    _is_transient_poll_error,
    _is_webhook_conflict_error,
)
from utils.bot_logging import setup_bot_logging

load_dotenv()

log = logging.getLogger('swingfox.telegram')

_shutdown_requested = False


def _print_startup_hints(error: Exception) -> None:
    log.warning('Telegram API is not reachable: %s', error)
    log.warning('If api.telegram.org is blocked, set TELEGRAM_PROXY in .env')


def _memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux ru_maxrss is kilobytes; on macOS it is bytes.
    if sys.platform == 'darwin':
        return usage.ru_maxrss / (1024 * 1024)
    return usage.ru_maxrss / 1024


def _on_shutdown_signal(signum: int, _frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    log.warning('Received signal %s — stopping after current poll iteration', signum)


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
            log.debug('Callback: %s from %s', data, user_id)
            try:
                handlers.tg.answer_callback_query(callback['id'])
            except Exception as exc:
                log.warning('Callback ack failed [%s]: %s', data, exc)
            handlers.handle_callback(callback, pre_acknowledged=True)
    except SwingfoxAPIError as exc:
        chat_id = None
        if 'message' in update:
            chat_id = update['message']['chat']['id']
        elif 'callback_query' in update:
            chat_id = update['callback_query']['message']['chat']['id']
        if chat_id is not None:
            handlers.tg.send_message(chat_id, f"❌ {exc.message}")
        log.warning('API error while handling update: %s', exc.message)
    except Exception:
        log.exception('Handler error while processing update')


def _log_heartbeat(last_update_id: int) -> None:
    log.info(
        'heartbeat last_update_id=%s in_memory_sessions=%s rss_mb=%.1f',
        last_update_id,
        session_store.active_session_count(),
        _memory_mb(),
    )


def run_polling() -> None:
    backend = get_backend_config()
    api = SwingfoxClient()
    handlers = BotHandlers(api)
    tg = TelegramClient()

    env_label = 'production' if backend['production'] else 'staging'
    log.info('SwingFox Telegram bot started (polling)')
    log.info('Backend: %s → %s', env_label, backend['api_url'])
    if api._token_store.persistent and api._token_store.count():
        log.info('Restored %s persisted session(s) from SQLite', api._token_store.count())
    elif not api._token_store.persistent:
        log.warning('Sessions are in-memory only until disk space is freed')
    log.info('Session DB: %s', api._token_store.db_path)
    if not os.getenv('TELEGRAM_BOT_SHARED_SECRET'):
        log.warning('TELEGRAM_BOT_SHARED_SECRET is not set — session refresh will fail')

    try:
        me = tg.check_connection()
        username = me.get('username') or me.get('first_name') or 'bot'
        log.info('Connected to Telegram as @%s', username)
    except Exception as exc:
        _print_startup_hints(exc)

    try:
        tg.ensure_polling_mode()
        log.info('Polling mode enabled (webhook cleared if it was set)')
    except Exception as exc:
        log.warning('Could not switch bot to polling mode: %s', exc)

    last_update_id = 0
    last_webhook_check = time.time()
    last_heartbeat = time.time()
    heartbeat_interval = int(os.getenv('BOT_HEARTBEAT_SECONDS', '1800'))

    while not _shutdown_requested:
        try:
            now = time.time()
            if now - last_webhook_check >= 60:
                try:
                    webhook_url = (tg.get_webhook_info().get('url') or '').strip()
                    if webhook_url:
                        log.warning('Webhook re-appeared (%s); clearing for polling...', webhook_url)
                        tg.delete_webhook()
                except Exception as exc:
                    log.warning('Webhook check failed: %s', exc)
                last_webhook_check = now

            if now - last_heartbeat >= heartbeat_interval:
                _log_heartbeat(last_update_id)
                last_heartbeat = now

            updates = tg.get_updates(offset=last_update_id + 1)
            if updates:
                callbacks = sum(1 for item in updates if 'callback_query' in item)
                if callbacks:
                    log.info('Polling batch: %s update(s), %s callback(s)', len(updates), callbacks)

            for update in updates:
                uid = update.get('update_id', 0)
                if uid > last_update_id:
                    last_update_id = uid
                _process_update(handlers, update)

        except KeyboardInterrupt:
            log.info('Stopped by keyboard interrupt')
            break
        except RequestException as exc:
            if _is_duplicate_poll_error(exc):
                log.error(
                    'Another process is polling the same bot token. '
                    'Stop duplicate swingfox_telegram containers.'
                )
                time.sleep(5)
                continue
            if _is_webhook_conflict_error(exc):
                log.warning('Webhook conflict detected; clearing webhook and resuming polling...')
                try:
                    tg.delete_webhook()
                except Exception as clear_exc:
                    log.exception('Failed to clear webhook: %s', clear_exc)
                time.sleep(2)
                continue
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            log.exception('Polling request error: %s', exc)
            time.sleep(5)
        except Exception as exc:
            if _is_duplicate_poll_error(exc):
                log.error(
                    'Another process is polling the same bot token. '
                    'Stop duplicate swingfox_telegram containers.'
                )
                time.sleep(5)
                continue
            if _is_webhook_conflict_error(exc):
                log.warning('Webhook conflict detected; clearing webhook and resuming polling...')
                try:
                    tg.delete_webhook()
                except Exception as clear_exc:
                    log.exception('Failed to clear webhook: %s', clear_exc)
                time.sleep(2)
                continue
            if _is_transient_poll_error(exc):
                time.sleep(2)
                continue
            log.exception('Polling loop error: %s', exc)
            time.sleep(5)

    log.info('Polling loop exited')


def main() -> None:
    faulthandler.enable()
    signal.signal(signal.SIGTERM, _on_shutdown_signal)
    signal.signal(signal.SIGINT, _on_shutdown_signal)

    if not os.getenv('TELEGRAM_SECRET'):
        log.error('TELEGRAM_SECRET is not set')
        raise SystemExit('Set TELEGRAM_SECRET in .env')

    try:
        run_polling()
    except Exception:
        log.exception('Fatal error — bot process exiting')
        raise


if __name__ == '__main__':
    setup_bot_logging()
    main()
