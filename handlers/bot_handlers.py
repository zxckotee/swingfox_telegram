import os
from typing import List, Optional

from api.swingfox_client import SwingfoxAPIError, SwingfoxClient
from config.backend import get_backend_config
from config.profile_options import FIELD_LABELS
from handlers.profile_pickers import field_uses_picker, format_multi_display, handle_picker_callback, start_picker
from state.session_store import session_store
from telegram.client import TelegramClient

_backend = get_backend_config()
UPLOADS_URL = _backend['uploads_url']
SITE_URL = _backend['web_url']

PROFILE_EDIT_FIELDS = {
    'city': 'город',
    'status': 'статус',
    'info': 'о себе',
    'search_status': 'кого ищу',
    'search_age': 'возраст для поиска',
    'mobile': 'контакт',
    'height': 'рост',
    'weight': 'вес',
    'smoking': 'курение',
    'alko': 'алкоголь',
}


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


def format_my_profile_caption(profile: dict) -> str:
    lines = [
        f"<b>Мой профиль — {profile.get('login', '—')}</b>",
        f"Статус: {profile.get('status') or '—'}",
        f"Город: {profile.get('city') or '—'}",
        f"Кого ищу: {format_multi_display(profile.get('search_status') or '')}",
        f"Возраст: {profile.get('search_age') or '—'}",
        f"О себе: {(profile.get('info') or '—')[:200]}",
    ]
    if profile.get('mobile'):
        lines.append(f"Контакт: {profile.get('mobile')}")
    return '\n'.join(lines)[:1024]


