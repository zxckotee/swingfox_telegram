"""Fixed profile field options (aligned with swingfox client Profile.js / Register.js)."""

from typing import Dict, List, Tuple

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
    'search_age',
    'smoking',
    'alko',
})

MULTI_PICKER_FIELDS = frozenset({'search_status'})
LIFESTYLE_FIELDS = frozenset({'smoking', 'alko'})

FIELD_LABELS: Dict[str, str] = {
    'status': 'статус',
    'search_status': 'кого ищу',
    'search_age': 'возраст для поиска',
    'smoking': 'курение',
    'alko': 'алкоголь',
    'city': 'город',
    'info': 'о себе',
    'mobile': 'контакт',
    'height': 'рост',
    'weight': 'вес',
}


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
    if value == 'no_matter':
        return 'Не имеет значения'
    return value


def is_couple_status(status: str) -> bool:
    return status in COUPLE_STATUSES


def split_multi_field(raw: str) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in str(raw).split('&&') if part.strip()]


def join_multi_field(values: List[str]) -> str:
    return '&&'.join(values)
