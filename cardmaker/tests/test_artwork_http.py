from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from urllib.request import Request

import pytest
from PIL import Image

from cardmaker.adapters.artwork_http import ArtworkHttpFetcher, ArtworkResponseLike
from cardmaker.errors import CardMakerError
from cardmaker.models import ArtworkReference


def test_fetch_decodes_supported_artwork_to_rgb_and_closes_response() -> None:
    response = FakeArtworkResponse(png_bytes(mode="RGBA"), content_type="image/png")
    requester = RecordingRequester(response)
    fetcher = ArtworkHttpFetcher(requester=requester)

    image = fetcher.fetch(ArtworkReference("https://i.scdn.co/artwork.png", 2, 3))

    assert image.mode == "RGB"
    assert image.size == (2, 3)
    assert image.getpixel((0, 0)) == (20, 40, 60)
    assert response.closed
    assert requester.requests[0].get_header("Accept") == "image/jpeg,image/png,image/webp"
    assert requester.timeouts == [5.0]


def test_fetch_rejects_non_https_without_making_a_request() -> None:
    requester = RecordingRequester(FakeArtworkResponse(png_bytes()))
    fetcher = ArtworkHttpFetcher(requester=requester)

    with pytest.raises(CardMakerError) as raised:
        fetcher.fetch(ArtworkReference("http://i.scdn.co/artwork.png"))

    assert raised.value.code == "artwork_unavailable"
    assert requester.requests == []


@pytest.mark.parametrize(
    "content_type",
    ["text/html", "image/svg+xml", "application/octet-stream", ""],
)
def test_fetch_rejects_unsupported_content_types_and_closes_response(
    content_type: str,
) -> None:
    response = FakeArtworkResponse(png_bytes(), content_type=content_type)
    fetcher = ArtworkHttpFetcher(requester=RecordingRequester(response))

    with pytest.raises(CardMakerError) as raised:
        fetcher.fetch(ArtworkReference("https://i.scdn.co/artwork"))

    assert raised.value.code == "artwork_unavailable"
    assert response.closed


def test_fetch_rejects_oversized_response_without_retaining_it() -> None:
    response = FakeArtworkResponse(b"x" * 33, content_type="image/jpeg")
    fetcher = ArtworkHttpFetcher(
        requester=RecordingRequester(response), max_response_bytes=32
    )

    with pytest.raises(CardMakerError, match="too large"):
        fetcher.fetch(ArtworkReference("https://i.scdn.co/artwork.jpg"))

    assert response.closed


def test_fetch_rejects_invalid_raster_bytes() -> None:
    response = FakeArtworkResponse(b"not an image", content_type="image/png")
    fetcher = ArtworkHttpFetcher(requester=RecordingRequester(response))

    with pytest.raises(CardMakerError) as raised:
        fetcher.fetch(ArtworkReference("https://i.scdn.co/artwork.png"))

    assert raised.value.code == "artwork_unavailable"
    assert response.closed


class FakeArtworkResponse:
    status = 200
    headers: Mapping[str, str]

    def __init__(self, body: bytes, *, content_type: str = "image/png") -> None:
        self._body = body
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def read(self, amount: int = -1) -> bytes:
        return self._body if amount < 0 else self._body[:amount]

    def close(self) -> None:
        self.closed = True


class RecordingRequester:
    def __init__(self, response: ArtworkResponseLike) -> None:
        self.response = response
        self.requests: list[Request] = []
        self.timeouts: list[float] = []

    def __call__(self, request: Request, timeout: float) -> ArtworkResponseLike:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return self.response


def png_bytes(*, mode: str = "RGB") -> bytes:
    color: tuple[int, ...] = (20, 40, 60, 128) if mode == "RGBA" else (20, 40, 60)
    image = Image.new(mode, (2, 3), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
