"""In-memory FSM for bot conversation state."""

from typing import Any, Dict, List, Optional


class SessionStore:
    def __init__(self):
        self._data: Dict[int, Dict[str, Any]] = {}

    def get(self, telegram_id: int) -> Dict[str, Any]:
        return self._data.setdefault(int(telegram_id), {})

    def set_state(self, telegram_id: int, state: Optional[str], **extra) -> None:
        entry = self.get(telegram_id)
        if state is None:
            entry.pop('state', None)
        else:
            entry['state'] = state
        entry.update(extra)

    def clear(self, telegram_id: int) -> None:
        self._data.pop(int(telegram_id), None)

    def get_state(self, telegram_id: int) -> Optional[str]:
        return self.get(telegram_id).get('state')

    def get_current_profile(self, telegram_id: int) -> Optional[str]:
        return self.get(telegram_id).get('current_profile')

    def set_login(self, telegram_id: int, login: str) -> None:
        self.get(telegram_id)['login'] = login

    def get_login(self, telegram_id: int) -> Optional[str]:
        return self.get(telegram_id).get('login')

    def set_last_swipe_message(self, telegram_id: int, chat_id: int, message_id: int) -> None:
        self.get(telegram_id)['last_swipe'] = {'chat_id': chat_id, 'message_id': message_id}

    def get_last_swipe_message(self, telegram_id: int) -> Optional[Dict[str, int]]:
        return self.get(telegram_id).get('last_swipe')

    def set_ads(self, telegram_id: int, ads: List[dict]) -> None:
        entry = self.get(telegram_id)
        entry['ads_list'] = ads
        entry['ads_index'] = 0

    def get_ads_state(self, telegram_id: int) -> tuple:
        entry = self.get(telegram_id)
        return entry.get('ads_list', []), entry.get('ads_index', 0)

    def set_ads_index(self, telegram_id: int, index: int) -> None:
        self.get(telegram_id)['ads_index'] = index


session_store = SessionStore()
