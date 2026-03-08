"""Controller orchestration for line-oriented scan input."""

from __future__ import annotations

from typing import Iterable

from .deduper import DuplicateGate
from .models import ControllerEvent, EventSink, PlaybackBackend, PlaybackRequest
from .parser import InvalidPayloadError, UnsupportedContentError, parse_spotify_uri


class Controller:
    """Coordinates parsing, duplicate suppression, and playback dispatch."""

    def __init__(
        self,
        *,
        playback_backend: PlaybackBackend,
        duplicate_gate: DuplicateGate,
        event_sinks: Iterable[EventSink] = (),
    ) -> None:
        self._playback_backend = playback_backend
        self._duplicate_gate = duplicate_gate
        self._event_sinks = list(event_sinks)

    def emit_idle(self) -> None:
        """Emit the initial idle state."""

        self._emit(ControllerEvent(code="idle", message="waiting for scan input"))

    def emit_ready(self, *, source: str | None = None) -> None:
        """Emit the scan-ready state."""

        self._emit(ControllerEvent(code="ready", message="waiting for scan input", source=source))

    def process_line(self, raw_line: str) -> None:
        """Process one raw input line."""

        payload = raw_line.rstrip("\r\n")
        if payload == "":
            return

        self._emit(ControllerEvent(code="scan_received", message="scan received", payload=payload))

        try:
            uri = parse_spotify_uri(payload)
        except InvalidPayloadError as exc:
            self._emit(
                ControllerEvent(
                    code="invalid_payload",
                    message=str(exc),
                    payload=payload,
                    reason_code=exc.reason_code,
                )
            )
            return
        except UnsupportedContentError as exc:
            self._emit(
                ControllerEvent(
                    code="unsupported_content",
                    message=str(exc),
                    payload=payload,
                    reason_code=exc.reason_code,
                )
            )
            return

        if self._duplicate_gate.is_duplicate(payload):
            self._emit(
                ControllerEvent(
                    code="duplicate_suppressed",
                    message=f"ignored within {self._duplicate_gate.window_seconds:.1f}s",
                    payload=payload,
                    uri_kind=uri.kind,
                )
            )
            return

        self._emit(
            ControllerEvent(
                code="scan_accepted",
                message=f"accepted {uri.kind} {payload}",
                payload=payload,
                uri_kind=uri.kind,
            )
        )

        result = self._playback_backend.dispatch(PlaybackRequest(uri=uri))
        if result.ok:
            self._duplicate_gate.record_success(payload)
            self._emit(
                ControllerEvent(
                    code="playback_dispatch_succeeded",
                    message=f"dispatched {uri.kind}",
                    payload=payload,
                    uri_kind=uri.kind,
                    backend=result.backend,
                    device_name=result.device_name,
                )
            )
            return

        self._emit(
            ControllerEvent(
                code="playback_dispatch_failed",
                message=result.message or "playback dispatch failed",
                payload=payload,
                uri_kind=uri.kind,
                backend=result.backend,
                reason_code=result.reason_code,
                device_name=result.device_name,
            )
        )

    def _emit(self, event: ControllerEvent) -> None:
        for sink in self._event_sinks:
            sink.handle(event)
