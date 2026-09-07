import unittest
from unittest.mock import MagicMock, patch

from handlers.bot_handlers import BotHandlers
from state.session_store import session_store
from telegram.client import TelegramClient


class MenuOverrideTest(unittest.TestCase):
    def setUp(self):
        session_store.clear(12345)
        self.api = MagicMock()
        self.api.ensure_authenticated.return_value = True
        self.handlers = BotHandlers(self.api)
        self.handlers.tg = MagicMock()

    def tearDown(self):
        session_store.clear(12345)

    def test_main_menu_buttons_constant(self):
        keyboard = TelegramClient.main_menu_keyboard()
        flat = [btn['text'] for row in keyboard['keyboard'] for btn in row]
        self.assertEqual(flat, list(TelegramClient.MAIN_MENU_BUTTONS))

    def test_menu_text_exits_profile_edit_state(self):
        session_store.set_state(12345, 'profile_edit:city')
        with patch.object(self.handlers, 'show_my_profile') as show_profile:
            self.handlers.handle_text(100, 12345, '👤 Мой профиль')
        self.assertIsNone(session_store.get_state(12345))
        show_profile.assert_called_once_with(100, 12345)

    def test_menu_text_exits_profile_pick_state(self):
        session_store.set_state(12345, 'profile_pick:status')
        session_store.set_pick_draft(12345, {'selected': []})
        with patch.object(self.handlers, 'show_next_profile') as show_swipe:
            self.handlers.handle_text(100, 12345, '🔥 Анкеты')
        self.assertIsNone(session_store.get_state(12345))
        self.assertEqual(session_store.get_pick_draft(12345), {})
        show_swipe.assert_called_once_with(100, 12345)

    def test_profile_edit_still_accepts_input(self):
        session_store.set_state(12345, 'profile_edit:city')
        with patch.object(self.handlers, '_apply_profile_field') as apply_field:
            self.handlers.handle_text(100, 12345, 'Москва')
        apply_field.assert_called_once_with(100, 12345, 'city', 'Москва')

    def test_profile_pick_rejects_non_menu_text(self):
        session_store.set_state(12345, 'profile_pick:status')
        self.handlers.handle_text(100, 12345, 'что-то')
        self.handlers.tg.send_message.assert_called_once()
        self.assertIn('кнопки', self.handlers.tg.send_message.call_args[0][1].lower())


if __name__ == '__main__':
    unittest.main()
