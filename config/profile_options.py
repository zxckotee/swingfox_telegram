"""Fixed profile field options (aligned with swingfox client Profile.js / Register.js)."""

import re
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

Option = Tuple[str, str]  # (stored_value, button_label)

COUPLE_STATUSES = frozenset({
    'Семейная пара(М+Ж)',
    'Несемейная пара(М+Ж)',
})

STATUS_OPTIONS: List[Option] = [
    ('Семейная пара(М+Ж)', 'Семейная пара (М+Ж)'),
    ('Несемейная пара(М+Ж)', 'Несемейная пара (М+Ж)'),
    ('Мужчина', 'Мужчина'),
    ('Женщина', 'Женщина'),
]

SEARCH_STATUS_OPTIONS: List[Option] = [
    ('Семейная пара(М+Ж)', 'Сем. пара (М+Ж)'),
    ('Несемейная пара(М+Ж)', 'Несем. пара (М+Ж)'),
    ('Мужчина', 'Мужчина'),
    ('Женщина', 'Женщина'),
]

SEARCH_AGE_OPTIONS: List[Option] = [
    ('Возраст значения не имеет', 'Возраст не важен'),
    ('С ровестниками', 'С ровестниками'),
    ('С ровестниками или с разницей +/- 5 лет', '±5 лет'),
    ('С ровестниками или с разницей +/- 10 лет', '±10 лет'),
]

SMOKING_OPTIONS: List[Option] = [
    ('no_matter', 'Не важно'),
    ('Не курю и не переношу табачного дыма', 'Не курю (строго)'),
    ('Не курю, но терпимо отношусь к табачному дыму', 'Терпимо к дыму'),
    ('Курю, но могу обойтись какое-то время без сигарет', 'Курю, могу без'),
    ('Не могу отказаться от курения ни при каких обстоятельствах', 'Не могу бросить'),
    ('Парю вейп', 'Вейп'),
    ('Курю кальян', 'Кальян'),
]

ALKO_OPTIONS: List[Option] = [
    ('no_matter', 'Не важно'),
    ('Не употребляю вообще', 'Не употребляю'),
    ('В незначительных дозах, количество выпитого не отражается на моем поведении', 'Незнач. дозы'),
    ('Умеренно, до легкого опьянения, контролирую свое поведение', 'Умеренно'),
    ('Могу напиться, потерять контроль над своим поведением', 'Могу потерять контроль'),
]

PICKER_FIELDS = frozenset({
    'status',
    'search_status',
    'smoking',
    'alko',
})

MULTI_PICKER_FIELDS = frozenset({'search_status'})
LIFESTYLE_FIELDS = frozenset({'smoking', 'alko'})
PHYSICAL_FIELDS = frozenset({'height', 'weight'})
TEXT_INPUT_FIELDS = frozenset({'city', 'info', 'mobile', 'date', 'search_age', 'height', 'weight'})
NUMERIC_INPUT_FIELDS = frozenset({'date', 'search_age', 'height', 'weight'})

CITY_MIN_LEN = 2
CITY_MAX_LEN = 100
INFO_MAX_LEN = 300
MOBILE_MAX_LEN = 255
MOBILE_MIN_DIGITS = 5

HEIGHT_SINGLE_RANGE = (140, 220)
WEIGHT_SINGLE_RANGE = (40, 200)
HEIGHT_COUPLE_MAN_RANGE = (140, 220)
HEIGHT_COUPLE_WOMAN_RANGE = (140, 200)
WEIGHT_COUPLE_MAN_RANGE = (40, 200)
WEIGHT_COUPLE_WOMAN_RANGE = (40, 150)

FIELD_LABELS: Dict[str, str] = {
    'status': 'статус',
    'search_status': 'кого ищу',
    'search_age': 'возраст для поиска',
    'date': 'возраст',
    'smoking': 'курение',
    'alko': 'алкоголь',
    'city': 'город',
    'info': 'о себе',
    'mobile': 'контакт',
    'height': 'рост',
    'weight': 'вес',
}

_VALUE_LABELS: Dict[str, str] = {}
for _options in (
    STATUS_OPTIONS,
    SEARCH_STATUS_OPTIONS,
    SEARCH_AGE_OPTIONS,
    SMOKING_OPTIONS,
    ALKO_OPTIONS,
):
    for _stored, _label in _options:
        _VALUE_LABELS[_stored] = _label


