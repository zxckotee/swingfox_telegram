"""Periodic backend health checks during Telegram long polling."""

import logging
import os
import time
from typing import TYPE_CHECKING, Optional

from state.backend_availability import downtime_hours, set_backend_available

if TYPE_CHECKING:
    from api.swingfox_client import SwingfoxClient

log = logging.getLogger('swingfox.telegram')


class BackendProbe:
    def __init__(self, api: 'SwingfoxClient', *, env_label: str):
        self._api = api
        self._env_label = env_label
        self._last_probe = 0.0
        self._last_down_log = 0.0
        self._probe_when_up = float(os.getenv('BACKEND_PROBE_INTERVAL_UP', '120'))
        self._probe_when_down = float(os.getenv('BACKEND_PROBE_SECONDS', '15'))
        self._down_log_interval = float(os.getenv('BACKEND_DOWN_LOG_SECONDS', '600'))
        first = self._api.ping()
        set_backend_available(first, now=time.time())
        if not first:
            log.warning(
                'Backend %s unreachable at startup (%s) — Telegram polling continues, '
                'will keep retrying (no time limit)',
                self._env_label,
                self._api.api_url,
            )
            self._last_down_log = time.time()
        self._last_probe = time.time()

    def maybe_probe(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        from state.backend_availability import is_backend_available

        interval = self._probe_when_up if is_backend_available() else self._probe_when_down
        if now - self._last_probe < interval:
            return

        was_up = is_backend_available()
        ok = self._api.ping()
        self._last_probe = now
        set_backend_available(ok, now=now)

        if ok and not was_up:
            hours = downtime_hours(now)
            log.info(
                'Backend %s is reachable again → %s (was down %.1f h)',
                self._env_label,
                self._api.api_url,
                hours,
            )
            return

        if not ok and was_up:
            log.warning(
                'Backend %s unreachable (%s) — bot stays up, retrying every %ss',
                self._env_label,
                self._api.api_url,
                int(self._probe_when_down),
            )
            self._last_down_log = now
            return

        if not ok and now - self._last_down_log >= self._down_log_interval:
            log.warning(
                'Backend %s still down (%.1f h) — continuing Telegram polling and API probes',
                self._env_label,
                downtime_hours(now),
            )
            self._last_down_log = now