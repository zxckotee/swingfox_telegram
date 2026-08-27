import json
import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout, RequestException
from urllib3.exceptions import ProtocolError

load_dotenv()

TOKEN = os.getenv('TELEGRAM_SECRET', '').strip()
API_BASE = os.getenv('TELEGRAM_API_BASE_URL', 'https://api.telegram.org').rstrip('/')
BASE_URL = f'{API_BASE}/bot{TOKEN}' if TOKEN else ''

PROXIES = None
_proxy_url = os.getenv('TELEGRAM_PROXY', '').strip()
if _proxy_url:
    PROXIES = {'http': _proxy_url, 'https': _proxy_url}

POST_RETRIES = 3


def _sanitize_error(message: str) -> str:
    if TOKEN:
        message = message.replace(TOKEN, '***')
    return message


def _is_transient_poll_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    markers = (
        'remote end closed connection',
        'connection aborted',
        'connection reset',
        'read timed out',
        'network is unreachable',
        'failed to establish a new connection',
    )
    return any(m in text for m in markers)


class TelegramClient:
    """Telegram Bot API client with legacy-style long polling."""

    @staticmethod
    def create_reply_keyboard(buttons: List[List[str]], resize_keyboard: bool = True) -> dict:
        return {
            'keyboard': [[{'text': t} for t in row] for row in buttons],
            'resize_keyboard': resize_keyboard
        }

    @staticmethod
    def create_inline_keyboard(rows: List[List[dict]]) -> dict:
        return {'inline_keyboard': rows}

    def _post(self, path: str, payload: Dict[str, Any]) -> dict:
        last_error: Optional[Exception] = None
        for attempt in range(POST_RETRIES):
            try:
                response = requests.post(
                    f'{BASE_URL}/{path}',
                    data=payload,
                    proxies=PROXIES,
                    timeout=(15, 60)
                )
                data = response.json()
                if not data.get('ok', True):
                    description = data.get('description') or 'Telegram API error'
                    raise RuntimeError(_sanitize_error(str(description)))
                return data
            except (RequestException, ProtocolError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 < POST_RETRIES and _is_transient_poll_error(exc):
                    continue
                raise RuntimeError(_sanitize_error(str(exc))) from exc
        raise RuntimeError(_sanitize_error(str(last_error))) from last_error

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[dict] = None,
        parse_mode: Optional[str] = None
    ) -> dict:
        payload: Dict[str, Any] = {
            'chat_id': chat_id,
            'text': text,
        }
        if parse_mode:
            payload['parse_mode'] = parse_mode
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        return self._post('sendMessage', payload)

    def send_photo(self, chat_id: int, photo_url: str, caption: str = '', reply_markup: Optional[dict] = None) -> dict:
        payload: Dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        return self._post('sendPhoto', payload)

    def answer_callback_query(self, callback_query_id: str, text: str = '', show_alert: bool = False) -> dict:
        return self._post('answerCallbackQuery', {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        })

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> list:
        params: Dict[str, Any] = {
            'timeout': timeout,
            'allowed_updates': ['message', 'callback_query']
        }
        if offset:
            params['offset'] = offset

        try:
            response = requests.get(
                f'{BASE_URL}/getUpdates',
                params=params,
                proxies=PROXIES,
                timeout=(15, timeout + 20)
            )
            data = response.json()
            if not data.get('ok', True):
                description = data.get('description') or 'getUpdates failed'
                raise RuntimeError(_sanitize_error(str(description)))
            return data.get('result', [])
        except (RequestException, ProtocolError, ReadTimeout, RequestsConnectionError) as exc:
            if _is_transient_poll_error(exc):
                return []
            raise RuntimeError(_sanitize_error(str(exc))) from exc

    def check_connection(self) -> dict:
        response = requests.get(f'{BASE_URL}/getMe', proxies=PROXIES, timeout=30)
        data = response.json()
        if not data.get('ok'):
            raise RuntimeError(data.get('description') or 'getMe failed')
        return data.get('result', {})

    @staticmethod
    def main_menu_keyboard() -> dict:
        return TelegramClient.create_reply_keyboard([
            ['🔥 Анкеты', '🔔 Уведомления'],
            ['💬 Чаты', '🎪 Клубы'],
            ['📢 Объявления', '🌐 ЛК на сайте']
        ])
