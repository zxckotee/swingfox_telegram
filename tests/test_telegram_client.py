import json
import unittest
from unittest.mock import MagicMock, patch

from telegram.client import TelegramClient


class TelegramClientPayloadTest(unittest.TestCase):
    def test_encode_form_payload_booleans(self):
        encoded = TelegramClient._encode_form_payload({
            'protect_content': True,
            'show_alert': False,
            'text': 'hello',
            'empty': '',
        })
        self.assertEqual(encoded['protect_content'], 'true')
        self.assertNotIn('show_alert', encoded)  # False booleans are omitted
        self.assertEqual(encoded['text'], 'hello')
        self.assertNotIn('empty', encoded)

    @patch('telegram.client.requests.get')
    def test_answer_callback_query_uses_get(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {'ok': True, 'result': True})
        TelegramClient().answer_callback_query('cb-1')
        mock_get.assert_called_once()
        params = mock_get.call_args.kwargs.get('params') or mock_get.call_args[1].get('params')
        self.assertEqual(params['callback_query_id'], 'cb-1')
        self.assertNotIn('text', params)

    @patch('telegram.client.requests.get')
    def test_get_updates_allowed_updates_json(self, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {'ok': True, 'result': []})
        TelegramClient().get_updates(offset=10)
        params = mock_get.call_args.kwargs.get('params') or mock_get.call_args[1].get('params')
        self.assertEqual(json.loads(params['allowed_updates']), ['message', 'callback_query'])


if __name__ == '__main__':
    unittest.main()
