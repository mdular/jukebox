"""Line-based input adapters."""

from __future__ import annotations

from typing import Iterator, Protocol


class ReadableInput(Protocol):
    """Minimal input contract for line-based scan ingestion."""

    def readline(self) -> str:
        """Return one input line or an empty string on EOF."""


class ScanLineReader:
    """Yield newline-terminated scan payloads from a text stream."""

    def __init__(self, stream: ReadableInput) -> None:
        self._stream = stream

    def __iter__(self) -> Iterator[str]:
        while True:
            line = self._stream.readline()
            if line == "":
                break
            yield line
