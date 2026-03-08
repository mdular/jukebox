"""Top-level runtime entrypoint for the Jukebox application."""

from __future__ import annotations

import logging
import sys
from typing import Callable, Mapping, TextIO

from .adapters.feedback import TerminalStatusSink
from .adapters.input import ReadableInput, ScanLineReader
from .config import ConfigError, Settings, from_env
from .core.controller import Controller
from .core.deduper import DuplicateGate
from .core.models import ControllerEvent, EventSink
from .logging import StructuredEventLogger, configure_logging
from .runtime import RuntimeDependencies, StartupError, build_runtime

LOGGER = logging.getLogger("jukebox.main")
RuntimeFactory = Callable[[Settings, ReadableInput], RuntimeDependencies]


def main(
    *,
    stdin: ReadableInput | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: Mapping[str, str] | None = None,
    runtime_factory: RuntimeFactory | None = None,
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

    event_sinks: list[EventSink] = [TerminalStatusSink(output_stream), StructuredEventLogger()]
    _emit_event(event_sinks, ControllerEvent(code="booting", message="waiting for scanner and receiver"))

    try:
        runtime = (build_runtime if runtime_factory is None else runtime_factory)(settings, input_stream)
    except StartupError as exc:
        _emit_event(
            event_sinks,
            ControllerEvent(
                code=exc.code,
                message=exc.message,
                backend=exc.backend,
                reason_code=exc.reason_code,
                device_name=exc.device_name,
                source=exc.source,
            ),
        )
        return 1
    except Exception as exc:
        print(f"Startup error: {exc}", file=error_stream)
        return 1

    controller = Controller(
        playback_backend=runtime.playback_backend,
        duplicate_gate=DuplicateGate(window_seconds=settings.duplicate_window_seconds),
        event_sinks=event_sinks,
    )
    controller.emit_ready(source=runtime.source)
    LOGGER.info("jukebox controller started", extra={"backend": settings.playback_backend})

    try:
        for line in ScanLineReader(runtime.input_stream):
            controller.process_line(line)
    except KeyboardInterrupt:
        LOGGER.info("jukebox controller interrupted")
        return 130

    return 0


def _emit_event(event_sinks: list[EventSink], event: ControllerEvent) -> None:
    for sink in event_sinks:
        sink.handle(event)
