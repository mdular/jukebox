from __future__ import annotations

import logging
from io import BytesIO

import pytest
from flask.testing import FlaskClient
from PIL import Image

from cardmaker.app import create_app
from cardmaker.errors import CardMakerError
from cardmaker.models import ArtworkReference, CatalogItem, RenderedCard, SpotifyReference

ID = "2takcwOaAZWiXQijPHIx7B"
URI = f"spotify:track:{ID}"


@pytest.fixture
def service() -> StubService:
    return StubService()


@pytest.fixture
def client(service: StubService) -> FlaskClient:
    return create_app(service=service).test_client()


def test_index_serves_plain_authoring_shell_without_secrets(
    client: FlaskClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b"Search Spotify" in response.data
    assert b"Paste Spotify URL or URI" in response.data
    assert response.data.count(b">Download PNG<") == 1
    assert b"Make another" in response.data
    assert b'id="card-preview"' in response.data
    assert b'width="600"' in response.data
    assert b'height="378"' in response.data
    assert b"Encoded URI" in response.data
    assert b"Credits" in response.data
    assert b'id="preview-status"' in response.data
    assert b'role="status"' in response.data
    assert b"Spotify" in response.data
    assert b"may look soft" in response.data
    assert b"Create preview" not in response.data
    assert response.data.index(b'id="card-preview"') < response.data.index(b"Encoded URI")
    assert response.data.index(b"Encoded URI") < response.data.index(b">Download PNG<")
    assert b"CARDMAKER_SPOTIFY_CLIENT_SECRET" not in response.data
    assert b"/static/app.js" in response.data

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert b"isLowResolution" in script.data
    assert b"AbortController" in script.data
    assert b"X-Cardmaker-Spotify-URI" in script.data
    assert b"X-Cardmaker-Width" in script.data
    assert b"X-Cardmaker-Height" in script.data
    assert b"responseUri !== elements.selectedUri.textContent" in script.data
    assert b"URL.createObjectURL" in script.data
    assert b"URL.revokeObjectURL" in script.data
    assert script.data.count(b'fetch("/api/render"') == 1
    assert script.data.count(b"response.blob()") == 1
    assert script.data.count(b"downloadLink.click()") == 1
    assert b"previewObjectUrl" in script.data
    assert b"if (item.artwork) void renderPreview(item.uri)" in script.data
    assert b"createPreview" not in script.data

    stylesheet = client.get("/static/style.css")
    assert stylesheet.status_code == 200
    assert b".discovery-grid, .review-layout" in stylesheet.data
    assert b"repeat(auto-fit, minmax(min(100%, 320px), 1fr))" in stylesheet.data
    assert b".card-preview" in stylesheet.data
    assert b"width: 100%" in stylesheet.data
    assert b"max-width: 100%" in stylesheet.data
    assert b".review-metadata" in stylesheet.data


def test_health_is_local_and_never_calls_the_service(
    client: FlaskClient, service: StubService
) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert service.calls == []


def test_search_serializes_full_metadata_for_browser_grouping(
    client: FlaskClient, service: StubService
) -> None:
    response = client.get("/api/search", query_string={"q": "Kinderlieder"})

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert service.calls == [("search", "Kinderlieder")]
    assert response.get_json() == {
        "items": [
            {
                "kind": "track",
                "spotify_id": ID,
                "uri": URI,
                "external_url": f"https://open.spotify.com/track/{ID}",
                "primary_label": "Lichterkinder",
                "secondary_label": "Körperteil Blues",
                "artwork": {
                    "url": "https://i.scdn.co/artwork.jpg",
                    "width": 640,
                    "height": 640,
                },
            }
        ]
    }


def test_empty_search_is_a_successful_empty_state(
    client: FlaskClient, service: StubService
) -> None:
    service.search_items = ()

    response = client.get("/api/search", query_string={"q": "nothing"})

    assert response.status_code == 200
    assert response.get_json() == {"items": []}


def test_resolve_accepts_only_one_string_reference(
    client: FlaskClient, service: StubService
) -> None:
    response = client.post(
        "/api/resolve",
        json={"reference": f"https://open.spotify.com/track/{ID}"},
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["uri"] == URI
    assert service.calls == [("resolve", f"https://open.spotify.com/track/{ID}")]

    for payload in ({}, {"reference": 3}, {"reference": URI, "label": "browser label"}):
        rejected = client.post("/api/resolve", json=payload)
        assert rejected.status_code == 400
        assert rejected.get_json()["code"] == "invalid_request"


def test_render_accepts_only_uri_and_returns_attachment_verified_png(
    client: FlaskClient, service: StubService
) -> None:
    response = client.post("/api/render", json={"uri": URI})

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == service.rendered.png_bytes
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Cardmaker-Spotify-URI"] == URI
    assert response.headers["X-Cardmaker-Width"] == "1200"
    assert response.headers["X-Cardmaker-Height"] == "756"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "Lichterkinder" in response.headers["Content-Disposition"]
    assert service.calls == [("render", URI)]

    rejected = client.post(
        "/api/render",
        json={"uri": URI, "artwork_url": "https://attacker.example/file"},
    )
    assert rejected.status_code == 400
    assert service.calls == [("render", URI)]


def test_expected_errors_use_small_json_envelope_and_retry_after(
    client: FlaskClient, service: StubService
) -> None:
    service.failure = CardMakerError(
        "spotify_rate_limited", "Spotify is rate limited.", retry_after=17
    )

    response = client.get("/api/search", query_string={"q": "limited"})

    assert response.status_code == 429
    assert response.get_json() == {
        "code": "spotify_rate_limited",
        "message": "Spotify is rate limited.",
    }
    assert response.headers["Retry-After"] == "17"
    assert response.headers["Cache-Control"] == "no-store"


def test_unexpected_errors_do_not_leak_details_to_browser_or_logs(
    client: FlaskClient, service: StubService, caplog: pytest.LogCaptureFixture
) -> None:
    service.failure = RuntimeError("raw upstream body with client-secret")

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/search", query_string={"q": "broken"})

    assert response.status_code == 500
    assert response.get_json() == {
        "code": "internal_error",
        "message": "The Card Maker could not complete that request.",
    }
    assert b"client-secret" not in response.data
    assert "client-secret" not in str(response.headers)
    assert "client-secret" not in caplog.text
    assert "raw upstream body" not in caplog.text
    assert "exception_type=RuntimeError" in caplog.text


@pytest.mark.parametrize(
    ("method", "path", "expected_status"),
    [
        ("get", "/api/render", 405),
        ("get", "/api/missing", 404),
    ],
)
def test_flask_api_errors_also_use_the_json_envelope(
    client: FlaskClient, method: str, path: str, expected_status: int
) -> None:
    response = getattr(client, method)(path)

    assert response.status_code == expected_status
    assert response.get_json() == {
        "code": "invalid_request",
        "message": "That Card Maker API route or method is not available.",
    }
    assert response.headers["Cache-Control"] == "no-store"


class StubService:
    def __init__(self) -> None:
        self.item = make_item()
        self.search_items: tuple[CatalogItem, ...] = (self.item,)
        self.calls: list[tuple[str, str]] = []
        self.failure: Exception | None = None
        self.rendered = RenderedCard(
            png_bytes=make_png(),
            normalized_uri=URI,
            filename="Lichterkinder - Körperteil Blues.png",
            width=1200,
            height=756,
        )

    def search(self, query: str) -> tuple[CatalogItem, ...]:
        self.calls.append(("search", query))
        self._maybe_fail()
        return self.search_items

    def resolve(self, raw_reference: str) -> CatalogItem:
        self.calls.append(("resolve", raw_reference))
        self._maybe_fail()
        return self.item

    def render(self, raw_reference: str) -> RenderedCard:
        self.calls.append(("render", raw_reference))
        self._maybe_fail()
        return self.rendered

    def _maybe_fail(self) -> None:
        if self.failure is not None:
            raise self.failure


def make_item() -> CatalogItem:
    reference = SpotifyReference("track", ID)
    return CatalogItem(
        reference=reference,
        primary_label="Lichterkinder",
        secondary_label="Körperteil Blues",
        artwork=ArtworkReference("https://i.scdn.co/artwork.jpg", 640, 640),
        external_url=reference.external_url,
    )


def make_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (1200, 756), "black").save(output, format="PNG")
    return output.getvalue()
