import unittest
from unittest.mock import MagicMock, patch

from state.backend_availability import (
    is_backend_available,
    set_backend_available,
)
from utils.backend_probe import BackendProbe


class BackendProbeTest(unittest.TestCase):
    def setUp(self):
        set_backend_available(True)

    @patch('utils.backend_probe.time.time', return_value=1000.0)
    def test_startup_marks_backend_down(self, _mock_time):
        api = MagicMock()
        api.api_url = 'https://127.0.0.1:3002/api'
        api.ping.return_value = False

        BackendProbe(api, env_label='staging')

        self.assertFalse(is_backend_available())

    @patch('utils.backend_probe.time.time')
    def test_recovery_logged_once(self, mock_time):
        mock_time.return_value = 2000.0
        api = MagicMock()
        api.api_url = 'https://127.0.0.1:3002/api'
        api.ping.return_value = False

        probe = BackendProbe(api, env_label='staging')
        self.assertFalse(is_backend_available())

        mock_time.return_value = 2030.0
        api.ping.return_value = True
        probe.maybe_probe(2030.0)
        self.assertTrue(is_backend_available())


class SwingfoxPingTest(unittest.TestCase):
    @patch('api.swingfox_client.requests.get')
    def test_ping_ok_on_200(self, mock_get):
        from api.swingfox_client import SwingfoxClient

        mock_get.return_value = MagicMock(status_code=200)
        client = SwingfoxClient(api_url='https://127.0.0.1:3002/api')
        self.assertTrue(client.ping(timeout=1))

    @patch('api.swingfox_client.requests.get')
    def test_ping_false_on_connection_error(self, mock_get):
        from api.swingfox_client import SwingfoxClient
        import requests

        mock_get.side_effect = requests.ConnectionError('refused')
        client = SwingfoxClient(api_url='https://127.0.0.1:3002/api')
        self.assertFalse(client.ping(timeout=1))


if __name__ == '__main__':
    unittest.main()