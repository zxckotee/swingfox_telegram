import json
import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_SECRET')
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'


class TelegramClient:
    @staticmethod
    def create_reply_keyboard(buttons: List[List[str]], resize_keyboard: bool = True) -> dict:
        return {
            'keyboard': [[{'text': t} for t in row] for row in buttons],
            'resize_keyboard': resize_keyboard
        }

    @staticmethod
    def create_inline_keyboard(rows: List[List[dict]]) -> dict:
        return {'inline_keyboard': rows}

    @staticmethod
    def send_message(
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
        response = requests.post(f'{BASE_URL}/sendMessage', data=payload, timeout=30)
        return response.json()

    @staticmethod
    def send_photo(chat_id: int, photo_url: str, caption: str = '', reply_markup: Optional[dict] = None) -> dict:
        payload: Dict[str, Any] = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        response = requests.post(f'{BASE_URL}/sendPhoto', data=payload, timeout=30)
        return response.json()

    @staticmethod
    def answer_callback_query(callback_query_id: str, text: str = '', show_alert: bool = False) -> dict:
        response = requests.post(f'{BASE_URL}/answerCallbackQuery', data={
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        }, timeout=15)
        return response.json()

    @staticmethod
    def get_updates(offset: Optional[int] = None, timeout: int = 30) -> list:
        params: Dict[str, Any] = {
            'timeout': timeout,
            'allowed_updates': ['message', 'callback_query']
        }
        if offset is not None:
            params['offset'] = offset
        response = requests.get(f'{BASE_URL}/getUpdates', params=params, timeout=timeout + 5)
        return response.json().get('result', [])

    @staticmethod
    def main_menu_keyboard() -> dict:
        return TelegramClient.create_reply_keyboard([
            ['🔥 Анкеты', '🔔 Уведомления'],
            ['💬 Чаты', '🎪 Клубы'],
            ['📢 Объявления', '🌐 ЛК на сайте']
        ])
