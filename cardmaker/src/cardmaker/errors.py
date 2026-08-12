"""Application errors safe to expose through the Card Maker HTTP API."""

from __future__ import annotations


class CardMakerError(Exception):
    """A classified, adult-readable failure at an application boundary."""

    def __init__(self, code: str, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after = retry_after
