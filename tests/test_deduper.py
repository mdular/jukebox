"""Tests for duplicate suppression."""

import unittest

from jukebox.core.deduper import DuplicateGate


class DuplicateGateTests(unittest.TestCase):
    def test_duplicate_is_suppressed_within_window(self) -> None:
        clock = _FakeClock([10.0, 11.5])
        gate = DuplicateGate(window_seconds=2.0, clock=clock)

        self.assertFalse(gate.is_duplicate("spotify:track:6rqhFgbbKwnb9MLmUQDhG6"))
        gate.record_success("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")

        self.assertTrue(gate.is_duplicate("spotify:track:6rqhFgbbKwnb9MLmUQDhG6"))

    def test_duplicate_is_accepted_after_window_expires(self) -> None:
        clock = _FakeClock([10.0, 12.1])
        gate = DuplicateGate(window_seconds=2.0, clock=clock)

        gate.record_success("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")

        self.assertFalse(gate.is_duplicate("spotify:track:6rqhFgbbKwnb9MLmUQDhG6"))

    def test_only_last_successful_payload_is_considered(self) -> None:
        clock = _FakeClock([10.0, 11.0])
        gate = DuplicateGate(window_seconds=2.0, clock=clock)

        gate.record_success("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")

        self.assertFalse(gate.is_duplicate("spotify:album:1ATL5GLyefJaxhQzSPVrLX"))


class _FakeClock:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def __call__(self) -> float:
        return self._values.pop(0)
