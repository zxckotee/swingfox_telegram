"""Backend reachability flag (updated from the polling loop)."""

import time
from typing import Optional

_available: bool = True
_down_since: Optional[float] = None


def is_backend_available() -> bool:
    return _available


def backend_down_since() -> Optional[float]:
    return _down_since


def downtime_hours(now: Optional[float] = None) -> float:
    if _down_since is None:
        return 0.0
    now = time.time() if now is None else now
    return max(0.0, (now - _down_since) / 3600.0)


def set_backend_available(available: bool, *, now: Optional[float] = None) -> None:
    global _available, _down_since
    now = time.time() if now is None else now
    if available:
        _available = True
        _down_since = None
        return
    _available = False
    if _down_since is None:
        _down_since = now