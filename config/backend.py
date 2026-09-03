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


def rewrite_site_url(url: str, *, production: bool, web_url: str) -> str:
    """Map production site URLs to the configured web_url when bot runs on staging."""
    if production or not url:
        return url
    prod_web = _PROD['web_url'].rstrip('/')
    target_web = web_url.rstrip('/')
    if target_web == prod_web:
        return url
    if url == prod_web or url.startswith(f'{prod_web}/'):
        return f'{target_web}{url[len(prod_web):]}'
    return url


def rewrite_uploads_url(url: str, *, production: bool, uploads_url: str) -> str:
    """Map production upload URLs to the configured uploads_url when bot runs on staging."""
    if production or not url:
        return url
    prod_uploads = _PROD['uploads_url'].rstrip('/')
    target_uploads = uploads_url.rstrip('/')
    if target_uploads == prod_uploads:
        return url
    if url == prod_uploads or url.startswith(f'{prod_uploads}/'):
        return f'{target_uploads}{url[len(prod_uploads):]}'
    return url


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
