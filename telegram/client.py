import json
import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_SECRET', '').strip()
API_BASE = os.getenv('TELEGRAM_API_BASE_URL', 'https://api.telegram.org').rstrip('/')
BASE_URL = f'{API_BASE}/bot{TOKEN}' if TOKEN else ''

# Optional proxy — same env as before, applied per-request like legacy host setup + export http_proxy
PROXIES = None
_proxy_url = os.getenv('TELEGRAM_PROXY', '').strip()
if _proxy_url:
    PROXIES = {'http': _proxy_url, 'https': _proxy_url}


def _sanitize_error(message: str) -> str:
    if TOKEN:
        message = message.replace(TOKEN, '***')
    return message


class TelegramClient:
    """Telegram Bot API client.

    Long polling (getUpdates) intentionally mirrors the legacy tg_methods.py:
    plain requests.get/post without requests-level timeout, because Telegram
    holds the HTTP connection open for `timeout` seconds on their side.
    """

    @staticmethod
    def create_reply_keyboard(buttons: List[List[str]], resize_keyboard: bool = True) -> dict:
        return {
            'keyboard': [[{'text': t} for t in row] for row in buttons],
            'resize_keyboard': resize_keyboard
        }

    @staticmethod
    def create_inline_keyboard(rows: List[List[dict]]) -> dict:
        return {'inline_keyboard': rows}

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
        response = requests.post(
            f'{BASE_URL}/sendMessage',
            data=payload,
            proxies=PROXIES
        )
        return response.json()

    def send_photo(self, chat_id: int, photo_url: str, caption: str = '', reply_markup: Optional[dict] = None) -> dict:
        payload: Dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        response = requests.post(
            f'{BASE_URL}/sendPhoto',
            data=payload,
            proxies=PROXIES
        )
        return response.json()

    def answer_callback_query(self, callback_query_id: str, text: str = '', show_alert: bool = False) -> dict:
        response = requests.post(f'{BASE_URL}/answerCallbackQuery', data={
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        }, proxies=PROXIES)
        return response.json()

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> list:
        """Long polling — same pattern as legacy tg_methods.get_updates()."""
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
                proxies=PROXIES
            )
            return response.json().get('result', [])
        except requests.RequestException as exc:
            raise RuntimeError(_sanitize_error(str(exc))) from exc

    def check_connection(self) -> dict:
        try:
            response = requests.get(f'{BASE_URL}/getMe', proxies=PROXIES, timeout=30)
            data = response.json()
            if not data.get('ok'):
                raise RuntimeError(data.get('description') or 'getMe failed')
            return data.get('result', {})
        except requests.RequestException as exc:
            raise RuntimeError(_sanitize_error(str(exc))) from exc

    @staticmethod
    def main_menu_keyboard() -> dict:
        return TelegramClient.create_reply_keyboard([
            ['🔥 Анкеты', '🔔 Уведомления'],
            ['💬 Чаты', '🎪 Клубы'],
            ['📢 Объявления', '🌐 ЛК на сайте']
        ])
