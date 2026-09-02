import os
import unittest

from handlers.profile_format import (
    format_lifestyle_field,
    format_my_profile_caption,
    format_physical_field,
)
from utils.telegram_register_link import build_register_url


class ProfileCaptionTest(unittest.TestCase):
    def test_format_my_profile_includes_physical_fields(self):
        caption = format_my_profile_caption({
            'login': 'testuser',
            'status': 'Мужчина',
            'city': 'Москва',
            'search_status': 'Женщина',
            'search_age': '±5 лет',
            'height': '180',
            'weight': '78',
            'smoking': 'Не курю и не переношу табачного дыма',
            'alko': 'Умеренно, до легкого опьянения, контролирую свое поведение',
            'info': 'Привет',
        })
        self.assertIn('Рост: 180 см', caption)
        self.assertIn('Вес: 78 кг', caption)
        self.assertIn('Курение:', caption)
        self.assertIn('Алкоголь:', caption)

    def test_format_couple_lifestyle(self):
        line = format_lifestyle_field('Курение', 'no_matter_Не курю и не переношу табачного дыма')
        self.assertIn('Ж:', line)

    def test_format_couple_height(self):
        line = format_physical_field('Рост', '180_165', 'см')
        self.assertIn('М: 180 см', line)
        self.assertIn('Ж: 165 см', line)


class RegisterLinkTest(unittest.TestCase):
    def test_build_register_url(self):
        os.environ['TELEGRAM_BOT_SHARED_SECRET'] = 'test-secret-key'
        url = build_register_url(123456789, 'https://swingfox.ru')
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith('https://swingfox.ru/register?tg_code='))
        self.assertEqual(build_register_url(1, 'https://swingfox.ru/stagging'), build_register_url(1, 'https://swingfox.ru/stagging'))


if __name__ == '__main__':
    unittest.main()
