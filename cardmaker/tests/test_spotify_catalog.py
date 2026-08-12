from __future__ import annotations

import json
from collections.abc import Iterable
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest

from cardmaker.adapters.spotify_catalog import ResponseLike, SpotifyCatalog
from cardmaker.errors import CardMakerError
from cardmaker.models import SpotifyReference

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"


def test_search_maps_spotify_labels_unicode_artwork_and_attribution() -> None:
    requester = SequenceRequester([token_response(), fixture_response("search.json")])
    catalog = make_catalog(requester)

    items = catalog.search("Kinderlieder")

    assert [(item.reference.kind, item.primary_label, item.secondary_label) for item in items] == [
        ("track", "Lichterkinder, Gästin", "Körperteil Blues"),
        ("album", "Willy Astor", "Kindischer Ozean"),
        ("playlist", "Laternenlauf", None),
    ]
    assert items[0].artwork is not None
    assert items[0].artwork.url == "https://i.scdn.co/large-track.jpg"
    assert items[0].external_url == items[0].reference.external_url


def test_search_uses_client_credentials_and_bounded_multi_type_query() -> None:
    requester = SequenceRequester([token_response(), fixture_response("search.json")])
    catalog = make_catalog(requester)

    catalog.search("Nina & Nino")

    token_request, search_request = requester.requests
    assert token_request.full_url == "https://accounts.spotify.com/api/token"
    assert token_request.get_method() == "POST"
    assert token_request.data == b"grant_type=client_credentials"
    assert token_request.get_header("Authorization", "").startswith("Basic ")
    query = parse_qs(urlsplit(search_request.full_url).query)
    assert query == {
        "q": ["Nina & Nino"],
        "type": ["track,album,playlist"],
        "market": ["DE"],
        "limit": ["5"],
    }
    assert search_request.get_header("Authorization") == "Bearer access-token"


def test_access_token_is_reused_then_refreshed_shortly_before_expiry() -> None:
    clock = MutableClock()
    requester = SequenceRequester(
        [
            token_response("token-1", expires_in=120),
            fixture_response("search.json"),
            fixture_response("search.json"),
            token_response("token-2", expires_in=120),
            fixture_response("search.json"),
        ]
    )
    catalog = make_catalog(requester, clock=clock)

    catalog.search("one")
    clock.value = 30
    catalog.search("two")
    clock.value = 61
    catalog.search("three")

    token_requests = [request for request in requester.requests if "api/token" in request.full_url]
    assert len(token_requests) == 2
    assert requester.requests[-1].get_header("Authorization") == "Bearer token-2"


@pytest.mark.parametrize("kind", ["track", "album", "playlist"])
def test_resolve_uses_the_corresponding_entity_endpoint(kind: str) -> None:
    payload = entity_payload(kind)
    requester = SequenceRequester([token_response(), JsonResponse(payload)])
    catalog = make_catalog(requester)
    reference = SpotifyReference(kind=kind, spotify_id="2takcwOaAZWiXQijPHIx7B")  # type: ignore[arg-type]

    item = catalog.resolve(reference)

    request = requester.requests[-1]
    assert urlsplit(request.full_url).path == f"/v1/{kind}s/{reference.spotify_id}"
    assert parse_qs(urlsplit(request.full_url).query) == {"market": ["DE"]}
    assert item.reference == reference


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (401, "spotify_auth_failed"),
        (403, "spotify_forbidden"),
        (404, "spotify_not_found"),
        (500, "spotify_unavailable"),
    ],
)
def test_resolve_maps_http_failures_without_leaking_upstream_body(
    status: int, expected_code: str
) -> None:
    requester = SequenceRequester(
        [token_response(), http_error(status, body=b"secret upstream body")]
    )
    catalog = make_catalog(requester)

    with pytest.raises(CardMakerError) as raised:
        catalog.resolve(SpotifyReference("track", "2takcwOaAZWiXQijPHIx7B"))

    assert raised.value.code == expected_code
    assert "secret upstream body" not in str(raised.value)


def test_rate_limit_preserves_retry_after_without_retrying() -> None:
    requester = SequenceRequester([token_response(), http_error(429, retry_after="23")])
    catalog = make_catalog(requester)

    with pytest.raises(CardMakerError) as raised:
        catalog.search("rate limited")

    assert raised.value.code == "spotify_rate_limited"
    assert raised.value.retry_after == 23
    assert len(requester.requests) == 2


@pytest.mark.parametrize(
    "failure",
    [
        URLError("DNS failed"),
        TimeoutError("timed out"),
    ],
)
def test_network_failures_map_to_unavailable(failure: Exception) -> None:
    requester = SequenceRequester([token_response(), failure])
    catalog = make_catalog(requester)

    with pytest.raises(CardMakerError) as raised:
        catalog.search("offline")

    assert raised.value.code == "spotify_unavailable"


def test_malformed_json_maps_to_unavailable() -> None:
    requester = SequenceRequester([token_response(), BytesResponse(b"not JSON")])
    catalog = make_catalog(requester)

    with pytest.raises(CardMakerError) as raised:
        catalog.search("malformed")

    assert raised.value.code == "spotify_unavailable"


def test_empty_search_is_an_empty_result_not_an_error() -> None:
    empty: dict[str, object] = {
        name: {"items": []} for name in ("tracks", "albums", "playlists")
    }
    catalog = make_catalog(SequenceRequester([token_response(), JsonResponse(empty)]))

    assert catalog.search("nothing") == ()


class JsonResponse:
    status = 200

    def __init__(self, payload: Any) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.closed = False

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        self.closed = True


class BytesResponse(JsonResponse):
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.closed = False


class SequenceRequester:
    def __init__(self, results: Iterable[ResponseLike | Exception]) -> None:
        self._results = iter(results)
        self.requests: list[Request] = []

    def __call__(self, request: Request, timeout: float) -> ResponseLike:
        assert timeout == 5.0
        self.requests.append(request)
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result


class MutableClock:
    value = 0.0

    def __call__(self) -> float:
        return self.value


def make_catalog(
    requester: SequenceRequester, *, clock: MutableClock | None = None
) -> SpotifyCatalog:
    return SpotifyCatalog(
        client_id="client-id",
        client_secret="client-secret",
        market="DE",
        requester=requester,
        clock=clock,
    )


def token_response(token: str = "access-token", *, expires_in: int = 3600) -> JsonResponse:
    return JsonResponse({"access_token": token, "expires_in": expires_in})


def fixture_response(name: str) -> JsonResponse:
    return JsonResponse(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def http_error(
    status: int, *, body: bytes = b"upstream error", retry_after: str | None = None
) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://api.spotify.com/v1/test", status, "error", headers, None)


def entity_payload(kind: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "2takcwOaAZWiXQijPHIx7B",
        "name": "Resolved name",
        "external_urls": {
            "spotify": f"https://open.spotify.com/{kind}/2takcwOaAZWiXQijPHIx7B"
        },
        "images": [{"url": "https://i.scdn.co/image.jpg", "width": 640, "height": 640}],
    }
    if kind == "playlist":
        return payload
    payload["artists"] = [{"name": "Resolved artist"}]
    if kind == "track":
        payload["album"] = {"images": payload.pop("images")}
    return payload