def options_for_field(field: str) -> List[Option]:
    return {
        'status': STATUS_OPTIONS,
        'search_status': SEARCH_STATUS_OPTIONS,
        'search_age': SEARCH_AGE_OPTIONS,
        'smoking': SMOKING_OPTIONS,
        'alko': ALKO_OPTIONS,
    }[field]


def option_value(field: str, index: int) -> str:
    return options_for_field(field)[index][0]


def display_value(value: str) -> str:
    if not value:
        return '—'
    return _VALUE_LABELS.get(value, value)


def _parse_birth_part(date_part: str) -> Optional[date]:
    if not date_part or not str(date_part).strip():
        return None
    value = str(date_part).strip()
    if '-' in value:
        parts = value.split('-')
        if len(parts) >= 3:
            try:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                pass
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    if len(value) == 4 and value.isdigit():
        return date(int(value), 1, 1)
    return None


def calculate_age_from_birth(birth: Optional[date]) -> Optional[int]:
    if birth is None:
        return None
    today = date.today()
    age = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    return age if age >= 0 else None


def format_profile_age_display(raw_date: Optional[str], *, fallback_age: Optional[int] = None) -> str:
    if raw_date and str(raw_date).strip():
        value = str(raw_date).strip()
        if '_' in value:
            man_part, woman_part = value.split('_', 1)
            parts = []
            man_age = calculate_age_from_birth(_parse_birth_part(man_part))
            woman_age = calculate_age_from_birth(_parse_birth_part(woman_part))
            if man_age is not None:
                parts.append(f'М: {man_age}')
            if woman_age is not None:
                parts.append(f'Ж: {woman_age}')
            if parts:
                return ' · '.join(parts)
        else:
            age = calculate_age_from_birth(_parse_birth_part(value))
            if age is not None:
                return str(age)
    if fallback_age is not None:
        return str(fallback_age)
    return '—'


def format_search_age_display(raw: Optional[str]) -> str:
    if not raw or not str(raw).strip():
        return '—'
    value = str(raw).strip()
    if value in _VALUE_LABELS:
        return _VALUE_LABELS[value]
    if '_' in value:
        man, woman = value.split('_', 1)
        if man.isdigit() and woman.isdigit():
            return f'М: {man} · Ж: {woman}'
    if value.isdigit():
        return value
    return value


def split_numeric_parts(raw: str) -> List[str]:
    text = (raw or '').strip().replace(',', ' ').replace('–', '-')
    if not text:
        return []
    if '_' in text and ' ' not in text:
        return [part.strip() for part in text.split('_') if part.strip()]
    return [part.strip() for part in text.split() if part.strip()]


def _validate_integer_part(part: str, min_value: int, max_value: int, label: str) -> Tuple[Optional[int], Optional[str]]:
    if not part.isdigit():
        return None, f'{label}: допустимы только целые числа.'
    value = int(part)
    if value < min_value or value > max_value:
        return None, f'{label}: допустимый диапазон {min_value}–{max_value}.'
    return value, None


def _parse_couple_numeric_field(
    raw: str,
    *,
    man_range: Tuple[int, int],
    woman_range: Tuple[int, int],
    man_label: str,
    woman_label: str,
) -> Tuple[Optional[str], Optional[str]]:
    parts = split_numeric_parts(raw)
    if len(parts) != 2:
        return None, (
            f'Для пары укажите два числа: сначала {man_label.lower()}, затем {woman_label.lower()} '
            '(например: 180 165).'
        )
    man_value, man_error = _validate_integer_part(parts[0], *man_range, man_label)
    if man_error:
        return None, man_error
    woman_value, woman_error = _validate_integer_part(parts[1], *woman_range, woman_label)
    if woman_error:
        return None, woman_error
    return f'{man_value}_{woman_value}', None


def _parse_single_numeric_field(
    raw: str,
    *,
    value_range: Tuple[int, int],
    label: str,
    example: str,
) -> Tuple[Optional[str], Optional[str]]:
    parts = split_numeric_parts(raw)
    if len(parts) != 1:
        return None, f'Укажите одно число ({label}). Пример: {example}.'
    value, error = _validate_integer_part(parts[0], *value_range, label)
    if error:
        return None, error
    return str(value), None


def parse_city_input(raw: str) -> Tuple[Optional[str], Optional[str]]:
    value = (raw or '').strip()
    if len(value) < CITY_MIN_LEN:
        return None, f'Укажите название города (от {CITY_MIN_LEN} символов).'
    if len(value) > CITY_MAX_LEN:
        return None, f'Название города не длиннее {CITY_MAX_LEN} символов.'
    return value, None


