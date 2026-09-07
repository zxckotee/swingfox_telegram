import unittest

from config.profile_options import format_search_age_display, parse_search_age_input


class SearchAgeTest(unittest.TestCase):
    def test_parse_single_age(self):
        value, error = parse_search_age_input('32', False)
        self.assertIsNone(error)
        self.assertEqual(value, '32')

    def test_parse_couple_age(self):
        value, error = parse_search_age_input('42 36', True)
        self.assertIsNone(error)
        self.assertEqual(value, '42_36')

    def test_reject_text_age(self):
        value, error = parse_search_age_input('Возраст не важен', False)
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_format_numeric_couple(self):
        self.assertEqual(format_search_age_display('42_36'), 'М: 42 · Ж: 36')


if __name__ == '__main__':
    unittest.main()
