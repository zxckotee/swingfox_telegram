"""In-memory FSM for bot conversation state."""

from typing import Any, Dict, Optional


class SessionStore:
    def __init__(self):
        self._data: Dict[int, Dict[str, Any]] = {}

    def get(self, telegram_id: int) -> Dict[str, Any]:
        return self._data.setdefault(int(telegram_id), {})

    def set_state(self, telegram_id: int, state: str, **extra) -> None:
        entry = self.get(telegram_id)
        entry['state'] = state
        entry.update(extra)

    def clear(self, telegram_id: int) -> None:
        self._data.pop(int(telegram_id), None)

    def get_state(self, telegram_id: int) -> Optional[str]:
        return self.get(telegram_id).get('state')

    def get_current_profile(self, telegram_id: int) -> Optional[str]:
        return self.get(telegram_id).get('current_profile')


session_store = SessionStore()
