"""Bounded, in-memory fetching for Spotify-provided raster artwork."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from io import BytesIO
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from cardmaker.errors import CardMakerError
from cardmaker.models import ArtworkReference

SUPPORTED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class ArtworkResponseLike(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, amount: int = -1) -> bytes:
        """Read at most ``amount`` response bytes."""

    def close(self) -> None:
        """Release network response resources."""


Requester = Callable[[Request, float], ArtworkResponseLike]


class ArtworkHttpFetcher:
    """Download one catalog-owned artwork image without persistence."""

    def __init__(
        self,
        *,
        requester: Requester | None = None,
        timeout_seconds: float = 5.0,
        max_response_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive.")
        self._requester = _default_requester if requester is None else requester
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    def fetch(self, reference: ArtworkReference) -> Image.Image:
        """Fetch, validate, decode, and detach one RGB image in memory."""

        parsed = urlsplit(reference.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise _artwork_error("Spotify artwork must use a valid HTTPS URL.")

        request = Request(
            reference.url,
            headers={"Accept": "image/jpeg,image/png,image/webp"},
            method="GET",
        )
        try:
            response = self._requester(request, self._timeout_seconds)
        except (HTTPError, URLError, TimeoutError, OSError):
            raise _artwork_error("Spotify artwork is temporarily unavailable.") from None

        try:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in SUPPORTED_CONTENT_TYPES:
                raise _artwork_error("Spotify artwork did not use a supported raster format.")
            body = response.read(self._max_response_bytes + 1)
            if len(body) > self._max_response_bytes:
                raise _artwork_error("Spotify artwork is too large to render safely.")
        finally:
            response.close()

        try:
            with Image.open(BytesIO(body)) as source:
                source.load()
                return source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise _artwork_error("Spotify artwork could not be decoded safely.") from None


def _artwork_error(message: str) -> CardMakerError:
    return CardMakerError("artwork_unavailable", message)


def _default_requester(request: Request, timeout: float) -> ArtworkResponseLike:
    return cast(ArtworkResponseLike, urlopen(request, timeout=timeout))
