from typing import Optional

from config.profile_options import display_value, split_couple_field
from handlers.profile_pickers import format_multi_display


def format_physical_field(label: str, raw: Optional[str], unit: str = '') -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    value = str(raw).strip()
    suffix = f' {unit}'.rstrip() if unit else ''
    man, woman = split_couple_field(value, 'height' if label == 'Рост' else 'weight')
    if woman is not None:
        parts = []
        if man and man.strip():
            parts.append(f"М: {man.strip()}{suffix}")
        if woman and woman.strip():
            parts.append(f"Ж: {woman.strip()}{suffix}")
        if parts:
            return f"{label}: {' · '.join(parts)}"
        return None
    return f"{label}: {value}{suffix}"


def format_lifestyle_field(label: str, raw: Optional[str]) -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    field = 'smoking' if label == 'Курение' else 'alko'
    value = str(raw).strip()
    man, woman = split_couple_field(value, field)
    if woman is not None:
        parts = []
        if man and man.strip() and man.strip() != 'no_matter':
            parts.append(f"М: {display_value(man.strip())}")
        if woman and woman.strip() and woman.strip() != 'no_matter':
            parts.append(f"Ж: {display_value(woman.strip())}")
        if parts:
            return f"{label}: {' · '.join(parts)}"
        return None
    if value == 'no_matter':
        return None
    return f"{label}: {display_value(value)}"


def _append_profile_details(lines: list, profile: dict) -> None:
    for line in (
        format_physical_field('Рост', profile.get('height'), 'см'),
        format_physical_field('Вес', profile.get('weight'), 'кг'),
        format_lifestyle_field('Курение', profile.get('smoking')),
        format_lifestyle_field('Алкоголь', profile.get('alko')),
    ):
        if line:
            lines.append(line)

    mobile = profile.get('mobile')
    if mobile and str(mobile).strip():
        lines.append(f"Контакт: {mobile}")


def format_my_profile_caption(profile: dict) -> str:
    lines = [
        f"<b>Мой профиль — {profile.get('login', '—')}</b>",
        f"Статус: {profile.get('status') or '—'}",
        f"Город: {profile.get('city') or '—'}",
        f"Кого ищу: {format_multi_display(profile.get('search_status') or '')}",
        f"Возраст: {display_value(profile.get('search_age') or '') or '—'}",
    ]
    _append_profile_details(lines, profile)
    lines.append(f"О себе: {(profile.get('info') or '—')[:200]}")
    return '\n'.join(lines)[:1024]


def format_swipe_profile_caption(profile: dict) -> str:
    p = profile.get('profile', profile)
    lines = [f"<b>{p.get('login', '—')}</b>"]
    if p.get('age'):
        lines.append(str(p['age']))
    if p.get('status'):
        lines.append(f"Статус: {p['status']}")
    city = p.get('city')
    if city:
        country = p.get('country')
        lines.append(f"Город: {f'{country}, {city}' if country else city}")
    distance = p.get('distance')
    if distance:
        lines.append(f"Расстояние: {distance} км")

    search_status = p.get('search_status') or p.get('searchStatus')
    search_age = p.get('search_age') or p.get('searchAge')
    if search_status:
        lines.append(f"Кого ищу: {format_multi_display(search_status)}")
    if search_age:
        lines.append(f"Возраст: {display_value(search_age)}")

    _append_profile_details(lines, p)

    if p.get('online'):
        lines.append(f"Онлайн: {p['online']}")
    lines.append(f"О себе: {(p.get('info') or '—')[:400]}")

    tg_link = p.get('telegram_link')
    tg_username = p.get('telegram_username')
    if tg_link:
        label = f"@{tg_username}" if tg_username else 'Telegram'
        lines.append(f'<a href="{tg_link}">{label}</a>')
    elif tg_username:
        lines.append(f"Telegram: @{tg_username}")

    return '\n'.join(lines)[:1024]
