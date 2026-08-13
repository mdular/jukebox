from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from cardmaker.adapters.qr_segno import SegnoQrEncoder
from cardmaker.adapters.qr_zxing import ZxingQrVerifier
from cardmaker.adapters.render_pillow import CardGeometry, PillowCardRenderer
from cardmaker.errors import CardMakerError
from cardmaker.models import ArtworkReference, CatalogItem, SpotifyKind, SpotifyReference
from cardmaker.service import MAX_SEARCH_QUERY_LENGTH, CardMakerService, safe_filename

ID = "2takcwOaAZWiXQijPHIx7B"
URI = f"spotify:track:{ID}"


def test_search_rejects_empty_and_oversized_queries_without_catalog_calls() -> None:
    catalog = FixtureCatalog(make_item())
    service = make_service(catalog=catalog)

    for query in ("", "   ", "x" * (MAX_SEARCH_QUERY_LENGTH + 1)):
        with pytest.raises(CardMakerError) as raised:
            service.search(query)
        assert raised.value.code == "invalid_query"

    assert catalog.search_queries == []


def test_search_trims_and_delegates_one_explicit_query() -> None:
    item = make_item()
    catalog = FixtureCatalog(item)

    assert make_service(catalog=catalog).search("  Kinderlieder  ") == (item,)
    assert catalog.search_queries == ["Kinderlieder"]


def test_resolve_normalizes_share_url_before_catalog_lookup() -> None:
    catalog = FixtureCatalog(make_item())
    service = make_service(catalog=catalog)

    item = service.resolve(f"https://open.spotify.com/track/{ID}?si=tracking")

    assert item.reference.uri == URI
    assert catalog.resolved == [SpotifyReference("track", ID)]


def test_render_re_resolves_and_returns_only_verified_png_bytes() -> None:
    item = make_item()
    catalog = FixtureCatalog(item)
    service = make_service(catalog=catalog)

    rendered = service.render(f"https://open.spotify.com/track/{ID}?si=tracking")

    assert catalog.resolved == [item.reference]
    assert rendered.normalized_uri == URI
    assert rendered.filename == "Lichterkinder - Körperteil Blues.png"
    assert (rendered.width, rendered.height) == (1200, 756)
    with Image.open(BytesIO(rendered.png_bytes)) as image:
        assert image.mode == "RGB"
        assert image.size == (1200, 756)
        assert image.info["dpi"] == pytest.approx((72.009, 72.009), abs=0.001)
        assert ZxingQrVerifier().decode(image.convert("RGB")) == URI
        assert set(image.info) == {"dpi"}


@pytest.mark.parametrize(
    ("kind", "secondary_label", "expected_marker_bounds"),
    [
        ("track", "Körperteil Blues", (0, 10, 51, 26)),
        ("album", "Körperteil Blues", (0, 0, 38, 36)),
        ("playlist", None, (0, 4, 48, 36)),
    ],
)
def test_render_verifies_png_and_marker_for_every_supported_type_without_files(
    kind: SpotifyKind,
    secondary_label: str | None,
    expected_marker_bounds: tuple[int, int, int, int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = make_item(kind=kind, secondary_label=secondary_label)
    service = make_service(catalog=FixtureCatalog(item))
    monkeypatch.chdir(tmp_path)

    rendered = service.render(item.reference.uri)

    assert rendered.normalized_uri == item.reference.uri
    assert (rendered.width, rendered.height) == (1200, 756)
    with Image.open(BytesIO(rendered.png_bytes)) as image:
        geometry = CardGeometry()
        assert image.mode == "RGB"
        assert image.size == (1200, 756)
        assert ZxingQrVerifier().decode(image.convert("RGB")) == item.reference.uri
        assert image.crop(
            (
                geometry.marker_x,
                geometry.marker_y,
                geometry.marker_x + geometry.marker_max_width,
                geometry.marker_y + geometry.marker_height,
            )
        ).getbbox() == expected_marker_bounds
    assert tuple(tmp_path.iterdir()) == ()


def test_render_blocks_items_without_spotify_artwork() -> None:
    item = make_item(artwork=None)
    fetcher = FixtureArtworkFetcher()
    service = make_service(catalog=FixtureCatalog(item), artwork_fetcher=fetcher)

    with pytest.raises(CardMakerError) as raised:
        service.render(URI)

    assert raised.value.code == "artwork_unavailable"
    assert fetcher.references == []


def test_render_blocks_a_mismatched_independent_decode() -> None:
    service = make_service(verifier=WrongValueVerifier())

    with pytest.raises(CardMakerError) as raised:
        service.render(URI)

    assert raised.value.code == "qr_verification_failed"


@pytest.mark.parametrize(
    ("primary", "secondary", "expected"),
    [
        ("Artist/name", "Title: bad?", "Artist-name - Title- bad-.png"),
        ("  Artist  ", "Title. ", "Artist - Title.png"),
        ("..", None, "card.png"),
        ("A\x00B\nC", None, "A-B-C.png"),
    ],
)
def test_suggested_filename_is_filesystem_safe(
    primary: str, secondary: str | None, expected: str
) -> None:
    assert safe_filename(primary, secondary) == expected


class FixtureCatalog:
    def __init__(self, item: CatalogItem) -> None:
        self.item = item
        self.search_queries: list[str] = []
        self.resolved: list[SpotifyReference] = []

    def search(self, query: str) -> tuple[CatalogItem, ...]:
        self.search_queries.append(query)
        return (self.item,)

    def resolve(self, reference: SpotifyReference) -> CatalogItem:
        self.resolved.append(reference)
        return CatalogItem(
            reference=reference,
            primary_label=self.item.primary_label,
            secondary_label=self.item.secondary_label,
            artwork=self.item.artwork,
            external_url=reference.external_url,
        )


class FixtureArtworkFetcher:
    def __init__(self) -> None:
        self.references: list[ArtworkReference] = []

    def fetch(self, reference: ArtworkReference) -> Image.Image:
        self.references.append(reference)
        return Image.new("RGB", (640, 640), (30, 80, 160))


class WrongValueVerifier:
    def decode(self, image: Image.Image) -> str:
        return "spotify:track:6rqhFgbbKwnb9MLmUQDhG6"


def make_item(
    *,
    kind: SpotifyKind = "track",
    secondary_label: str | None = "Körperteil Blues",
    artwork: ArtworkReference | None = ArtworkReference("https://i.scdn.co/a"),
) -> CatalogItem:
    reference = SpotifyReference(kind, ID)
    return CatalogItem(
        reference=reference,
        primary_label="Lichterkinder",
        secondary_label=secondary_label,
        artwork=artwork,
        external_url=reference.external_url,
    )


def make_service(
    *,
    catalog: FixtureCatalog | None = None,
    artwork_fetcher: FixtureArtworkFetcher | None = None,
    verifier: ZxingQrVerifier | WrongValueVerifier | None = None,
) -> CardMakerService:
    return CardMakerService(
        catalog=catalog or FixtureCatalog(make_item()),
        artwork_fetcher=artwork_fetcher or FixtureArtworkFetcher(),
        qr_encoder=SegnoQrEncoder(),
        qr_verifier=verifier or ZxingQrVerifier(),
        renderer=PillowCardRenderer(),
    )