def parse_info_input(raw: str) -> Tuple[Optional[str], Optional[str]]:
    value = (raw or '').strip()
    if len(value) > INFO_MAX_LEN:
        return None, f'Текст «О себе» не длиннее {INFO_MAX_LEN} символов.'
    return value, None


def parse_mobile_input(raw: str) -> Tuple[Optional[str], Optional[str]]:
    value = (raw or '').strip()
    if not value or value == '-':
        return '', None
    if len(value) > MOBILE_MAX_LEN:
        return None, f'Контакт не длиннее {MOBILE_MAX_LEN} символов.'
    digits = re.sub(r'\D', '', value)
    if len(digits) < MOBILE_MIN_DIGITS:
        return None, (
            f'Укажите телефон: минимум {MOBILE_MIN_DIGITS} цифр, можно с +, скобками и пробелами. '
            'Пример: +7 900 123-45-67'
        )
    if not re.fullmatch(r'[\d\s()+\-]+', value):
        return None, 'В контакте допустимы только цифры, пробелы, +, скобки и дефисы.'
    return value, None


def parse_height_input(raw: str, is_couple: bool) -> Tuple[Optional[str], Optional[str]]:
    if is_couple:
        return _parse_couple_numeric_field(
            raw,
            man_range=HEIGHT_COUPLE_MAN_RANGE,
            woman_range=HEIGHT_COUPLE_WOMAN_RANGE,
            man_label='Рост мужчины',
            woman_label='рост женщины',
        )
    return _parse_single_numeric_field(
        raw,
        value_range=HEIGHT_SINGLE_RANGE,
        label='рост в см',
        example='175',
    )


def parse_weight_input(raw: str, is_couple: bool) -> Tuple[Optional[str], Optional[str]]:
    if is_couple:
        return _parse_couple_numeric_field(
            raw,
            man_range=WEIGHT_COUPLE_MAN_RANGE,
            woman_range=WEIGHT_COUPLE_WOMAN_RANGE,
            man_label='Вес мужчины',
            woman_label='вес женщины',
        )
    return _parse_single_numeric_field(
        raw,
        value_range=WEIGHT_SINGLE_RANGE,
        label='вес в кг',
        example='70',
    )


def parse_date_input(raw: str, is_couple: bool) -> Tuple[Optional[str], Optional[str]]:
    parts = split_numeric_parts(raw)
    if not parts:
        return None, 'Укажите возраст числом.'

    for part in parts:
        if not part.isdigit():
            return None, 'Допустимы только числа. Пример: 32 или 42 36.'
        age = int(part)
        if age < 18 or age > 99:
            return None, 'Возраст должен быть от 18 до 99 лет.'

    current_year = date.today().year
    if is_couple:
        if len(parts) != 2:
            return None, 'Для пары укажите два числа: сначала мужчина, затем женщина (например: 42 36).'
        return f'{current_year - int(parts[0])}_{current_year - int(parts[1])}', None

    if len(parts) != 1:
        return None, 'Укажите один возраст числом (например: 32).'
    return str(current_year - int(parts[0])), None


def parse_search_age_input(raw: str, is_couple: bool) -> Tuple[Optional[str], Optional[str]]:
    parts = split_numeric_parts(raw)
    if not parts:
        return None, 'Укажите возраст числом.'

    for part in parts:
        if not part.isdigit():
            return None, 'Допустимы только числа. Пример: 32 или 42 36.'
        age = int(part)
        if age < 18 or age > 99:
            return None, 'Возраст должен быть от 18 до 99 лет.'

    if is_couple:
        if len(parts) != 2:
            return None, 'Для пары укажите два числа: сначала мужчина, затем женщина (например: 42 36).'
        return f'{parts[0]}_{parts[1]}', None

    if len(parts) != 1:
        return None, 'Укажите один возраст числом (например: 32).'
    return parts[0], None


_FIELD_PARSERS: Dict[str, Callable[..., Tuple[Optional[str], Optional[str]]]] = {
    'city': lambda raw, is_couple=False: parse_city_input(raw),
    'info': lambda raw, is_couple=False: parse_info_input(raw),
    'mobile': lambda raw, is_couple=False: parse_mobile_input(raw),
    'date': parse_date_input,
    'search_age': parse_search_age_input,
    'height': parse_height_input,
    'weight': parse_weight_input,
}


def parse_profile_field_input(field: str, raw: str, is_couple: bool = False) -> Tuple[Optional[str], Optional[str]]:
    parser = _FIELD_PARSERS.get(field)
    if not parser:
        value = (raw or '').strip()
        return (value, None) if value else (None, 'Укажите значение.')
    return parser(raw, is_couple)


