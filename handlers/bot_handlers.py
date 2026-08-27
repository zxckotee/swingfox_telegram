import os
from typing import Optional

from api.swingfox_client import SwingfoxAPIError, SwingfoxClient
from state.session_store import session_store
from telegram.client import TelegramClient

UPLOADS_URL = (os.getenv('SWINGFOX_UPLOADS_URL') or 'https://swingfox.ru/uploads').rstrip('/')
SITE_URL = os.getenv('PUBLIC_WEB_URL', 'https://swingfox.ru')


def avatar_url(filename: Optional[str]) -> Optional[str]:
    if not filename or filename == 'no_photo.jpg':
        return None
    return f"{UPLOADS_URL}/{filename.lstrip('/')}"


def format_profile_caption(profile: dict) -> str:
    p = profile.get('profile', profile)
    parts = [
        f"<b>{p.get('login', '—')}</b>",
        p.get('status') or '',
        p.get('city') or '',
        p.get('info') or ''
    ]
    if p.get('telegram_link'):
        parts.append(f"Telegram: {p['telegram_link']}")
    elif p.get('mobile'):
        parts.append(f"Контакт: {p['mobile']}")
    return '\n'.join(x for x in parts if x)[:1024]


class BotHandlers:
    def __init__(self, api: SwingfoxClient):
        self.api = api
        self.tg = TelegramClient()

    def handle_start(self, chat_id: int, user_id: int, text: str, username: Optional[str]) -> None:
        if text.startswith('/start link_'):
            code = text.replace('/start link_', '', 1).strip()
            try:
                data = self.api.complete_link(user_id, code, username)
                login = data.get('user', {}).get('login', '')
                self.tg.send_message(
                    chat_id,
                    f"✅ Аккаунт <b>{login}</b> привязан!\n\nИспользуйте меню ниже.",
                    reply_markup=self.tg.main_menu_keyboard(),
                    parse_mode='HTML'
                )
                session_store.clear(user_id)
            except SwingfoxAPIError as e:
                self.tg.send_message(chat_id, f"❌ {e.message}")
            except Exception as e:
                print(f'Link complete failed for {user_id}: {e}')
                self.tg.send_message(
                    chat_id,
                    "❌ Не удалось привязать аккаунт. Проверьте, что ссылка свежая (15 мин) "
                    "и backend доступен боту."
                )
            return

        if not self.api.get_token(user_id):
            self.tg.send_message(
                chat_id,
                "👋 Привет! Чтобы пользоваться ботом, привяжите аккаунт SwingFox.\n\n"
                "Откройте профиль на сайте → раздел «Telegram-бот» → получите ссылку и нажмите её.",
                reply_markup={'remove_keyboard': True}
            )
            return

        self.tg.send_message(
            chat_id,
            "С возвращением! Выберите действие в меню.",
            reply_markup=self.tg.main_menu_keyboard()
        )

    def handle_text(self, chat_id: int, user_id: int, text: str) -> None:
        if not self.api.get_token(user_id):
            self.tg.send_message(chat_id, "Сначала привяжите аккаунт через ссылку из профиля на swingfox.ru")
            return

        if text == '🔥 Анкеты':
            self.show_next_profile(chat_id, user_id)
        elif text == '🔔 Уведомления':
            self.show_notifications(chat_id, user_id)
        elif text == '💬 Чаты':
            self.show_chats(chat_id, user_id)
        elif text == '🎪 Клубы':
            self.show_clubs(chat_id, user_id)
        elif text == '📢 Объявления':
            self.show_ads(chat_id, user_id)
        elif text == '🌐 ЛК на сайте':
            self.send_web_login(chat_id, user_id)
        else:
            self.tg.send_message(chat_id, "Выберите пункт меню 👇", reply_markup=self.tg.main_menu_keyboard())

    def show_next_profile(self, chat_id: int, user_id: int) -> None:
        try:
            profiles = self.api.get_swipe_profiles(user_id)
            if not profiles:
                self.tg.send_message(chat_id, "Анкеты закончились. Загляните позже!")
                return
            profile = profiles[0]
            login = profile.get('login') or profile.get('profile', {}).get('login')
            caption = format_profile_caption({'profile': profile})
            ava = avatar_url(profile.get('ava') or profile.get('profile', {}).get('ava'))
            keyboard = self.tg.create_inline_keyboard([
                [
                    {'text': '❤️', 'callback_data': f'like:{login}'},
                    {'text': '👎', 'callback_data': f'dislike:{login}'},
                    {'text': '➡️', 'callback_data': 'swipe:next'}
                ]
            ])
            if ava:
                self.tg.send_photo(chat_id, ava, caption, reply_markup=keyboard)
            else:
                self.tg.send_message(chat_id, caption, reply_markup=keyboard, parse_mode='HTML')
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_notifications(self, chat_id: int, user_id: int) -> None:
        try:
            data = self.api.get_notifications(user_id)
            items = data.get('notifications', [])
            if not items:
                self.tg.send_message(chat_id, "Нет новых уведомлений.")
                return
            lines = []
            for n in items[:10]:
                lines.append(f"• [{n.get('type')}] {n.get('title')}: {n.get('message')}")
            self.tg.send_message(chat_id, '\n'.join(lines))
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_chats(self, chat_id: int, user_id: int) -> None:
        try:
            data = self.api.get_chats(user_id)
            chats = data.get('conversations', []) if isinstance(data, dict) else data
            if not chats:
                self.tg.send_message(chat_id, "Чатов пока нет.")
                return
            lines = []
            for c in chats[:15]:
                partner = c.get('companion') or c.get('partner') or c.get('login')
                unread = c.get('unread_count', 0)
                lines.append(f"• {partner}" + (f" ({unread} новых)" if unread else ''))
            self.tg.send_message(
                chat_id,
                "Ваши диалоги:\n" + '\n'.join(lines) + "\n\nОткрыть чат — на сайте.",
                reply_markup=self.tg.create_inline_keyboard([[{'text': 'Открыть чаты', 'url': f'{SITE_URL}/chat'}]])
            )
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_clubs(self, chat_id: int, user_id: int) -> None:
        try:
            data = self.api.get_clubs(user_id)
            clubs = data.get('clubs', data) if isinstance(data, dict) else data
            if not clubs:
                self.tg.send_message(chat_id, "Клубы не найдены.")
                return
            lines = [f"• {c.get('name', c.get('id'))}" for c in clubs[:10]]
            self.tg.send_message(
                chat_id,
                "Клубы:\n" + '\n'.join(lines),
                reply_markup=self.tg.create_inline_keyboard([[{'text': 'Все клубы', 'url': f'{SITE_URL}/clubs'}]])
            )
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_ads(self, chat_id: int, user_id: int) -> None:
        try:
            data = self.api.get_ads(user_id)
            ads = data.get('ads', data) if isinstance(data, dict) else data
            if not ads:
                self.tg.send_message(chat_id, "Объявлений нет.")
                return
            lines = [f"• {a.get('title', a.get('id'))}" for a in ads[:10]]
            self.tg.send_message(
                chat_id,
                "Объявления:\n" + '\n'.join(lines),
                reply_markup=self.tg.create_inline_keyboard([[{'text': 'Витрина', 'url': f'{SITE_URL}/ads'}]])
            )
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def send_web_login(self, chat_id: int, user_id: int) -> None:
        try:
            data = self.api.web_login_code(user_id)
            url = data.get('url')
            if not url:
                self.tg.send_message(chat_id, "Не удалось получить ссылку.")
                return
            self.tg.send_message(
                chat_id,
                "Нажмите кнопку, чтобы открыть личный кабинет на сайте в вашей сессии:",
                reply_markup=self.tg.create_inline_keyboard([[{'text': '🌐 Открыть SwingFox', 'url': url}]])
            )
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def handle_callback(self, callback_query: dict) -> None:
        cb_id = callback_query['id']
        chat_id = callback_query['message']['chat']['id']
        user_id = callback_query['from']['id']
        data = callback_query.get('data', '')

        if not self.api.get_token(user_id):
            self.tg.answer_callback_query(cb_id, 'Привяжите аккаунт на сайте', show_alert=True)
            return

        try:
            if data.startswith('like:'):
                login = data.split(':', 1)[1]
                result = self.api.like(user_id, login)
                msg = '💕 Взаимная симпатия!' if result.get('match') else '❤️ Лайк отправлен'
                self.tg.answer_callback_query(cb_id, msg)
                self.show_next_profile(chat_id, user_id)
            elif data.startswith('dislike:'):
                login = data.split(':', 1)[1]
                self.api.dislike(user_id, login)
                self.tg.answer_callback_query(cb_id, 'Пропущено')
                self.show_next_profile(chat_id, user_id)
            elif data == 'swipe:next':
                self.tg.answer_callback_query(cb_id)
                self.show_next_profile(chat_id, user_id)
            else:
                self.tg.answer_callback_query(cb_id)
        except SwingfoxAPIError as e:
            self.tg.answer_callback_query(cb_id, e.message[:200], show_alert=True)
            self.handle_api_error(chat_id, user_id, e)

    def handle_api_error(self, chat_id: int, user_id: int, error: SwingfoxAPIError) -> None:
        if error.error == 'like_limit':
            self.tg.send_message(
                chat_id,
                f"⚠️ {error.message}",
                reply_markup=self.tg.create_inline_keyboard([[{'text': 'VIP на сайте', 'url': f'{SITE_URL}/profile'}]])
            )
        elif error.error == 'no_root':
            self.tg.send_message(
                chat_id,
                f"⚠️ {error.message}",
                reply_markup=self.tg.create_inline_keyboard([[{'text': 'Оформить VIP', 'url': f'{SITE_URL}/profile'}]])
            )
        elif error.error in ('invalid_token', 'token_expired', 'not_linked'):
            self.api._tokens.pop(user_id, None)
            self.tg.send_message(
                chat_id,
                "Сессия устарела. Перепривяжите Telegram через ссылку в профиле на сайте."
            )
        else:
            self.tg.send_message(chat_id, f"Ошибка: {error.message}")
