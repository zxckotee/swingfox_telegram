from typing import Optional

from config.profile_options import display_value
from handlers.profile_pickers import format_multi_display


def format_physical_field(label: str, raw: Optional[str], unit: str = '') -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    value = str(raw).strip()
    suffix = f' {unit}'.rstrip() if unit else ''
    if '_' in value:
        man, woman = value.split('_', 1)
        parts = []
        if man.strip():
            parts.append(f"М: {man.strip()}{suffix}")
        if woman.strip():
            parts.append(f"Ж: {woman.strip()}{suffix}")
        if parts:
            return f"{label}: {' · '.join(parts)}"
        return None
    return f"{label}: {value}{suffix}"


def format_lifestyle_field(label: str, raw: Optional[str]) -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    value = str(raw).strip()
    if '_' in value:
        man, woman = value.split('_', 1)
        parts = []
        if man.strip() and man.strip() != 'no_matter':
            parts.append(f"М: {display_value(man.strip())}")
        if woman.strip() and woman.strip() != 'no_matter':
            parts.append(f"Ж: {display_value(woman.strip())}")
        if parts:
            return f"{label}: {' · '.join(parts)}"
        return None
    if value == 'no_matter':
        return None
    return f"{label}: {display_value(value)}"


def format_my_profile_caption(profile: dict) -> str:
    lines = [
        f"<b>Мой профиль — {profile.get('login', '—')}</b>",
        f"Статус: {profile.get('status') or '—'}",
        f"Город: {profile.get('city') or '—'}",
        f"Кого ищу: {format_multi_display(profile.get('search_status') or '')}",
        f"Возраст: {profile.get('search_age') or '—'}",
    ]
    for line in (
        format_physical_field('Рост', profile.get('height'), 'см'),
        format_physical_field('Вес', profile.get('weight'), 'кг'),
        format_lifestyle_field('Курение', profile.get('smoking')),
        format_lifestyle_field('Алкоголь', profile.get('alko')),
    ):
        if line:
            lines.append(line)
    lines.append(f"О себе: {(profile.get('info') or '—')[:200]}")
    if profile.get('mobile'):
        lines.append(f"Контакт: {profile.get('mobile')}")
    return '\n'.join(lines)[:1024]
