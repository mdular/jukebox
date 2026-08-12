"""Spotify public catalog adapter using client-credentials authorization."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cardmaker.errors import CardMakerError
from cardmaker.models import (
    ArtworkReference,
    CatalogItem,
    SpotifyKind,
    SpotifyReference,
)

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"
SEARCH_LIMIT = 5


class ResponseLike(Protocol):
    """Minimal response shape needed from the injected HTTP requester."""

    status: int

    def read(self) -> bytes:
        """Read the response body."""

    def close(self) -> None:
        """Release the response resources."""


Requester = Callable[[Request, float], ResponseLike]
Clock = Callable[[], float]


class SpotifyCatalog:
    """Search and resolve supported Spotify catalog entities."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        market: str,
        requester: Requester | None = None,
        timeout_seconds: float = 5.0,
        clock: Clock | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._market = market.upper()
        self._requester = _default_requester if requester is None else requester
        self._timeout_seconds = timeout_seconds
        self._clock = time.monotonic if clock is None else clock
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0

    def search(self, query: str) -> tuple[CatalogItem, ...]:
        """Return up to five results per supported entity type."""

        request = self._authorized_request(
            f"{API_URL}/search?"
            + urlencode(
                {
                    "q": query,
                    "type": "track,album,playlist",
                    "market": self._market,
                    "limit": str(SEARCH_LIMIT),
                }
            )
        )
        payload = self._request_json(request, operation="catalog")
        if not isinstance(payload, dict):
            raise _unavailable("Spotify search returned an invalid response.")

        results: list[CatalogItem] = []
        for kind, bucket_name in (
            ("track", "tracks"),
            ("album", "albums"),
            ("playlist", "playlists"),
        ):
            bucket = payload.get(bucket_name)
            if not isinstance(bucket, dict) or not isinstance(bucket.get("items"), list):
                raise _unavailable("Spotify search returned an invalid response.")
            for raw_item in bucket["items"]:
                if raw_item is None:
                    continue
                results.append(_map_item(cast(SpotifyKind, kind), raw_item))
        return tuple(results)

    def resolve(self, reference: SpotifyReference) -> CatalogItem:
        """Resolve one canonical reference through the matching entity endpoint."""

        request = self._authorized_request(
            f"{API_URL}/{reference.kind}s/{reference.spotify_id}?"
            + urlencode({"market": self._market})
        )
        payload = self._request_json(request, operation="catalog")
        return _map_item(reference.kind, payload, expected_reference=reference)

    def _authorized_request(self, url: str) -> Request:
        token = self._access_token_value()
        return Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")

    def _access_token_value(self) -> str:
        now = self._clock()
        if self._access_token is not None and now < self._access_token_expires_at:
            return self._access_token

        encoded_credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            TOKEN_URL,
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        payload = self._request_json(request, operation="token")
        if not isinstance(payload, dict):
            raise CardMakerError(
                "spotify_auth_failed", "Spotify authentication returned an invalid response."
            )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise CardMakerError(
                "spotify_auth_failed", "Spotify authentication did not return an access token."
            )
        raw_expiry = payload.get("expires_in", 3600)
        expires_in = raw_expiry if isinstance(raw_expiry, int) else 3600
        self._access_token = token
        self._access_token_expires_at = now + max(expires_in - 60, 1)
        return token

    def _request_json(self, request: Request, *, operation: str) -> object:
        try:
            response = self._requester(request, self._timeout_seconds)
        except HTTPError as exc:
            raise _map_http_error(exc, operation=operation) from None
        except (URLError, TimeoutError, OSError):
            raise _unavailable("Spotify is temporarily unavailable.") from None

        try:
            if not 200 <= response.status < 300:
                raise CardMakerError(
                    "spotify_unavailable", "Spotify returned an unexpected response."
                )
            body = response.read()
        finally:
            response.close()

        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _unavailable("Spotify returned an invalid response.") from None


