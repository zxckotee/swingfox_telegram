"""Persistent JWT storage so bot restarts do not drop user sessions."""

import json
import os
import threading
from typing import Dict, Optional


class TokenStore:
    def __init__(self, path: Optional[str] = None):
        default_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'tokens.json'
        )
        self._path = os.path.abspath(path or os.getenv('TOKEN_STORE_PATH', default_path))
        self._lock = threading.Lock()
        self._tokens: Dict[int, str] = self._load()

    def _load(self) -> Dict[int, str]:
        if not os.path.isfile(self._path):
            return {}
        try:
            with open(self._path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
            return {int(key): value for key, value in raw.items() if value}
        except Exception as exc:
            print(f'WARNING: failed to load token store ({self._path}): {exc}')
            return {}

    def _save(self) -> None:
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {str(key): value for key, value in self._tokens.items() if value}
        tmp_path = f'{self._path}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle)
        os.replace(tmp_path, self._path)

    def get(self, telegram_id: int) -> Optional[str]:
        return self._tokens.get(int(telegram_id))

    def set(self, telegram_id: int, token: str) -> None:
        with self._lock:
            self._tokens[int(telegram_id)] = token
            self._save()

    def pop(self, telegram_id: int) -> None:
        with self._lock:
            if self._tokens.pop(int(telegram_id), None) is not None:
                self._save()

    def count(self) -> int:
        return len(self._tokens)
