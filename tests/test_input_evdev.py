"""Tests for the Linux evdev scanner input adapter."""

from __future__ import annotations

import unittest
from typing import Iterator

from jukebox.adapters.input_evdev import EvdevScannerInput, ScannerKeyEvent


class EvdevScannerInputTests(unittest.TestCase):
    def test_reads_one_newline_terminated_scan_from_key_presses(self) -> None:
        scanner = EvdevScannerInput(
            "/dev/input/by-id/scanner-event-kbd",
            event_stream_factory=lambda path: iter(
                [
                    ScannerKeyEvent("KEY_S"),
                    ScannerKeyEvent("KEY_P"),
                    ScannerKeyEvent("KEY_O"),
                    ScannerKeyEvent("KEY_T"),
                    ScannerKeyEvent("KEY_I"),
                    ScannerKeyEvent("KEY_F"),
                    ScannerKeyEvent("KEY_Y"),
                    ScannerKeyEvent("KEY_COLON"),
                    ScannerKeyEvent("KEY_T"),
                    ScannerKeyEvent("KEY_R"),
                    ScannerKeyEvent("KEY_A"),
                    ScannerKeyEvent("KEY_C"),
                    ScannerKeyEvent("KEY_K"),
                    ScannerKeyEvent("KEY_COLON"),
                    ScannerKeyEvent("KEY_1"),
                    ScannerKeyEvent("KEY_2"),
                    ScannerKeyEvent("KEY_3"),
                    ScannerKeyEvent("KEY_ENTER"),
                ]
            ),
        )

        self.assertEqual(scanner.readline(), "spotify:track:123\n")

    def test_ignores_releases_and_empty_scans(self) -> None:
        scanner = EvdevScannerInput(
            "/dev/input/by-id/scanner-event-kbd",
            event_stream_factory=lambda path: iter(
                [
                    ScannerKeyEvent("KEY_A", is_press=False),
                    ScannerKeyEvent("KEY_ENTER"),
                    ScannerKeyEvent("KEY_S"),
                    ScannerKeyEvent("KEY_1", is_press=False),
                    ScannerKeyEvent("KEY_1"),
                    ScannerKeyEvent("KEY_ENTER"),
                ]
            ),
        )

        self.assertEqual(scanner.readline(), "s1\n")

    def test_preserves_shifted_letters_and_colons_from_scanner(self) -> None:
        scanner = EvdevScannerInput(
            "/dev/input/by-id/scanner-event-kbd",
            event_stream_factory=lambda path: iter(
                [
                    ScannerKeyEvent("KEY_S"),
                    ScannerKeyEvent("KEY_P"),
                    ScannerKeyEvent("KEY_O"),
                    ScannerKeyEvent("KEY_T"),
                    ScannerKeyEvent("KEY_I"),
                    ScannerKeyEvent("KEY_F"),
                    ScannerKeyEvent("KEY_Y"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_SEMICOLON"),
                    ScannerKeyEvent("KEY_SEMICOLON", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_T"),
                    ScannerKeyEvent("KEY_R"),
                    ScannerKeyEvent("KEY_A"),
                    ScannerKeyEvent("KEY_C"),
                    ScannerKeyEvent("KEY_K"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_SEMICOLON"),
                    ScannerKeyEvent("KEY_SEMICOLON", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_2"),
                    ScannerKeyEvent("KEY_3"),
                    ScannerKeyEvent("KEY_D"),
                    ScannerKeyEvent("KEY_F"),
                    ScannerKeyEvent("KEY_Q"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_X"),
                    ScannerKeyEvent("KEY_X", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_3"),
                    ScannerKeyEvent("KEY_N"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_R"),
                    ScannerKeyEvent("KEY_R", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_S"),
                    ScannerKeyEvent("KEY_P"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_R"),
                    ScannerKeyEvent("KEY_R", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_F"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_H"),
                    ScannerKeyEvent("KEY_H", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_T"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_V"),
                    ScannerKeyEvent("KEY_V", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_G"),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_O"),
                    ScannerKeyEvent("KEY_O", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_V"),
                    ScannerKeyEvent("KEY_V", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT"),
                    ScannerKeyEvent("KEY_U"),
                    ScannerKeyEvent("KEY_U", is_press=False),
                    ScannerKeyEvent("KEY_LEFTSHIFT", is_press=False),
                    ScannerKeyEvent("KEY_9"),
                    ScannerKeyEvent("KEY_5"),
                    ScannerKeyEvent("KEY_ENTER"),
                ]
            ),
        )

        self.assertEqual(scanner.readline(), "spotify:track:23dfqX3nRspRfHtVgOVU95\n")

    def test_status_reports_unavailable_until_the_device_can_be_opened(self) -> None:
        attempts = {"count": 0}

        def factory(path: str) -> list[ScannerKeyEvent] | Iterator[ScannerKeyEvent]:
            del path
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise OSError("cannot open scanner")
            return iter([ScannerKeyEvent("KEY_S"), ScannerKeyEvent("KEY_ENTER")])

        scanner = EvdevScannerInput(
            "/dev/input/by-id/scanner-event-kbd",
            event_stream_factory=factory,
            sleeper=lambda seconds: None,
        )

        unavailable = scanner.status()
        line = scanner.readline()
        ready = scanner.status()

        self.assertFalse(unavailable.ready)
        self.assertEqual(unavailable.code, "scanner_unavailable")
        self.assertEqual(line, "s\n")
        self.assertTrue(ready.ready)
        self.assertEqual(ready.code, "ready")

    def test_disconnect_clears_the_partial_buffer_before_reconnect(self) -> None:
        scanner = EvdevScannerInput(
            "/dev/input/by-id/scanner-event-kbd",
            event_stream_factory=_ReconnectFactory(
                [
                    _disconnecting_stream(
                        [
                            ScannerKeyEvent("KEY_S"),
                            ScannerKeyEvent("KEY_P"),
                            ScannerKeyEvent("KEY_O"),
                        ]
                    ),
                    iter(
                        [
                            ScannerKeyEvent("KEY_S"),
                            ScannerKeyEvent("KEY_P"),
                            ScannerKeyEvent("KEY_O"),
                            ScannerKeyEvent("KEY_T"),
                            ScannerKeyEvent("KEY_I"),
                            ScannerKeyEvent("KEY_F"),
                            ScannerKeyEvent("KEY_Y"),
                            ScannerKeyEvent("KEY_COLON"),
                            ScannerKeyEvent("KEY_T"),
                            ScannerKeyEvent("KEY_R"),
                            ScannerKeyEvent("KEY_A"),
                            ScannerKeyEvent("KEY_C"),
                            ScannerKeyEvent("KEY_K"),
                            ScannerKeyEvent("KEY_COLON"),
                            ScannerKeyEvent("KEY_1"),
                            ScannerKeyEvent("KEY_2"),
                            ScannerKeyEvent("KEY_3"),
                            ScannerKeyEvent("KEY_ENTER"),
                        ]
                    ),
                ]
            ),
            sleeper=lambda seconds: None,
        )

        self.assertEqual(scanner.readline(), "spotify:track:123\n")
class _ReconnectFactory:
    def __init__(self, streams: list[Iterator[ScannerKeyEvent]]) -> None:
        self._streams = streams

    def __call__(self, path: str) -> Iterator[ScannerKeyEvent]:
        del path
        return self._streams.pop(0)


def _disconnecting_stream(events: list[ScannerKeyEvent]) -> Iterator[ScannerKeyEvent]:
    for event in events:
        yield event
    raise OSError("scanner disconnected")
