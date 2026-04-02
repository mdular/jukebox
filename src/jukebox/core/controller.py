"""Controller orchestration for line-oriented scan input."""

from __future__ import annotations

from typing import Iterable

from ..adapters.action_router import ActionRouter
from ..operator_state import OperatorStateStore
from .cards import JukeboxActionCard, PlaybackMode
from .deduper import DuplicateGate
from .models import ControllerEvent, EventSink, PlaybackBackend, PlaybackRequest
from .parser import InvalidPayloadError, UnsupportedContentError, parse_scan_payload


class Controller:
    """Coordinates parsing, duplicate suppression, and playback dispatch."""

    def __init__(
        self,
        *,
        playback_backend: PlaybackBackend,
        duplicate_gate: DuplicateGate,
        action_router: ActionRouter | None = None,
        operator_state: OperatorStateStore | None = None,
        event_sinks: Iterable[EventSink] = (),
    ) -> None:
        self._playback_backend = playback_backend
        self._duplicate_gate = duplicate_gate
        self._action_router = action_router
        self._operator_state = operator_state
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
            card = parse_scan_payload(payload)
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

        if isinstance(card, JukeboxActionCard):
            if self._action_router is None:
                self._emit(
                    ControllerEvent(
                        code="action_failed",
                        message="unsupported action",
                        payload=payload,
                        card_kind="action",
                        action_name=card.action_id,
                        reason_code="unsupported_action",
                    )
                )
                return
            self._emit(
                ControllerEvent(
                    code="action_card_accepted",
                    message=f"accepted action {card.action_id}",
                    payload=payload,
                    card_kind="action",
                    action_name=card.action_id,
                )
            )
            action_result = self._action_router.execute(card)
            event = ControllerEvent(
                code="action_succeeded" if action_result.ok else "action_failed",
                message=action_result.message,
                payload=payload,
                card_kind="action",
                action_name=action_result.action_id,
                action_scope=action_result.action_scope,
                reason_code=action_result.reason_code,
                playback_mode=action_result.playback_mode,
                setup_mode=action_result.setup_mode,
            )
            self._emit(event)
            if action_result.ok and action_result.playback_mode is not None:
                self._emit(
                    ControllerEvent(
                        code="playback_mode_changed",
                        message=f"playback mode set to {action_result.playback_mode}",
                        payload=payload,
                        card_kind="action",
                        action_name=action_result.action_id,
                        action_scope=action_result.action_scope,
                        playback_mode=action_result.playback_mode,
                    )
                )
            return

        uri = card
        if self._duplicate_gate.is_duplicate(payload):
            self._emit(
                ControllerEvent(
                    code="duplicate_suppressed",
                    message=f"ignored within {self._duplicate_gate.window_seconds:.1f}s",
                    payload=payload,
                    card_kind="media",
                    uri_kind=uri.kind,
                )
            )
            return

        self._emit(
            ControllerEvent(
                code="scan_accepted",
                message=f"accepted {uri.kind} {payload}",
                payload=payload,
                card_kind="media",
                uri_kind=uri.kind,
            )
        )

        playback_mode: PlaybackMode = "replace"
        if self._operator_state is not None:
            playback_mode = self._operator_state.load().playback_mode

        if playback_mode == "queue_tracks" and uri.kind == "track":
            playback_result = self._playback_backend.enqueue(PlaybackRequest(uri=uri))
            success_code = "playback_enqueued"
            success_message = f"queued {uri.kind}"
        else:
            if playback_mode == "queue_tracks" and uri.kind in {"album", "playlist"}:
                self._emit(
                    ControllerEvent(
                        code="playback_mode_fallback",
                        message=f"queue mode falls back to replace for {uri.kind}",
                        payload=payload,
                        card_kind="media",
                        uri_kind=uri.kind,
                        playback_mode=playback_mode,
                    )
                )
            playback_result = self._playback_backend.dispatch(PlaybackRequest(uri=uri))
            success_code = "playback_dispatch_succeeded"
            success_message = f"dispatched {uri.kind}"
        if playback_result.ok:
            self._duplicate_gate.record_success(payload)
            self._emit(
                ControllerEvent(
                    code=success_code,
                    message=success_message,
                    payload=payload,
                    card_kind="media",
                    uri_kind=uri.kind,
                    backend=playback_result.backend,
                    device_name=playback_result.device_name,
                    playback_mode=playback_mode,
                )
            )
            return

        self._emit(
            ControllerEvent(
                code="playback_dispatch_failed",
                message=playback_result.message or "playback dispatch failed",
                payload=payload,
                card_kind="media",
                uri_kind=uri.kind,
                backend=playback_result.backend,
                reason_code=playback_result.reason_code,
                device_name=playback_result.device_name,
                playback_mode=playback_mode,
            )
        )

    def _emit(self, event: ControllerEvent) -> None:
        for sink in self._event_sinks:
            sink.handle(event)