def profile_field_input_hint(field: str, is_couple: bool = False) -> str:
    label = FIELD_LABELS.get(field, field).capitalize()
    hints = {
        'city': (
            'Введите название города.\n'
            f'От {CITY_MIN_LEN} до {CITY_MAX_LEN} символов.\n'
            'Пример: <code>Москва</code>'
        ),
        'info': (
            'Кратко о себе.\n'
            f'До {INFO_MAX_LEN} символов, можно оставить пустым.'
        ),
        'mobile': (
            'Телефон для связи.\n'
            f'Минимум {MOBILE_MIN_DIGITS} цифр, можно с +, скобками и пробелами.\n'
            'Пример: <code>+7 900 123-45-67</code>\n'
            'Чтобы убрать контакт — отправьте пустое сообщение или «-».'
        ),
        'date': (
            'Введите ваш возраст числом.\n'
            'Для пары — два числа через пробел или «_» (сначала мужчина, потом женщина).\n'
            'Диапазон: 18–99.\n'
            'Примеры: <code>38</code> или <code>42 36</code>'
            if is_couple else
            'Введите ваш возраст числом.\n'
            'Диапазон: 18–99.\n'
            'Пример: <code>32</code>'
        ),
        'search_age': (
            'Введите возраст для поиска числом.\n'
            'Для пары — два числа через пробел или «_» (сначала мужчина, потом женщина).\n'
            'Диапазон: 18–99.\n'
            'Примеры: <code>38</code> или <code>42 36</code>'
            if is_couple else
            'Введите возраст для поиска числом.\n'
            'Диапазон: 18–99.\n'
            'Пример: <code>32</code>'
        ),
        'height': (
            'Рост в сантиметрах.\n'
            'Для пары — два числа через пробел или «_» (сначала мужчина, потом женщина).\n'
            f'Мужчина: {HEIGHT_COUPLE_MAN_RANGE[0]}–{HEIGHT_COUPLE_MAN_RANGE[1]}, '
            f'женщина: {HEIGHT_COUPLE_WOMAN_RANGE[0]}–{HEIGHT_COUPLE_WOMAN_RANGE[1]}.\n'
            'Пример: <code>180 165</code>'
            if is_couple else
            'Рост в сантиметрах, одним числом.\n'
            f'Диапазон: {HEIGHT_SINGLE_RANGE[0]}–{HEIGHT_SINGLE_RANGE[1]}.\n'
            'Пример: <code>175</code>'
        ),
        'weight': (
            'Вес в килограммах.\n'
            'Для пары — два числа через пробел или «_» (сначала мужчина, потом женщина).\n'
            f'Мужчина: {WEIGHT_COUPLE_MAN_RANGE[0]}–{WEIGHT_COUPLE_MAN_RANGE[1]}, '
            f'женщина: {WEIGHT_COUPLE_WOMAN_RANGE[0]}–{WEIGHT_COUPLE_WOMAN_RANGE[1]}.\n'
            'Пример: <code>80 55</code>'
            if is_couple else
            'Вес в килограммах, одним числом.\n'
            f'Диапазон: {WEIGHT_SINGLE_RANGE[0]}–{WEIGHT_SINGLE_RANGE[1]}.\n'
            'Пример: <code>70</code>'
        ),
    }
    return f'<b>{label}</b>\n{hints.get(field, "Введите новое значение.")}'


def is_couple_status(status: str) -> bool:
    return status in COUPLE_STATUSES


def split_multi_field(raw: str) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in str(raw).split('&&') if part.strip()]


def join_multi_field(values: List[str]) -> str:
    return '&&'.join(values)


def split_couple_field(raw: str, field: str) -> Tuple[Optional[str], Optional[str]]:
    """Split man_woman stored value without breaking keys like no_matter."""
    if not raw or not str(raw).strip():
        return None, None
    value = str(raw).strip()
    if field in PHYSICAL_FIELDS:
        if '_' not in value:
            return value, None
        man, woman = value.split('_', 1)
        return man or None, woman or None

    if field not in LIFESTYLE_FIELDS:
        if '_' not in value:
            return value, None
        man, woman = value.split('_', 1)
        return man or None, woman or None

    keys = [key for key, _ in options_for_field(field)]
    for woman_key in sorted(keys, key=len, reverse=True):
        if value == woman_key:
            return None, woman_key
        suffix = f'_{woman_key}'
        if value.endswith(suffix):
            man = value[:-len(suffix)]
            return man or None, woman_key
    return value, None
