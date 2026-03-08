"""Terminal feedback sinks."""

from __future__ import annotations

from typing import TextIO

from ..core.models import ControllerEvent


class TerminalStatusSink:
    """Render concise controller feedback to a terminal stream."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def handle(self, event: ControllerEvent) -> None:
        """Write one human-readable line for the event."""

        line = self._render(event)
        self._stream.write(f"{line}\n")
        self._stream.flush()

    def _render(self, event: ControllerEvent) -> str:
        if event.code == "idle":
            return "[IDLE] waiting for scan input"
        if event.code == "scan_received":
            return f"[SCAN] {event.payload}"
        if event.code == "scan_accepted":
            return f"[ACCEPTED] {event.uri_kind} {event.payload}"
        if event.code == "duplicate_suppressed":
            return f"[DUPLICATE] {event.message}"
        if event.code in {"invalid_payload", "unsupported_content"}:
            reason_code = event.reason_code or "error"
            return f"[ERROR {reason_code}] {event.message}"
        if event.code == "playback_dispatch_succeeded":
            return f"[PLAYBACK {event.backend}] dispatched {event.uri_kind}"
        if event.code == "playback_dispatch_failed":
            reason_code = event.reason_code or "error"
            return f"[PLAYBACK {event.backend}] failed: {reason_code}"
        return f"[EVENT {event.code}] {event.message}"
