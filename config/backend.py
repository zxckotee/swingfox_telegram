import os
from typing import TypedDict


class BackendConfig(TypedDict):
    production: bool
    api_url: str
    uploads_url: str
    web_url: str


_PROD = {
    'api_url': 'https://127.0.0.1:3001/api',
    'uploads_url': 'https://swingfox.ru/uploads',
    'web_url': 'https://swingfox.ru',
}

_STAGING = {
    'api_url': 'https://127.0.0.1:3002/api',
    'uploads_url': 'https://swingfox.ru/stagging/uploads',
    'web_url': 'https://swingfox.ru/stagging',
}


def is_production() -> bool:
    """PRODUCTION=on → prod backend; off/empty (default) → staging."""
    value = (os.getenv('PRODUCTION') or 'off').strip().lower()
    return value in ('1', 'true', 'yes', 'on')


def get_backend_config() -> BackendConfig:
    defaults = _PROD if is_production() else _STAGING
    return {
        'production': is_production(),
        'api_url': (os.getenv('SWINGFOX_API_URL') or defaults['api_url']).rstrip('/'),
        'uploads_url': (os.getenv('SWINGFOX_UPLOADS_URL') or defaults['uploads_url']).rstrip('/'),
        'web_url': (os.getenv('PUBLIC_WEB_URL') or defaults['web_url']).rstrip('/'),
    }
