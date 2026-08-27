import hashlib
import hmac
import os
import time
import warnings
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from urllib3.exceptions import InsecureRequestWarning

from config.backend import get_backend_config


class SwingfoxClient:
    """HTTP-клиент SwingFox API. Без auth/password — только пользовательский JWT."""

    def __init__(self, api_url: Optional[str] = None, shared_secret: Optional[str] = None):
        backend = get_backend_config()
        self.api_url = (api_url or backend['api_url']).rstrip('/')
        self.shared_secret = shared_secret or os.getenv('TELEGRAM_BOT_SHARED_SECRET', '')
        self._tokens: Dict[int, str] = {}
        self._verify_ssl = self._resolve_ssl_verify()

    def _resolve_ssl_verify(self) -> bool:
        explicit = os.getenv('SWINGFOX_API_VERIFY')
        if explicit is not None:
            return explicit.lower() in ('1', 'true', 'yes')
        host = (urlparse(self.api_url).hostname or '').lower()
        if host in ('127.0.0.1', 'localhost', '::1'):
            return False
        return True

    def set_token(self, telegram_id: int, token: str) -> None:
        self._tokens[int(telegram_id)] = token

    def get_token(self, telegram_id: int) -> Optional[str]:
        return self._tokens.get(int(telegram_id))

    def _sign(self, telegram_id: int) -> Dict[str, Any]:
        ts = int(time.time())
        payload = f"{telegram_id}:{ts}"
        signature = hmac.new(
            self.shared_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            'telegram_id': str(telegram_id),
            'timestamp': ts,
            'signature': signature
        }

    def _request(
        self,
        method: str,
        path: str,
        telegram_id: Optional[int] = None,
        *,
        json: Optional[dict] = None,
        auth: bool = True,
        retry_refresh: bool = True
    ) -> Any:
        headers = {'Content-Type': 'application/json'}
        if auth and telegram_id is not None:
            token = self.get_token(telegram_id)
            if token:
                headers['Authorization'] = f'Bearer {token}'

        url = f"{self.api_url}{path}"
        if not self._verify_ssl:
            warnings.filterwarnings('ignore', category=InsecureRequestWarning)
        try:
            response = requests.request(
                method, url, headers=headers, json=json, timeout=30, verify=self._verify_ssl
            )
        except requests.RequestException as exc:
            raise SwingfoxAPIError(503, {
                'error': 'backend_unreachable',
                'message': f'Backend недоступен: {exc}'
            }) from exc
        data = {}
        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code in (401, 403) and auth and telegram_id and retry_refresh:
            err = data.get('error', '')
            if err in ('token_expired', 'invalid_token') and self.refresh_token(telegram_id):
                return self._request(method, path, telegram_id, json=json, auth=auth, retry_refresh=False)

        if response.status_code >= 400:
            raise SwingfoxAPIError(response.status_code, data)
        return data

    def complete_link(
        self,
        telegram_id: int,
        link_code: str,
        telegram_username: Optional[str] = None
    ) -> dict:
        body = {
            **self._sign(telegram_id),
            'link_code': link_code,
            'telegram_username': telegram_username
        }
        data = self._request('POST', '/telegram/link/complete', None, json=body, auth=False)
        if data.get('token'):
            self.set_token(telegram_id, data['token'])
        return data

    def refresh_token(self, telegram_id: int) -> bool:
        body = self._sign(telegram_id)
        try:
            data = self._request('POST', '/telegram/token/refresh', None, json=body, auth=False)
            if data.get('token'):
                self.set_token(telegram_id, data['token'])
                return True
        except SwingfoxAPIError:
            return False
        return False

    def web_login_code(self, telegram_id: int) -> dict:
        body = self._sign(telegram_id)
        return self._request('POST', '/telegram/web-login-code', None, json=body, auth=False)

    def get_swipe_profiles(self, telegram_id: int) -> list:
        data = self._request('GET', '/swipe/profiles', telegram_id)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and data.get('login'):
            return [data]
        return data.get('profiles', []) if isinstance(data, dict) else []

    def like(self, telegram_id: int, target_user: str) -> dict:
        return self._request('POST', '/swipe/like', telegram_id, json={
            'target_user': target_user,
            'source': 'telegram'
        })

    def dislike(self, telegram_id: int, target_user: str) -> dict:
        return self._request('POST', '/swipe/dislike', telegram_id, json={
            'target_user': target_user,
            'source': 'telegram'
        })

    def get_profile(self, telegram_id: int, login: str) -> dict:
        return self._request('GET', f'/profiles/{login}', telegram_id)

    def get_notifications(self, telegram_id: int, page: int = 1) -> dict:
        return self._request('GET', f'/notifications?page={page}&limit=10', telegram_id)

    def get_conversations(self, telegram_id: int) -> dict:
        return self._request('GET', '/chat/conversations', telegram_id)

    def get_chats(self, telegram_id: int) -> dict:
        return self.get_conversations(telegram_id)

    def get_clubs(self, telegram_id: int) -> dict:
        return self._request('GET', '/clubs', telegram_id)

    def get_ads(self, telegram_id: int) -> dict:
        return self._request('GET', '/ads?limit=10', telegram_id)


class SwingfoxAPIError(Exception):
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self.payload = payload
        self.error = payload.get('error', 'unknown')
        self.message = (
            payload.get('message')
            or payload.get('error')
            or f'HTTP {status_code}'
        )
        super().__init__(self.message)
