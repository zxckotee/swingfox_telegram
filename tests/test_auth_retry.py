import unittest
from unittest.mock import MagicMock, patch

from api.swingfox_client import (
    AUTH_BACKEND_OUTDATED,
    AUTH_CONFIG,
    AUTH_NOT_LINKED,
    SwingfoxAPIError,
    SwingfoxClient,
    classify_auth_failure,
)


class AuthRetryTest(unittest.TestCase):
    def test_ensure_authenticated_refreshes_expired_token_without_clearing_first(self):
        client = SwingfoxClient(api_url='http://test', shared_secret='secret')
        expired = (
            'eyJhbGciOiJIUzI1NiJ9.'
            'eyJleHAiOjF9.'
            'sig'
        )
        with patch.object(client, 'get_token', return_value=expired), \
             patch.object(client, 'clear_token') as clear_mock, \
             patch.object(client, 'refresh_token', return_value=True) as refresh_mock:
            self.assertTrue(client.ensure_authenticated(42))
        refresh_mock.assert_called_once_with(42)
        clear_mock.assert_not_called()

    def test_call_with_auth_retry_retries_after_refresh(self):
        client = SwingfoxClient(api_url='http://test', shared_secret='secret')
        fn = MagicMock(side_effect=[
            SwingfoxAPIError(401, {'error': 'token_expired'}),
            'ok',
        ])
        with patch.object(client, 'refresh_token', return_value=True):
            result = client.call_with_auth_retry(7, fn)
        self.assertEqual(result, 'ok')
        self.assertEqual(fn.call_count, 2)

    def test_update_profile_uses_cached_current(self):
        client = SwingfoxClient(api_url='http://test', shared_secret='secret')
        current = {
            'country': 'RU',
            'city': 'Москва',
            'status': 'Мужчина',
            'search_status': 'Женщина',
            'search_age': '25-35',
            'location': '',
            'mobile': '',
            'info': '',
            'date': '',
            'height': '',
            'weight': '',
            'smoking': 'no',
            'alko': 'no',
        }
        with patch.object(client, 'get_my_profile') as get_mock, \
             patch.object(client, '_request', return_value={'ok': True}) as req_mock:
            client.update_profile(1, {'search_status': 'Мужчина&&Женщина'}, current=current)
        get_mock.assert_not_called()
        payload = req_mock.call_args.kwargs['json']
        self.assertEqual(payload['search_status'], 'Мужчина&&Женщина')
        self.assertEqual(payload['city'], 'Москва')


    def test_classify_auth_failure(self):
        self.assertEqual(classify_auth_failure('not_linked'), AUTH_NOT_LINKED)
        self.assertEqual(classify_auth_failure('invalid_signature'), AUTH_CONFIG)
        self.assertEqual(classify_auth_failure('API endpoint не найден'), AUTH_BACKEND_OUTDATED)


if __name__ == '__main__':
    unittest.main()
