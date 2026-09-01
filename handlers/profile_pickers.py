"""Inline keyboards for profile fields with fixed options."""

from typing import TYPE_CHECKING, List, Optional, Set

from api.swingfox_client import SwingfoxAPIError
from config.profile_options import (
    FIELD_LABELS,
    LIFESTYLE_FIELDS,
    MULTI_PICKER_FIELDS,
    PICKER_FIELDS,
    display_value,
    is_couple_status,
    join_multi_field,
    options_for_field,
    option_value,
    split_multi_field,
)
from state.session_store import session_store

if TYPE_CHECKING:
    from handlers.bot_handlers import BotHandlers


def field_uses_picker(field: str) -> bool:
    return field in PICKER_FIELDS


def format_multi_display(raw: str) -> str:
    parts = split_multi_field(raw)
    if not parts:
        return '—'
    return ', '.join(display_value(part) for part in parts)


def _single_keyboard(field: str) -> List[List[dict]]:
    rows: List[List[dict]] = []
    for index, (_, label) in enumerate(options_for_field(field)):
        rows.append([{'text': label, 'callback_data': f'prof:s:{field}:{index}'}])
    rows.append([{'text': 'Отмена', 'callback_data': 'prof:cancel'}])
    return rows


def _multi_keyboard(field: str, selected: Set[str]) -> List[List[dict]]:
    rows: List[List[dict]] = []
    for index, (value, label) in enumerate(options_for_field(field)):
        prefix = '✅ ' if value in selected else ''
        rows.append([{'text': f'{prefix}{label}', 'callback_data': f'prof:t:{field}:{index}'}])
    rows.append([
        {'text': '✅ Готово', 'callback_data': f'prof:ok:{field}'},
        {'text': 'Отмена', 'callback_data': 'prof:cancel'},
    ])
    return rows


def _lifestyle_keyboard(field: str, partner: Optional[str] = None) -> List[List[dict]]:
    rows: List[List[dict]] = []
    for index, (_, label) in enumerate(options_for_field(field)):
        if partner == 'man':
            cb = f'prof:cm:{field}:{index}'
        elif partner == 'woman':
            cb = f'prof:cw:{field}:{index}'
        else:
            cb = f'prof:s:{field}:{index}'
        rows.append([{'text': label, 'callback_data': cb}])
    rows.append([{'text': 'Отмена', 'callback_data': 'prof:cancel'}])
    return rows


def start_picker(handlers: 'BotHandlers', chat_id: int, user_id: int, field: str) -> None:
    profile = handlers.api.get_my_profile(user_id)
    label = FIELD_LABELS.get(field, field)

    if field in MULTI_PICKER_FIELDS:
        selected = set(split_multi_field(profile.get(field) or ''))
        session_store.set_pick_draft(user_id, {'selected': list(selected)})
        session_store.set_state(user_id, f'profile_pick:{field}')
        handlers.tg.send_message(
            chat_id,
            f"<b>{label.capitalize()}</b>\nВыберите один или несколько вариантов, затем нажмите «Готово».",
            reply_markup=handlers.tg.create_inline_keyboard(_multi_keyboard(field, selected)),
            parse_mode='HTML',
        )
        return

    if field in LIFESTYLE_FIELDS and is_couple_status(profile.get('status') or ''):
        session_store.set_pick_draft(user_id, {'partner': 'man'})
        session_store.set_state(user_id, f'profile_pick:{field}')
        handlers.tg.send_message(
            chat_id,
            f"<b>{label.capitalize()} — мужчина</b>\nВыберите вариант:",
            reply_markup=handlers.tg.create_inline_keyboard(_lifestyle_keyboard(field, 'man')),
            parse_mode='HTML',
        )
        return

    session_store.set_state(user_id, f'profile_pick:{field}')
    handlers.tg.send_message(
        chat_id,
        f"<b>{label.capitalize()}</b>\nВыберите вариант:",
        reply_markup=handlers.tg.create_inline_keyboard(_single_keyboard(field)),
        parse_mode='HTML',
    )


