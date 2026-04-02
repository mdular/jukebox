"""Duplicate suppression logic."""

from __future__ import annotations

import time
from typing import Callable

Clock = Callable[[], float]


class DuplicateGate:
    """Tracks the last successful dispatch for duplicate suppression."""

    def __init__(self, *, window_seconds: float, clock: Clock | None = None) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")
        self._window_seconds = window_seconds
        self._clock = time.monotonic if clock is None else clock
        self._last_payload: str | None = None
        self._last_success_monotonic: float | None = None

    @property
    def window_seconds(self) -> float:
        """Return the configured duplicate window."""

        return self._window_seconds

    def is_duplicate(self, payload: str) -> bool:
        """Return whether the payload should be suppressed as a duplicate."""

        if self._last_payload != payload or self._last_success_monotonic is None:
            return False
        return (self._clock() - self._last_success_monotonic) <= self._window_seconds

    def record_success(self, payload: str) -> None:
        """Record a successful dispatch for future duplicate suppression."""

        self._last_payload = payload
        self._last_success_monotonic = self._clock()


class ActionDebounceGate(DuplicateGate):
    """Reuse duplicate-gate timing for idempotent action-card scans."""
