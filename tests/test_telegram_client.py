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

    @patch.object(TelegramClient, '_post')
    def test_answer_callback_query_omits_empty_text(self, mock_post):
        TelegramClient().answer_callback_query('cb-1')
        mock_post.assert_called_once_with('answerCallbackQuery', {'callback_query_id': 'cb-1'})


if __name__ == '__main__':
    unittest.main()
