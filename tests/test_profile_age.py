import unittest
from datetime import date
from unittest.mock import patch

from config.profile_options import (
    calculate_age_from_birth,
    format_profile_age_display,
    parse_date_input,
)


class _FixedDate(date):
    _today = date(2026, 9, 19)

    @classmethod
    def today(cls):
        return cls._today


class ProfileAgeTest(unittest.TestCase):
    def test_format_single_age_from_year(self):
        with patch('config.profile_options.date', _FixedDate):
            self.assertEqual(format_profile_age_display('1990'), '36')

    def test_format_couple_age_from_years(self):
        with patch('config.profile_options.date', _FixedDate):
            self.assertEqual(format_profile_age_display('1984_1990'), 'М: 42 · Ж: 36')

    def test_format_couple_age_from_full_dates(self):
        with patch('config.profile_options.date', _FixedDate):
            self.assertEqual(format_profile_age_display('1984-05-10_1990-03-20'), 'М: 42 · Ж: 36')

    def test_format_age_fallback(self):
        self.assertEqual(format_profile_age_display(None, fallback_age=33), '33')

    def test_calculate_age_from_birth(self):
        with patch('config.profile_options.date', _FixedDate):
            self.assertEqual(calculate_age_from_birth(date(1990, 1, 1)), 36)

    def test_parse_date_input_single(self):
        with patch('config.profile_options.date', _FixedDate):
            value, error = parse_date_input('32', False)
            self.assertIsNone(error)
            self.assertEqual(value, '1994')

    def test_parse_date_input_couple(self):
        with patch('config.profile_options.date', _FixedDate):
            value, error = parse_date_input('42 36', True)
            self.assertIsNone(error)
            self.assertEqual(value, '1984_1990')


if __name__ == '__main__':
    unittest.main()
