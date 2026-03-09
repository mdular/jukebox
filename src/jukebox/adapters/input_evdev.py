"""Linux evdev-based scanner input adapter."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from ..runtime_health import DependencyStatus
from .input import ReadableInput

EventStreamFactory = Callable[[str], Iterable["ScannerKeyEvent"]]
Sleeper = Callable[[float], None]

_ENTER_KEYS = frozenset({"KEY_ENTER", "KEY_KPENTER"})
_SHIFT_KEYS = frozenset({"KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"})
_UNSHIFTED_KEYCODE_TO_CHAR = {
    "KEY_0": "0",
    "KEY_1": "1",
    "KEY_2": "2",
    "KEY_3": "3",
    "KEY_4": "4",
    "KEY_5": "5",
    "KEY_6": "6",
    "KEY_7": "7",
    "KEY_8": "8",
    "KEY_9": "9",
    "KEY_A": "a",
    "KEY_B": "b",
    "KEY_C": "c",
    "KEY_D": "d",
    "KEY_E": "e",
    "KEY_F": "f",
    "KEY_G": "g",
    "KEY_H": "h",
    "KEY_I": "i",
    "KEY_J": "j",
    "KEY_K": "k",
    "KEY_L": "l",
    "KEY_M": "m",
    "KEY_N": "n",
    "KEY_O": "o",
    "KEY_P": "p",
    "KEY_Q": "q",
    "KEY_R": "r",
    "KEY_S": "s",
    "KEY_T": "t",
    "KEY_U": "u",
    "KEY_V": "v",
    "KEY_W": "w",
    "KEY_X": "x",
    "KEY_Y": "y",
    "KEY_Z": "z",
    "KEY_SEMICOLON": ";",
    "KEY_COLON": ":",
}
_SHIFTED_KEYCODE_TO_CHAR = {
    **{f"KEY_{digit}": digit for digit in "0123456789"},
    **{f"KEY_{letter}": letter for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    "KEY_SEMICOLON": ":",
    "KEY_COLON": ":",
}


@dataclass(frozen=True)
class ScannerKeyEvent:
    """One normalized key press emitted by the scanner."""

    keycode: str
    is_press: bool = True


class EvdevScannerInput(ReadableInput):
    """Assemble newline-terminated scan lines from Linux input events."""

    def __init__(
        self,
        scanner_device: str,
        *,
        event_stream_factory: EventStreamFactory | None = None,
        reconnect_delay_seconds: float = 1.0,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._scanner_device = scanner_device
        self._event_stream_factory = (
            _default_event_stream_factory if event_stream_factory is None else event_stream_factory
        )
        self._events: Iterator[ScannerKeyEvent] | None = None
        self._buffer: list[str] = []
        self._shift_pressed = False
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._sleeper = time.sleep if sleeper is None else sleeper
        self._lock = threading.Lock()
        self._status = DependencyStatus(
            code="scanner_unavailable",
            ready=False,
            message="Scanner device unavailable.",
            reason_code="scanner_unavailable",
            source="evdev",
        )

    def status(self) -> DependencyStatus:
        """Return the current scanner status, attempting to reconnect if needed."""

        self._ensure_event_stream()
        with self._lock:
            return self._status

    def readline(self) -> str:
        while True:
            events = self._ensure_event_stream()
            if events is None:
                self._sleeper(self._reconnect_delay_seconds)
                continue

            try:
                event = next(events)
            except StopIteration:
                self._mark_unavailable("Scanner stream ended unexpectedly.")
                self._sleeper(self._reconnect_delay_seconds)
                continue
            except OSError as exc:
                self._mark_unavailable(f"Scanner device unavailable: {exc}")
                self._sleeper(self._reconnect_delay_seconds)
                continue

            if event.keycode in _SHIFT_KEYS:
                self._shift_pressed = event.is_press
                continue
            if not event.is_press:
                continue
            if event.keycode in _ENTER_KEYS:
                if not self._buffer:
                    continue
                line = "".join(self._buffer)
                self._buffer.clear()
                return f"{line}\n"

            character = _map_keycode_to_char(event.keycode, shift_pressed=self._shift_pressed)
            if character is not None:
                self._buffer.append(character)

    def _ensure_event_stream(self) -> Iterator[ScannerKeyEvent] | None:
        with self._lock:
            if self._events is not None:
                return self._events
            try:
                events = iter(self._event_stream_factory(self._scanner_device))
            except OSError as exc:
                self._status = DependencyStatus(
                    code="scanner_unavailable",
                    ready=False,
                    message=f"Scanner device unavailable: {exc}",
                    reason_code="scanner_unavailable",
                    source="evdev",
                )
                return None

            self._events = events
            self._buffer.clear()
            self._shift_pressed = False
            self._status = DependencyStatus(
                code="ready",
                ready=True,
                message="waiting for scan input",
                source="evdev",
            )
            return self._events

    def _mark_unavailable(self, message: str) -> None:
        with self._lock:
            self._events = None
            self._buffer.clear()
            self._shift_pressed = False
            self._status = DependencyStatus(
                code="scanner_unavailable",
                ready=False,
                message=message,
                reason_code="scanner_unavailable",
                source="evdev",
            )


def _default_event_stream_factory(scanner_device: str) -> Iterator[ScannerKeyEvent]:
    try:
        from evdev import InputDevice, categorize, ecodes  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise OSError(
            "evdev is not installed. Install the 'pi' extras for scanner support."
        ) from exc

    device = InputDevice(scanner_device)
    for event in device.read_loop():
        if event.type != ecodes.EV_KEY:
            continue
        key_event = categorize(event)
        keycode = key_event.keycode
        if isinstance(keycode, list):
            keycode = keycode[0]
        yield ScannerKeyEvent(
            keycode=str(keycode),
            is_press=bool(key_event.keystate == key_event.key_down),
        )


def _map_keycode_to_char(keycode: str, *, shift_pressed: bool) -> str | None:
    if shift_pressed:
        return _SHIFTED_KEYCODE_TO_CHAR.get(keycode)
    return _UNSHIFTED_KEYCODE_TO_CHAR.get(keycode)
