"""Top-level runtime entrypoint for the Jukebox application."""

from __future__ import annotations

import logging
import sys
from typing import Mapping, TextIO

from .adapters.feedback import TerminalStatusSink
from .adapters.input import ReadableInput, ScanLineReader
from .adapters.playback_spotify import SpotifyPlaybackBackend
from .adapters.playback_stub import StubPlaybackBackend
from .config import ConfigError, Settings, from_env
from .core.controller import Controller
from .core.deduper import DuplicateGate
from .core.models import PlaybackBackend
from .logging import StructuredEventLogger, configure_logging

LOGGER = logging.getLogger("jukebox.main")


def main(
    *,
    stdin: ReadableInput | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    """Load configuration, run the controller loop, and return an exit code."""

    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr

    try:
        settings = from_env(env)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=error_stream)
        return 2

    configure_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        environment=settings.environment,
        stream=error_stream,
    )

    try:
        playback_backend = _build_playback_backend(settings)
    except Exception as exc:
        print(f"Startup error: {exc}", file=error_stream)
        return 1

    controller = Controller(
        playback_backend=playback_backend,
        duplicate_gate=DuplicateGate(window_seconds=settings.duplicate_window_seconds),
        event_sinks=[TerminalStatusSink(output_stream), StructuredEventLogger()],
    )
    controller.emit_idle()
    LOGGER.info("jukebox controller started", extra={"backend": settings.playback_backend})

    try:
        for line in ScanLineReader(input_stream):
            controller.process_line(line)
    except KeyboardInterrupt:
        LOGGER.info("jukebox controller interrupted")
        return 130

    return 0


def _build_playback_backend(settings: Settings) -> PlaybackBackend:
    if settings.playback_backend == "spotify":
        assert settings.spotify_client_id is not None
        assert settings.spotify_client_secret is not None
        assert settings.spotify_refresh_token is not None
        return SpotifyPlaybackBackend(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            refresh_token=settings.spotify_refresh_token,
            device_id=settings.spotify_device_id,
        )
    return StubPlaybackBackend()
