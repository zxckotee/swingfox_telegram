import unittest

from config.backend import rewrite_site_url, rewrite_uploads_url


class BackendUrlRewriteTest(unittest.TestCase):
    def test_rewrite_site_url_to_staging(self):
        url = rewrite_site_url(
            'https://swingfox.ru/auth/telegram?code=abc&redirect=/game',
            production=False,
            web_url='https://swingfox.ru/stagging',
        )
        self.assertEqual(
            url,
            'https://swingfox.ru/stagging/auth/telegram?code=abc&redirect=/game',
        )

    def test_rewrite_site_url_keeps_production(self):
        url = rewrite_site_url(
            'https://swingfox.ru/game',
            production=True,
            web_url='https://swingfox.ru',
        )
        self.assertEqual(url, 'https://swingfox.ru/game')

    def test_rewrite_uploads_url_to_staging(self):
        url = rewrite_uploads_url(
            'https://swingfox.ru/uploads/ads/1.jpg',
            production=False,
            uploads_url='https://swingfox.ru/stagging/uploads',
        )
        self.assertEqual(url, 'https://swingfox.ru/stagging/uploads/ads/1.jpg')


if __name__ == '__main__':
    unittest.main()
