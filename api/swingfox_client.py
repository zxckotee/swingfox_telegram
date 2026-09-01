import base64
import hashlib
import hmac
import json
import os
import time
import warnings
from typing import Any, Callable, Dict, Optional, TypeVar
from urllib.parse import urlparse

import requests
from urllib3.exceptions import InsecureRequestWarning

from config.backend import get_backend_config
from state.token_store import token_store

AUTH_RETRY_ERRORS = frozenset({'invalid_token', 'token_expired'})
T = TypeVar('T')

AUTH_NOT_LINKED = 'not_linked'
AUTH_CONFIG = 'config'
AUTH_BACKEND_DOWN = 'backend_down'
AUTH_BACKEND_OUTDATED = 'backend_outdated'
AUTH_UNKNOWN = 'unknown'


def classify_auth_failure(error: Optional[str]) -> str:
    if not error or error == 'not_linked':
        return AUTH_NOT_LINKED
    if error in ('invalid_signature', 'missing_shared_secret'):
        return AUTH_CONFIG
    if error == 'backend_unreachable':
        return AUTH_BACKEND_DOWN
    if error == 'API endpoint не найден' or 'endpoint' in error.lower():
        return AUTH_BACKEND_OUTDATED
    return AUTH_UNKNOWN


class SwingfoxClient:
    """HTTP-клиент SwingFox API. Без auth/password — только пользовательский JWT."""

    def __init__(self, api_url: Optional[str] = None, shared_secret: Optional[str] = None):
        backend = get_backend_config()
        self.api_url = (api_url or backend['api_url']).rstrip('/')
        self.shared_secret = shared_secret or os.getenv('TELEGRAM_BOT_SHARED_SECRET', '')
        self._token_store = token_store
        self.last_auth_error: Optional[str] = None
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
        login = self._login_from_jwt(token)
        self._token_store.set(telegram_id, token, login=login)
        self.last_auth_error = None
        if login:
            from state.session_store import session_store
            session_store.set_login(telegram_id, login)

    def clear_token(self, telegram_id: int) -> None:
        self._token_store.pop(telegram_id)

    @staticmethod
    def _jwt_expired(token: str, leeway_sec: int = 60) -> bool:
        try:
            parts = token.split('.')
            if len(parts) < 2:
                return True
            pad = '=' * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
            exp = payload.get('exp')
            if not exp:
                return False
            return time.time() >= float(exp) - leeway_sec
        except Exception:
            return True

    @staticmethod
    def _login_from_jwt(token: str) -> Optional[str]:
        try:
            parts = token.split('.')
            if len(parts) < 2:
                return None
            pad = '=' * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
            return payload.get('login')
        except Exception:
            return None

    def resolve_login(self, telegram_id: int) -> Optional[str]:
        from state.session_store import session_store
        login = session_store.get_login(telegram_id)
        if login:
            return login
        login = self._token_store.get_login(telegram_id)
        if login:
            session_store.set_login(telegram_id, login)
            return login
        token = self.get_token(telegram_id)
        if token:
            login = self._login_from_jwt(token)
            if login:
                self._token_store.set_login(telegram_id, login)
                session_store.set_login(telegram_id, login)
            return login
        return None

    def get_token(self, telegram_id: int) -> Optional[str]:
        return self._token_store.get(telegram_id)

    def ensure_authenticated(self, telegram_id: int) -> bool:
        """Use persisted JWT or refresh from backend when missing/expired."""
        token = self.get_token(telegram_id)
        if token and not self._jwt_expired(token):
            return True
        return self.refresh_token(telegram_id)

    def call_with_auth_retry(self, telegram_id: int, fn: Callable[[], T]) -> T:
        """Run API call; on auth error refresh JWT once and retry."""
        try:
            return fn()
        except SwingfoxAPIError as exc:
            if exc.error not in AUTH_RETRY_ERRORS or not self.refresh_token(telegram_id):
                raise
            return fn()

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
        self.last_auth_error = None
        if not self.shared_secret:
            self.last_auth_error = 'missing_shared_secret'
            print(
                f'WARNING: refresh_token failed for {telegram_id}: '
                'TELEGRAM_BOT_SHARED_SECRET is not set'
            )
            return False

        body = self._sign(telegram_id)
        try:
            data = self._request('POST', '/telegram/token/refresh', None, json=body, auth=False)
            if data.get('token'):
                self.set_token(telegram_id, data['token'])
                return True
            self.last_auth_error = 'no_token_in_response'
        except SwingfoxAPIError as exc:
            self.last_auth_error = exc.error
            print(
                f'WARNING: refresh_token failed for {telegram_id}: '
                f'{exc.error} ({exc.message})'
            )
            return False
        return False

    def web_login_code(self, telegram_id: int, redirect_to: Optional[str] = None) -> dict:
        body = self._sign(telegram_id)
        if redirect_to:
            body['redirect_to'] = redirect_to
        return self._request('POST', '/telegram/web-login-code', None, json=body, auth=False)

    def get_swipe_profile(self, telegram_id: int, direction: str = 'forward') -> Optional[dict]:
        data = self._request('GET', f'/swipe/profiles?direction={direction}', telegram_id)
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict) and data.get('login'):
            return data
        if isinstance(data, dict):
            profiles = data.get('profiles') or []
            return profiles[0] if profiles else None
        return None

    def get_swipe_profiles(self, telegram_id: int) -> list:
        profile = self.get_swipe_profile(telegram_id)
        return [profile] if profile else []

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
        return self._request('GET', f'/users/profile/{login}', telegram_id)

    def get_my_profile(self, telegram_id: int) -> dict:
        login = self.resolve_login(telegram_id)
        if not login:
            raise SwingfoxAPIError(400, {
                'error': 'no_login',
                'message': 'Не удалось определить логин пользователя'
            })
        return self.get_profile(telegram_id, login)

    def update_profile(
        self,
        telegram_id: int,
        fields: Dict[str, Any],
        *,
        current: Optional[dict] = None,
    ) -> dict:
        if current is None:
            current = self.get_my_profile(telegram_id)
        payload = {
            'country': fields.get('country', current.get('country')),
            'city': fields.get('city', current.get('city')),
            'status': fields.get('status', current.get('status')),
            'search_status': fields.get('search_status', current.get('search_status')),
            'search_age': fields.get('search_age', current.get('search_age')),
            'location': fields.get('location', current.get('location')),
            'mobile': fields.get('mobile', current.get('mobile')),
            'info': fields.get('info', current.get('info')),
            'date': fields.get('date', current.get('date')),
            'height': fields.get('height', current.get('height')),
            'weight': fields.get('weight', current.get('weight')),
            'smoking': fields.get('smoking', current.get('smoking')),
            'alko': fields.get('alko', current.get('alko')),
        }
        return self._request('PUT', '/users/profile', telegram_id, json=payload)

    def upload_avatar(self, telegram_id: int, file_bytes: bytes, filename: str = 'avatar.jpg') -> dict:
        token = self.get_token(telegram_id)
        if not token:
            raise SwingfoxAPIError(401, {'error': 'not_authenticated', 'message': 'Нет токена'})
        headers = {'Authorization': f'Bearer {token}'}
        url = f'{self.api_url}/users/upload-avatar'
        if not self._verify_ssl:
            warnings.filterwarnings('ignore', category=InsecureRequestWarning)
        response = requests.post(
            url,
            headers=headers,
            files={'avatar': (filename, file_bytes, 'image/jpeg')},
            timeout=60,
            verify=self._verify_ssl
        )
        data = {}
        try:
            data = response.json()
        except Exception:
            data = {}
        if response.status_code >= 400:
            raise SwingfoxAPIError(response.status_code, data)
        return data

    def get_notifications(self, telegram_id: int, page: int = 1) -> dict:
        return self._request('GET', f'/notifications?page={page}&limit=10', telegram_id)

    def get_conversations(self, telegram_id: int) -> dict:
        return self._request('GET', '/chat/conversations', telegram_id)

    def get_chats(self, telegram_id: int) -> dict:
        return self.get_conversations(telegram_id)

    def get_clubs(self, telegram_id: int) -> dict:
        return self._request('GET', '/clubs', telegram_id)

    def get_ads(self, telegram_id: int) -> dict:
        return self._request('GET', '/ads?limit=20&telegram_bot=1', telegram_id)

    def accept_game_invite(self, telegram_id: int, invite_id: str) -> dict:
        return self._request('POST', f'/game/invites/{invite_id}/accept', telegram_id)

    def decline_game_invite(self, telegram_id: int, invite_id: str) -> dict:
        return self._request('POST', f'/game/invites/{invite_id}/decline', telegram_id)


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
