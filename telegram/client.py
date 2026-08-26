import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, '').strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=('GET', 'POST'),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=4)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    proxy = os.getenv('TELEGRAM_PROXY', '').strip()
    if proxy:
        session.proxies.update({'http': proxy, 'https': proxy})

    return session


def _sanitize_error(message: str) -> str:
    token = os.getenv('TELEGRAM_SECRET', '')
    if token:
        message = message.replace(token, '***')
    return message


class TelegramClient:
    def __init__(self) -> None:
        token = os.getenv('TELEGRAM_SECRET', '').strip()
        if not token:
            raise ValueError('TELEGRAM_SECRET is not set')

        api_base = os.getenv('TELEGRAM_API_BASE_URL', 'https://api.telegram.org').rstrip('/')
        self._token = token
        self.base_url = f'{api_base}/bot{token}'
        self.session = _build_session()
        self.connect_timeout = _env_int('TELEGRAM_CONNECT_TIMEOUT', 15)
        self.read_timeout = _env_int('TELEGRAM_READ_TIMEOUT', 75)

    def _timeout(self, read_timeout: Optional[int] = None) -> Tuple[int, int]:
        return self.connect_timeout, read_timeout or self.read_timeout

    def _request(self, method: str, path: str, *, timeout: Optional[Tuple[int, int]] = None, **kwargs: Any) -> dict:
        url = f'{self.base_url}/{path}'
        try:
            response = self.session.request(method, url, timeout=timeout or self._timeout(), **kwargs)
            response.raise_for_status()
            data = response.json()
            if not data.get('ok', True):
                description = data.get('description') or 'Telegram API error'
                raise RuntimeError(_sanitize_error(str(description)))
            return data
        except requests.RequestException as exc:
            raise RuntimeError(_sanitize_error(str(exc))) from exc

    def check_connection(self) -> dict:
        data = self._request('GET', 'getMe', timeout=(self.connect_timeout, 30))
        return data.get('result', {})

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
        return self._request('POST', 'sendMessage', data=payload, timeout=self._timeout(45))

    def send_photo(self, chat_id: int, photo_url: str, caption: str = '', reply_markup: Optional[dict] = None) -> dict:
        payload: Dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        return self._request('POST', 'sendPhoto', data=payload, timeout=self._timeout(45))

    def answer_callback_query(self, callback_query_id: str, text: str = '', show_alert: bool = False) -> dict:
        return self._request('POST', 'answerCallbackQuery', data={
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        }, timeout=self._timeout(30))

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> list:
        params: Dict[str, Any] = {
            'timeout': timeout,
            'allowed_updates': ['message', 'callback_query']
        }
        if offset is not None:
            params['offset'] = offset
        data = self._request(
            'GET',
            'getUpdates',
            params=params,
            timeout=(self.connect_timeout, timeout + 15)
        )
        return data.get('result', [])

    @staticmethod
    def main_menu_keyboard() -> dict:
        return TelegramClient.create_reply_keyboard([
            ['🔥 Анкеты', '🔔 Уведомления'],
            ['💬 Чаты', '🎪 Клубы'],
            ['📢 Объявления', '🌐 ЛК на сайте']
        ])