def _map_item(
    kind: SpotifyKind,
    raw_item: object,
    *,
    expected_reference: SpotifyReference | None = None,
) -> CatalogItem:
    if not isinstance(raw_item, dict):
        raise _unavailable("Spotify returned invalid catalog metadata.")

    if expected_reference is None:
        spotify_id = raw_item.get("id")
        if not isinstance(spotify_id, str):
            raise _unavailable("Spotify returned invalid catalog metadata.")
        try:
            reference = SpotifyReference(kind, spotify_id)
        except ValueError:
            raise _unavailable("Spotify returned invalid catalog metadata.") from None
    else:
        reference = expected_reference

    name = raw_item.get("name")
    if not isinstance(name, str) or not name:
        raise _unavailable("Spotify returned invalid catalog metadata.")

    if kind == "playlist":
        primary_label = name
        secondary_label = None
        images = raw_item.get("images")
    else:
        artists = raw_item.get("artists")
        if not isinstance(artists, list):
            raise _unavailable("Spotify returned invalid catalog metadata.")
        artist_names: list[str] = []
        for artist in artists:
            if not isinstance(artist, dict):
                continue
            artist_name = artist.get("name")
            if isinstance(artist_name, str):
                artist_names.append(artist_name)
        if not artist_names:
            raise _unavailable("Spotify returned invalid catalog metadata.")
        primary_label = ", ".join(artist_names)
        secondary_label = name
        if kind == "track":
            album = raw_item.get("album")
            images = album.get("images") if isinstance(album, dict) else None
        else:
            images = raw_item.get("images")

    external_urls = raw_item.get("external_urls")
    supplied_external_url = (
        external_urls.get("spotify") if isinstance(external_urls, dict) else None
    )
    external_url = (
        supplied_external_url
        if isinstance(supplied_external_url, str) and supplied_external_url
        else reference.external_url
    )
    return CatalogItem(
        reference=reference,
        primary_label=primary_label,
        secondary_label=secondary_label,
        artwork=_largest_artwork(images),
        external_url=external_url,
    )


def _largest_artwork(raw_images: object) -> ArtworkReference | None:
    if not isinstance(raw_images, list):
        return None
    candidates: list[ArtworkReference] = []
    for image in raw_images:
        if not isinstance(image, dict) or not isinstance(image.get("url"), str):
            continue
        width = image.get("width") if isinstance(image.get("width"), int) else None
        height = image.get("height") if isinstance(image.get("height"), int) else None
        candidates.append(ArtworkReference(url=image["url"], width=width, height=height))
    if not candidates:
        return None
    return max(candidates, key=lambda image: (image.width or 0) * (image.height or 0))


def _map_http_error(error: HTTPError, *, operation: str) -> CardMakerError:
    if error.code == 429:
        retry_after = _retry_after_seconds(error)
        message = "Spotify is rate limited. Try again later."
        if retry_after is not None:
            message = f"Spotify is rate limited. Try again in {retry_after} seconds."
        return CardMakerError("spotify_rate_limited", message, retry_after=retry_after)
    if operation == "token" or error.code == 401:
        return CardMakerError(
            "spotify_auth_failed", "Spotify rejected the Card Maker credentials."
        )
    if error.code == 403:
        return CardMakerError(
            "spotify_forbidden", "This Spotify item is unavailable to the configured app."
        )
    if error.code == 404:
        return CardMakerError("spotify_not_found", "Spotify could not find that item.")
    return _unavailable("Spotify is temporarily unavailable.")


def _retry_after_seconds(error: HTTPError) -> int | None:
    raw_value = error.headers.get("Retry-After") if error.headers is not None else None
    try:
        value = int(raw_value) if raw_value is not None else None
    except ValueError:
        return None
    return value if value is not None and value >= 0 else None


def _unavailable(message: str) -> CardMakerError:
    return CardMakerError("spotify_unavailable", message)


def _default_requester(request: Request, timeout: float) -> ResponseLike:
    return cast(ResponseLike, urlopen(request, timeout=timeout))