class BotHandlers:
    def __init__(self, api: SwingfoxClient):
        self.api = api
        self.tg = TelegramClient()

    @staticmethod
    def _parse_link_start(text: str) -> Optional[str]:
        parts = text.strip().split(maxsplit=1)
        if not parts or not parts[0].startswith('/start'):
            return None
        if len(parts) < 2:
            return None
        payload = parts[1].strip()
        if payload.startswith('link_'):
            return payload[5:]
        return None

    def _welcome_back(self, chat_id: int, message: str = "С возвращением! Выберите действие в меню.") -> None:
        self.tg.send_message(
            chat_id,
            message,
            reply_markup=self.tg.main_menu_keyboard()
        )

    def _prompt_link(self, chat_id: int) -> None:
        self.tg.send_message(
            chat_id,
            "👋 Привет! Чтобы пользоваться ботом, привяжите аккаунт SwingFox.\n\n"
            "Откройте профиль на сайте → раздел «Telegram-бот» → получите ссылку и нажмите её.",
            reply_markup={'remove_keyboard': True}
        )

    def _require_auth(self, chat_id: int, user_id: int) -> bool:
        if self.api.ensure_authenticated(user_id):
            return True
        self._send_auth_failure(chat_id, user_id)
        return False

    def _send_auth_failure(self, chat_id: int, user_id: int) -> None:
        reason = self.api.last_auth_error or 'not_linked'
        if reason == 'not_linked':
            self.tg.send_message(
                chat_id,
                "Сначала привяжите аккаунт через ссылку из профиля на swingfox.ru"
            )
        elif reason in ('invalid_signature', 'missing_shared_secret', 'backend_unreachable'):
            self.tg.send_message(
                chat_id,
                "⚠️ Временная ошибка авторизации. Нажмите /start через минуту."
            )
        else:
            self.tg.send_message(
                chat_id,
                "Сессия сброшена. Нажмите /start — если Telegram привязан в профиле, "
                "вход восстановится автоматически."
            )

    def _profile_search_ready(self, profile: dict) -> bool:
        return bool((profile.get('search_status') or '').strip() and (profile.get('search_age') or '').strip())

    def _clear_swipe_keyboard(self, user_id: int) -> None:
        last = session_store.get_last_swipe_message(user_id)
        if not last:
            return
        try:
            self.tg.edit_message_reply_markup(
                last['chat_id'],
                last['message_id'],
                {'inline_keyboard': []}
            )
        except Exception as exc:
            print(f'Failed to clear swipe keyboard: {exc}')

    def handle_start(self, chat_id: int, user_id: int, text: str, username: Optional[str]) -> None:
        link_code = self._parse_link_start(text)
        if link_code is not None:
            try:
                data = self.api.complete_link(user_id, link_code, username)
                login = data.get('user', {}).get('login', '')
                if login:
                    session_store.set_login(user_id, login)
                self.tg.send_message(
                    chat_id,
                    f"✅ Аккаунт <b>{login}</b> привязан!\n\nИспользуйте меню ниже.",
                    reply_markup=self.tg.main_menu_keyboard(),
                    parse_mode='HTML'
                )
                session_store.clear(user_id)
                session_store.set_login(user_id, login)
            except SwingfoxAPIError as e:
                if e.error == 'telegram_already_linked' and self.api.refresh_token(user_id):
                    self._welcome_back(
                        chat_id,
                        "✅ Telegram уже был привязан — сессия восстановлена.\n\nВыберите действие в меню."
                    )
                else:
                    self.tg.send_message(chat_id, f"❌ {e.message}")
            except Exception as e:
                print(f'Link complete failed for {user_id}: {e}')
                self.tg.send_message(
                    chat_id,
                    "❌ Не удалось привязать аккаунт. Проверьте, что ссылка свежая (15 мин) "
                    "и backend доступен боту."
                )
            return

        if self.api.ensure_authenticated(user_id):
            self._welcome_back(chat_id)
            return

        if self.api.refresh_token(user_id):
            self._welcome_back(
                chat_id,
                "✅ Сессия восстановлена из базы. Выберите действие в меню."
            )
            return

        self._prompt_link(chat_id)

    def handle_text(self, chat_id: int, user_id: int, text: str) -> None:
        if not self._require_auth(chat_id, user_id):
            return

        state = session_store.get_state(user_id)
        if state and state.startswith('profile_edit:'):
            field = state.split(':', 1)[1]
            if field_uses_picker(field):
                self.tg.send_message(chat_id, "Используйте кнопки под сообщением для выбора значения.")
                return
            self._apply_profile_field(chat_id, user_id, field, text)
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
            self.show_ads(chat_id, user_id, page_index=0)
        elif text == '👤 Мой профиль':
            self.show_my_profile(chat_id, user_id)
        elif text == '🌐 ЛК на сайте':
            self.send_web_login(chat_id, user_id)
        else:
            self.tg.send_message(chat_id, "Выберите пункт меню 👇", reply_markup=self.tg.main_menu_keyboard())

    def handle_photo(self, chat_id: int, user_id: int, photo_sizes: list) -> None:
        if not self._require_auth(chat_id, user_id):
            return
        if session_store.get_state(user_id) != 'profile_edit:photo':
            self.tg.send_message(chat_id, "Отправьте фото в разделе «Мой профиль» → «Фото».")
            return
        try:
            best = max(photo_sizes, key=lambda p: p.get('file_size', 0))
            file_info = self.tg.get_file(best['file_id'])
            content = self.tg.download_file(file_info['file_path'])
            self.api.upload_avatar(user_id, content, 'avatar.jpg')
            session_store.set_state(user_id, None)
            self.tg.send_message(chat_id, "✅ Фото профиля обновлено.")
            self.show_my_profile(chat_id, user_id)
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)
        except Exception as e:
            print(f'Avatar upload failed: {e}')
            self.tg.send_message(chat_id, "❌ Не удалось загрузить фото.")

    def _apply_profile_field(self, chat_id: int, user_id: int, field: str, value: str) -> None:
        if not self.api.ensure_authenticated(user_id):
            self._send_auth_failure(chat_id, user_id)
            return
        try:
            payload = {field: value.strip()}
            self.api.call_with_auth_retry(
                user_id,
                lambda: self.api.update_profile(user_id, payload),
            )
            session_store.set_state(user_id, None)
            self.tg.send_message(
                chat_id,
                f"✅ Поле «{PROFILE_EDIT_FIELDS.get(field, FIELD_LABELS.get(field, field))}» обновлено."
            )
            self.show_my_profile(chat_id, user_id)
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_my_profile(self, chat_id: int, user_id: int) -> None:
        try:
            profile = self.api.get_my_profile(user_id)
            caption = format_my_profile_caption(profile)
            ava = avatar_url(profile.get('ava'))
            keyboard = self.tg.create_inline_keyboard([
                [{'text': 'Город', 'callback_data': 'profile:edit:city'},
                 {'text': 'Статус', 'callback_data': 'profile:edit:status'}],
                [{'text': 'О себе', 'callback_data': 'profile:edit:info'},
                 {'text': 'Кого ищу', 'callback_data': 'profile:edit:search_status'}],
                [{'text': 'Возраст', 'callback_data': 'profile:edit:search_age'},
                 {'text': 'Контакт', 'callback_data': 'profile:edit:mobile'}],
                [{'text': 'Рост', 'callback_data': 'profile:edit:height'},
                 {'text': 'Вес', 'callback_data': 'profile:edit:weight'}],
                [{'text': 'Курение', 'callback_data': 'profile:edit:smoking'},
                 {'text': 'Алкоголь', 'callback_data': 'profile:edit:alko'}],
                [{'text': '📷 Фото', 'callback_data': 'profile:edit:photo'}],
            ])
            if ava:
                self.tg.send_photo(chat_id, ava, caption, reply_markup=keyboard)
            else:
                self.tg.send_message(chat_id, caption, reply_markup=keyboard, parse_mode='HTML')
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_next_profile(self, chat_id: int, user_id: int, direction: str = 'forward') -> None:
        try:
            my_profile = {}
            try:
                my_profile = self.api.get_my_profile(user_id)
            except SwingfoxAPIError:
                pass

            if direction == 'forward' and my_profile and not self._profile_search_ready(my_profile):
                self.tg.send_message(
                    chat_id,
                    "⚠️ Заполните «кого ищу» и «возраст» в разделе «👤 Мой профиль», "
                    "чтобы смотреть анкеты.",
                    reply_markup=self.tg.create_inline_keyboard([
                        [{'text': 'Открыть профиль', 'callback_data': 'profile:open'}]
                    ])
                )
                return

            profile = self.api.get_swipe_profile(user_id, direction=direction)
            if not profile:
                self.tg.send_message(chat_id, "Анкеты закончились. Загляните позже!")
                return

            login = profile.get('login') or profile.get('profile', {}).get('login')
            caption = format_profile_caption({'profile': profile})
            ava = avatar_url(profile.get('ava') or profile.get('profile', {}).get('ava'))

            row1 = [
                {'text': '❤️', 'callback_data': f'like:{login}'},
                {'text': '👎', 'callback_data': f'dislike:{login}'},
            ]
            rows: List[list] = [row1]

            tg_link = profile.get('telegram_link')
            if tg_link:
                rows.append([{'text': '📱 Telegram', 'url': tg_link}])

            if (my_profile.get('viptype') or '') in ('VIP', 'PREMIUM'):
                rows.append([{'text': '↩️ Назад', 'callback_data': 'swipe:back'}])

            keyboard = self.tg.create_inline_keyboard(rows)
            if ava:
                sent = self.tg.send_photo(chat_id, ava, caption, reply_markup=keyboard)
            else:
                sent = self.tg.send_message(chat_id, caption, reply_markup=keyboard, parse_mode='HTML')
            message = sent.get('result') or {}
            if message.get('message_id'):
                session_store.set_last_swipe_message(user_id, chat_id, message['message_id'])
        except SwingfoxAPIError as e:
            if e.error in ('no_previous', 'no_profiles'):
                self.tg.send_message(chat_id, e.message)
            else:
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
                info = c.get('companion_info') or {}
                tg_link = info.get('telegram_link')
                tg_username = info.get('telegram_username')
                line = f"• <b>{partner}</b>"
                if unread:
                    line += f" ({unread} новых)"
                if tg_link:
                    line += f"\n  📱 {tg_link}"
                elif tg_username:
                    line += f"\n  📱 @{tg_username}"
                lines.append(line)
            login_url = self.api.web_login_code(user_id, redirect_to='/chat').get('url')
            buttons = []
            if login_url:
                buttons.append([{'text': '💬 Открыть чаты на сайте', 'url': login_url}])
            self.tg.send_message(
                chat_id,
                "Ваши диалоги:\n" + '\n'.join(lines),
                reply_markup=self.tg.create_inline_keyboard(buttons) if buttons else None,
                parse_mode='HTML'
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
            lines = []
            buttons = []
            for c in clubs[:10]:
                name = c.get('name', c.get('id'))
                city = c.get('city') or ''
                lines.append(f"• <b>{name}</b>{f' — {city}' if city else ''}")
                tg_link = c.get('telegram_link')
                if tg_link:
                    buttons.append([{'text': f'📱 {name[:30]}', 'url': tg_link}])
            buttons.append([{'text': 'Все клубы на сайте', 'url': f'{SITE_URL}/clubs'}])
            self.tg.send_message(
                chat_id,
                "Клубы:\n" + '\n'.join(lines),
                reply_markup=self.tg.create_inline_keyboard(buttons),
                parse_mode='HTML'
            )
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def show_ads(self, chat_id: int, user_id: int, page_index: int = 0, edit_message: Optional[dict] = None) -> None:
        try:
            ads_list, _ = session_store.get_ads_state(user_id)
            if not ads_list or page_index == 0 and not edit_message:
                data = self.api.get_ads(user_id)
                ads_list = data.get('ads', data) if isinstance(data, dict) else data
                if not ads_list:
                    self.tg.send_message(chat_id, "Объявлений нет.")
                    return
                session_store.set_ads(user_id, ads_list)

            if page_index < 0:
                page_index = 0
            if page_index >= len(ads_list):
                page_index = len(ads_list) - 1
            session_store.set_ads_index(user_id, page_index)

            ad = ads_list[page_index]
            title = ad.get('title', 'Без названия')
            text = (
                f"<b>{title}</b>\n"
                f"{ad.get('type', '')} · {ad.get('city', '')}\n\n"
                f"{(ad.get('description') or '')[:800]}"
            )
            nav = []
            if len(ads_list) > 1:
                nav = [
                    {'text': '◀️', 'callback_data': 'ads:prev'},
                    {'text': f'{page_index + 1}/{len(ads_list)}', 'callback_data': 'ads:noop'},
                    {'text': '▶️', 'callback_data': 'ads:next'},
                ]
            keyboard_rows = []
            if nav:
                keyboard_rows.append(nav)
            keyboard_rows.append([{'text': 'Витрина на сайте', 'url': f'{SITE_URL}/ads'}])
            keyboard = self.tg.create_inline_keyboard(keyboard_rows)

            image = ad.get('image')
            if edit_message:
                self.tg.send_message(chat_id, text, reply_markup=keyboard, parse_mode='HTML')
            elif image:
                img_url = f"{UPLOADS_URL}/{str(image).lstrip('/')}"
                self.tg.send_photo(chat_id, img_url, text, reply_markup=keyboard)
            else:
                self.tg.send_message(chat_id, text, reply_markup=keyboard, parse_mode='HTML')
        except SwingfoxAPIError as e:
            self.handle_api_error(chat_id, user_id, e)

    def send_web_login(self, chat_id: int, user_id: int, redirect_to: Optional[str] = None) -> None:
        try:
            data = self.api.web_login_code(user_id, redirect_to=redirect_to)
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

        if not self.api.ensure_authenticated(user_id):
            self.tg.answer_callback_query(cb_id, 'Привяжите аккаунт на сайте', show_alert=True)
            return

        try:
            if data.startswith('like:'):
                login = data.split(':', 1)[1]
                self._clear_swipe_keyboard(user_id)
                result = self.api.like(user_id, login)
                msg = '💕 Взаимная симпатия!' if result.get('match') else '❤️ Лайк отправлен'
                self.tg.answer_callback_query(cb_id, msg)
                self.show_next_profile(chat_id, user_id)
            elif data.startswith('dislike:'):
                login = data.split(':', 1)[1]
                self._clear_swipe_keyboard(user_id)
                self.api.dislike(user_id, login)
                self.tg.answer_callback_query(cb_id, 'Пропущено')
                self.show_next_profile(chat_id, user_id)
            elif data == 'swipe:back':
                self.tg.answer_callback_query(cb_id)
                self.show_next_profile(chat_id, user_id, direction='back')
            elif data == 'profile:open':
                self.tg.answer_callback_query(cb_id)
                self.show_my_profile(chat_id, user_id)
            elif data.startswith('profile:edit:'):
                field = data.split(':', 2)[2]
                if field == 'photo':
                    session_store.set_state(user_id, 'profile_edit:photo')
                    self.tg.answer_callback_query(cb_id)
                    self.tg.send_message(chat_id, "Отправьте новое фото профиля.")
                elif field_uses_picker(field):
                    self.tg.answer_callback_query(cb_id)
                    try:
                        start_picker(self, chat_id, user_id, field)
                    except SwingfoxAPIError as e:
                        self.handle_api_error(chat_id, user_id, e)
                else:
                    session_store.set_state(user_id, f'profile_edit:{field}')
                    label = PROFILE_EDIT_FIELDS.get(field, field)
                    self.tg.answer_callback_query(cb_id)
                    self.tg.send_message(chat_id, f"Введите новое значение: <b>{label}</b>", parse_mode='HTML')
            elif data.startswith('prof:'):
                if not handle_picker_callback(self, chat_id, user_id, data, cb_id):
                    self.tg.answer_callback_query(cb_id)
            elif data == 'ads:prev':
                ads_list, idx = session_store.get_ads_state(user_id)
                self.tg.answer_callback_query(cb_id)
                self.show_ads(chat_id, user_id, page_index=max(0, idx - 1), edit_message=callback_query.get('message'))
            elif data == 'ads:next':
                ads_list, idx = session_store.get_ads_state(user_id)
                self.tg.answer_callback_query(cb_id)
                next_idx = idx + 1 if idx + 1 < len(ads_list) else 0
                self.show_ads(chat_id, user_id, page_index=next_idx, edit_message=callback_query.get('message'))
            elif data == 'ads:noop':
                self.tg.answer_callback_query(cb_id)
            elif data.startswith('gi:accept:'):
                invite_id = data.split(':', 2)[2]
                self.api.accept_game_invite(user_id, invite_id)
                self.tg.answer_callback_query(cb_id, 'Приглашение принято ✅')
            elif data.startswith('gi:decline:'):
                invite_id = data.split(':', 2)[2]
                self.api.decline_game_invite(user_id, invite_id)
                self.tg.answer_callback_query(cb_id, 'Приглашение отклонено')
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
        elif error.error in ('invalid_token', 'token_expired'):
            if self.api.refresh_token(user_id):
                self.tg.send_message(
                    chat_id,
                    "Сессия обновлена. Повторите последнее действие."
                )
                return
            self.api.clear_token(user_id)
            self.tg.send_message(
                chat_id,
                "Сессия устарела. Нажмите /start — если Telegram привязан в профиле, "
                "вход восстановится автоматически."
            )
        elif error.error == 'not_linked':
            self.api.clear_token(user_id)
            self.tg.send_message(
                chat_id,
                "Сессия устарела. Перепривяжите Telegram через ссылку в профиле на сайте."
            )
        else:
            self.tg.send_message(chat_id, f"Ошибка: {error.message}")
