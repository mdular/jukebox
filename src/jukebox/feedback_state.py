"""Shared user-facing feedback snapshot tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .core.models import ControllerEvent


@dataclass(frozen=True)
class FeedbackSnapshot:
    """Current user-facing feedback state."""

    display_state: str = "booting"
    message: str = "waiting for scanner and receiver"
    reason_code: str | None = None
    device_name: str | None = None
    playback_mode: str | None = None
    setup_mode: str | None = None
    action_name: str | None = None
    updated_at: float = 0.0


class FeedbackStateTracker:
    """Consume controller events into one reusable snapshot."""

    def __init__(self) -> None:
        self._snapshot = FeedbackSnapshot(updated_at=time.time())

    def handle(self, event: ControllerEvent) -> None:
        self._snapshot = FeedbackSnapshot(
            display_state=event.code,
            message=event.message,
            reason_code=event.reason_code,
            device_name=event.device_name,
            playback_mode=event.playback_mode or self._snapshot.playback_mode,
            setup_mode=event.setup_mode or self._snapshot.setup_mode,
            action_name=event.action_name,
            updated_at=time.time(),
        )

    def snapshot(self) -> FeedbackSnapshot:
        """Return the latest feedback snapshot."""

        return self._snapshot