def _save_field(handlers: 'BotHandlers', chat_id: int, user_id: int, field: str, value: str) -> None:
    try:
        handlers.api.update_profile(user_id, {field: value})
        session_store.set_state(user_id, None)
        session_store.clear_pick_draft(user_id)
        label = FIELD_LABELS.get(field, field)
        handlers.tg.send_message(chat_id, f"✅ Поле «{label}» обновлено.")
        handlers.show_my_profile(chat_id, user_id)
    except SwingfoxAPIError as e:
        handlers.handle_api_error(chat_id, user_id, e)


def handle_picker_callback(
    handlers: 'BotHandlers',
    chat_id: int,
    user_id: int,
    data: str,
    cb_id: str,
) -> bool:
    if data == 'prof:cancel':
        session_store.set_state(user_id, None)
        session_store.clear_pick_draft(user_id)
        handlers.tg.answer_callback_query(cb_id, 'Отменено')
        handlers.show_my_profile(chat_id, user_id)
        return True

    parts = data.split(':')
    if len(parts) < 3 or parts[0] != 'prof':
        return False

    action = parts[1]

    def _pick_value(field_name: str, raw_index: str) -> Optional[str]:
        try:
            idx = int(raw_index)
            values = options_for_field(field_name)
            if idx < 0 or idx >= len(values):
                return None
            return values[idx][0]
        except (ValueError, KeyError):
            return None

    if action == 's' and len(parts) == 4:
        field = parts[2]
        value = _pick_value(field, parts[3])
        if value is None:
            handlers.tg.answer_callback_query(cb_id, 'Неверный вариант', show_alert=True)
            return True
        handlers.tg.answer_callback_query(cb_id)
        _save_field(handlers, chat_id, user_id, field, value)
        return True

    if action == 't' and len(parts) == 4:
        field = parts[2]
        value = _pick_value(field, parts[3])
        if value is None:
            handlers.tg.answer_callback_query(cb_id, 'Неверный вариант', show_alert=True)
            return True
        draft = session_store.get_pick_draft(user_id)
        selected = set(draft.get('selected') or [])
        if value in selected:
            selected.discard(value)
        else:
            selected.add(value)
        session_store.set_pick_draft(user_id, {'selected': list(selected)})
        handlers.tg.answer_callback_query(cb_id)
        handlers.tg.send_message(
            chat_id,
            f"<b>{FIELD_LABELS.get(field, field).capitalize()}</b>\n"
            "Выберите варианты и нажмите «Готово».",
            reply_markup=handlers.tg.create_inline_keyboard(_multi_keyboard(field, selected)),
            parse_mode='HTML',
        )
        return True

    if action == 'ok' and len(parts) == 3:
        field = parts[2]
        draft = session_store.get_pick_draft(user_id)
        selected = draft.get('selected') or []
        if not selected:
            handlers.tg.answer_callback_query(cb_id, 'Выберите хотя бы один вариант', show_alert=True)
            return True
        handlers.tg.answer_callback_query(cb_id)
        _save_field(handlers, chat_id, user_id, field, join_multi_field(list(selected)))
        return True

    if action == 'cm' and len(parts) == 4:
        field = parts[2]
        value = _pick_value(field, parts[3])
        if value is None:
            handlers.tg.answer_callback_query(cb_id, 'Неверный вариант', show_alert=True)
            return True
        session_store.set_pick_draft(user_id, {'partner': 'woman', 'man': value})
        handlers.tg.answer_callback_query(cb_id)
        handlers.tg.send_message(
            chat_id,
            f"<b>{FIELD_LABELS.get(field, field).capitalize()} — женщина</b>\nВыберите вариант:",
            reply_markup=handlers.tg.create_inline_keyboard(_lifestyle_keyboard(field, 'woman')),
            parse_mode='HTML',
        )
        return True

    if action == 'cw' and len(parts) == 4:
        field = parts[2]
        woman_value = _pick_value(field, parts[3])
        if woman_value is None:
            handlers.tg.answer_callback_query(cb_id, 'Неверный вариант', show_alert=True)
            return True
        draft = session_store.get_pick_draft(user_id)
        man_value = draft.get('man', 'no_matter')
        combined = f'{man_value}_{woman_value}'
        handlers.tg.answer_callback_query(cb_id)
        _save_field(handlers, chat_id, user_id, field, combined)
        return True

    return False
