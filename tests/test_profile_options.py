import unittest

from config.profile_options import (
    join_multi_field,
    option_value,
    split_multi_field,
)
from handlers.profile_pickers import field_uses_picker, format_multi_display


class ProfileOptionsTest(unittest.TestCase):
    def test_picker_fields(self):
        self.assertTrue(field_uses_picker('status'))
        self.assertTrue(field_uses_picker('search_status'))
        self.assertFalse(field_uses_picker('city'))

    def test_multi_join_split(self):
        raw = join_multi_field(['Мужчина', 'Женщина'])
        self.assertEqual(raw, 'Мужчина&&Женщина')
        self.assertEqual(split_multi_field(raw), ['Мужчина', 'Женщина'])

    def test_format_multi_display(self):
        text = format_multi_display('Мужчина&&Женщина')
        self.assertIn('Мужчина', text)
        self.assertIn('Женщина', text)

    def test_option_value_by_index(self):
        self.assertEqual(option_value('status', 0), 'Семейная пара(М+Ж)')


if __name__ == '__main__':
    unittest.main()
