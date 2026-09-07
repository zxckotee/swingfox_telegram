import unittest

from config.profile_options import (
    parse_city_input,
    parse_height_input,
    parse_info_input,
    parse_mobile_input,
    parse_profile_field_input,
    parse_search_age_input,
    parse_weight_input,
    profile_field_input_hint,
)


class ProfileFieldInputTest(unittest.TestCase):
    def test_city_requires_name(self):
        value, error = parse_city_input('М')
        self.assertIsNone(value)
        self.assertIn('города', error)

    def test_city_accepts_valid_name(self):
        value, error = parse_city_input('Санкт-Петербург')
        self.assertEqual(value, 'Санкт-Петербург')
        self.assertIsNone(error)

    def test_info_max_length(self):
        value, error = parse_info_input('a' * 301)
        self.assertIsNone(value)
        self.assertIn('300', error)

    def test_info_allows_empty(self):
        value, error = parse_info_input('   ')
        self.assertEqual(value, '')
        self.assertIsNone(error)

    def test_mobile_requires_digits(self):
        value, error = parse_mobile_input('телефон')
        self.assertIsNone(value)
        self.assertIn('цифр', error)

    def test_mobile_accepts_formatted_phone(self):
        value, error = parse_mobile_input('+7 (900) 123-45-67')
        self.assertEqual(value, '+7 (900) 123-45-67')
        self.assertIsNone(error)

    def test_mobile_clear_with_dash(self):
        value, error = parse_mobile_input('-')
        self.assertEqual(value, '')
        self.assertIsNone(error)

    def test_height_single_rejects_text(self):
        value, error = parse_height_input('высокий', False)
        self.assertIsNone(value)
        self.assertIn('числа', error)

    def test_height_single_range(self):
        value, error = parse_height_input('130', False)
        self.assertIsNone(value)
        self.assertIn('140', error)

    def test_height_single_valid(self):
        value, error = parse_height_input('175', False)
        self.assertEqual(value, '175')
        self.assertIsNone(error)

    def test_height_couple_valid(self):
        value, error = parse_height_input('180 165', True)
        self.assertEqual(value, '180_165')
        self.assertIsNone(error)

    def test_height_couple_woman_range(self):
        value, error = parse_height_input('180 210', True)
        self.assertIsNone(value)
        self.assertIn('женщины', error)

    def test_weight_single_valid(self):
        value, error = parse_weight_input('70', False)
        self.assertEqual(value, '70')
        self.assertIsNone(error)

    def test_weight_couple_valid(self):
        value, error = parse_weight_input('80_55', True)
        self.assertEqual(value, '80_55')
        self.assertIsNone(error)

    def test_search_age_still_numeric(self):
        value, error = parse_search_age_input('Возраст не важен', False)
        self.assertIsNone(value)
        self.assertIn('числа', error)

    def test_profile_field_input_dispatcher(self):
        value, error = parse_profile_field_input('city', 'Казань')
        self.assertEqual(value, 'Казань')
        self.assertIsNone(error)

    def test_profile_field_hint_contains_format(self):
        hint = profile_field_input_hint('height', is_couple=False)
        self.assertIn('175', hint)
        self.assertIn('140', hint)


if __name__ == '__main__':
    unittest.main()
