"""Stub playback backend for local validation."""

from __future__ import annotations

from ..core.models import PlaybackRequest, PlaybackResult


class StubPlaybackBackend:
    """A no-op playback backend that reports what would be played."""

    def probe(self) -> PlaybackResult:
        """Report that the stub backend is ready."""

        return PlaybackResult(ok=True, backend="stub", message="Stub backend ready.")

    def dispatch(self, request: PlaybackRequest) -> PlaybackResult:
        """Return a successful dispatch result without side effects."""

        return PlaybackResult(
            ok=True,
            backend="stub",
            message=f"Would play {request.uri.kind} {request.uri.raw}",
        )
