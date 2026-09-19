import unittest
from unittest.mock import MagicMock, patch

from telegram.client import TelegramClient, _is_webhook_conflict_error


class WebhookConflictTest(unittest.TestCase):
    def test_detects_getupdates_webhook_conflict(self):
        exc = RuntimeError(
            "Conflict: can't use getUpdates method while webhook is active; "
            "use deleteWebhook to delete the webhook first"
        )
        self.assertTrue(_is_webhook_conflict_error(exc))

    def test_detects_setwebhook_termination(self):
        exc = RuntimeError('Conflict: terminated by setWebhook request')
        self.assertTrue(_is_webhook_conflict_error(exc))

    def test_ignores_unrelated_errors(self):
        self.assertFalse(_is_webhook_conflict_error(RuntimeError('Connection reset by peer')))


class EnsurePollingModeTest(unittest.TestCase):
    @patch('telegram.client.requests.get')
    @patch.object(TelegramClient, '_post')
    def test_clears_active_webhook(self, mock_post, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {
            'ok': True,
            'result': {'url': 'https://example.com/hook', 'has_custom_certificate': False},
        })
        mock_post.return_value = {'ok': True, 'result': True}

        TelegramClient().ensure_polling_mode()

        mock_post.assert_called_once_with('deleteWebhook', {'drop_pending_updates': False})

    @patch('telegram.client.requests.get')
    @patch.object(TelegramClient, '_post')
    def test_no_log_when_webhook_absent(self, mock_post, mock_get):
        mock_get.return_value = MagicMock(json=lambda: {
            'ok': True,
            'result': {'url': '', 'has_custom_certificate': False},
        })
        mock_post.return_value = {'ok': True, 'result': True}

        TelegramClient().ensure_polling_mode()

        mock_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
