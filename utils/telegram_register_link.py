import base64
import hashlib
import hmac
import json
import os
from typing import Optional


def build_register_url(telegram_id: int, base_url: str) -> Optional[str]:
    secret = os.getenv('TELEGRAM_BOT_SHARED_SECRET', '').strip()
    if not secret:
        return None
    tid = str(telegram_id)
    sig = hmac.new(
        secret.encode(),
        f'register:{tid}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    token = base64.urlsafe_b64encode(
        json.dumps({'tid': tid, 'sig': sig}, separators=(',', ':')).encode()
    ).decode().rstrip('=')
    return f"{base_url.rstrip('/')}/register?tg_code={token}"
