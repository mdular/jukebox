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
        if event.code == "booting":
            return "[BOOT] waiting for scanner and receiver"
        if event.code in {"idle", "ready"}:
            return "[READY] waiting for scan input"
        if event.code == "scanner_unavailable":
            reason_code = event.reason_code or "error"
            return f"[SCANNER] unavailable: {reason_code}"
        if event.code == "controller_auth_unavailable":
            reason_code = event.reason_code or "error"
            return f"[API AUTH] unavailable: {reason_code}"
        if event.code == "network_unavailable":
            reason_code = event.reason_code or "error"
            return f"[NETWORK] unavailable: {reason_code}"
        if event.code == "receiver_unavailable":
            reason_code = event.reason_code or "error"
            return f"[RECEIVER] unavailable: {reason_code}"
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
            device_fragment = f" on {event.device_name}" if event.device_name else ""
            return f"[PLAYBACK {event.backend}] started {event.uri_kind}{device_fragment}"
        if event.code == "playback_dispatch_failed":
            reason_code = event.reason_code or "error"
            return f"[PLAYBACK {event.backend}] failed: {reason_code}"
        return f"[EVENT {event.code}] {event.message}"
