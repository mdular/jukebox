"""Stub playback backend for local validation."""

from __future__ import annotations

from ..core.models import PlaybackRequest, PlaybackResult
from ..runtime_health import DependencyStatus


class StubPlaybackBackend:
    """A no-op playback backend that reports what would be played."""

    def __init__(self) -> None:
        self._active = False

    def probe(self) -> PlaybackResult:
        """Report that the stub backend is ready."""

        return PlaybackResult(ok=True, backend="stub", message="Stub backend ready.")

    def status(self) -> DependencyStatus:
        """Report that the stub backend is ready."""

        return DependencyStatus(
            code="ready",
            ready=True,
            message="waiting for scan input",
            backend="stub",
        )

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Return a successful dispatch result without side effects."""

        self._active = True
        return PlaybackResult(
            ok=True,
            backend="stub",
            message=f"Would play {request.uri.kind} {request.uri.raw}",
        )

    def enqueue(self, request: PlaybackRequest) -> PlaybackResult:
        """Return a successful queue result without side effects."""

        return PlaybackResult(
            ok=True,
            backend="stub",
            message=f"Would queue {request.uri.kind} {request.uri.raw}",
        )

    def stop(self) -> PlaybackResult:
        """Return a successful stop result without side effects."""

        self._active = False
        return PlaybackResult(ok=True, backend="stub", message="Would stop playback")

    def skip_next(self) -> PlaybackResult:
        """Return a successful next-track result without side effects."""

        return PlaybackResult(ok=True, backend="stub", message="Would skip to next track")

    def set_volume_percent(self, percent: int) -> PlaybackResult:
        """Return a successful volume result without side effects."""

        return PlaybackResult(ok=True, backend="stub", message=f"Would set volume to {percent}%")

    def player_active(self) -> bool | None:
        """Return whether the stub backend currently considers playback active."""

        return self._active
