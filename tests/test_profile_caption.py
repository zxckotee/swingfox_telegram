import os
import unittest

from config.profile_options import display_value, split_couple_field
from handlers.profile_format import (
    format_lifestyle_field,
    format_my_profile_caption,
    format_physical_field,
    format_swipe_profile_caption,
)
from utils.telegram_register_link import build_register_url


class ProfileCaptionTest(unittest.TestCase):
    def test_format_my_profile_includes_physical_fields(self):
        caption = format_my_profile_caption({
            'login': 'testuser',
            'status': 'Мужчина',
            'city': 'Москва',
            'search_status': 'Женщина',
            'search_age': 'С ровестниками или с разницей +/- 5 лет',
            'height': '180',
            'weight': '78',
            'mobile': '+7 900 000-00-00',
            'smoking': 'Не курю и не переношу табачного дыма',
            'alko': 'Умеренно, до легкого опьянения, контролирую свое поведение',
            'info': 'Привет',
        })
        self.assertIn('Рост: 180 см', caption)
        self.assertIn('Вес: 78 кг', caption)
        self.assertIn('Контакт: +7 900 000-00-00', caption)
        self.assertIn('Курение:', caption)
        self.assertIn('Алкоголь:', caption)
        self.assertIn('±5 лет', caption)

    def test_format_couple_lifestyle(self):
        line = format_lifestyle_field('Курение', 'no_matter_Не курю и не переношу табачного дыма')
        self.assertIn('Ж: Не курю (строго)', line)
        self.assertNotIn('no', line)
        self.assertNotIn('matter', line)

    def test_format_couple_height(self):
        line = format_physical_field('Рост', '180_165', 'см')
        self.assertIn('М: 180 см', line)
        self.assertIn('Ж: 165 см', line)

    def test_split_couple_no_matter_both(self):
        man, woman = split_couple_field('no_matter_no_matter', 'smoking')
        self.assertEqual(man, 'no_matter')
        self.assertEqual(woman, 'no_matter')

    def test_display_value_maps_keys(self):
        self.assertEqual(display_value('no_matter'), 'Не важно')
        self.assertEqual(
            display_value('Не курю и не переношу табачного дыма'),
            'Не курю (строго)',
        )

    def test_format_swipe_profile_includes_details(self):
        caption = format_swipe_profile_caption({
            'login': 'anna',
            'age': '36 лет',
            'status': 'Женщина',
            'city': 'Казань',
            'searchStatus': 'Мужчина',
            'searchAge': 'С ровестниками или с разницей +/- 5 лет',
            'height': '170',
            'weight': '58',
            'smoking': 'no_matter',
            'alko': 'Умеренно, до легкого опьянения, контролирую свое поведение',
            'info': 'Привет',
            'telegram_link': 'https://t.me/anna',
            'telegram_username': 'anna',
        })
        self.assertIn('Рост: 170 см', caption)
        self.assertIn('Вес: 58 кг', caption)
        self.assertIn('Кого ищу:', caption)
        self.assertIn('https://t.me/anna', caption)


class RegisterLinkTest(unittest.TestCase):
    def test_build_register_url(self):
        os.environ['TELEGRAM_BOT_SHARED_SECRET'] = 'test-secret-key'
        url = build_register_url(123456789, 'https://swingfox.ru')
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith('https://swingfox.ru/register?tg_code='))
        self.assertEqual(build_register_url(1, 'https://swingfox.ru/stagging'), build_register_url(1, 'https://swingfox.ru/stagging'))


if __name__ == '__main__':
    unittest.main()
