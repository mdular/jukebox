from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from cardmaker.adapters.qr_segno import SegnoQrEncoder
from cardmaker.adapters.render_pillow import CardGeometry, PillowCardRenderer, fit_text
from cardmaker.models import CardDraft, CatalogItem, SpotifyReference

URI = "spotify:track:2takcwOaAZWiXQijPHIx7B"


def test_renderer_produces_locked_rgb_canvas_and_geometry() -> None:
    geometry = CardGeometry()
    artwork = Image.new("RGB", (800, 400), (220, 40, 20))
    qr = Image.new("1", (geometry.qr_panel_size, geometry.qr_panel_size), 255)

    image = PillowCardRenderer().render(make_draft(artwork=artwork), qr)

    assert image.mode == "RGB"
    assert image.size == (1200, 756)
    assert image.getpixel((0, 0)) == (0, 0, 0)
    assert image.getpixel((40, 40)) == (255, 255, 255)
    assert image.getpixel((715, 715)) == (255, 255, 255)
    assert image.getpixel((716, 40)) == (0, 0, 0)
    assert image.getpixel((755, 40)) == (0, 0, 0)
    assert image.getpixel((756, 40)) == (220, 40, 20)


def test_spotify_artwork_is_contained_without_cropping_or_distortion() -> None:
    artwork = Image.new("RGB", (800, 400), (220, 40, 20))
    image = PillowCardRenderer().render(
        make_draft(artwork=artwork), Image.new("1", (676, 676), 255)
    )

    assert image.getpixel((756, 40)) == (220, 40, 20)
    assert image.getpixel((1159, 241)) == (220, 40, 20)
    assert image.getpixel((756, 242)) == (0, 0, 0)


def test_playlist_renders_no_invented_secondary_line() -> None:
    geometry = CardGeometry()
    image = PillowCardRenderer().render(
        make_draft(kind="playlist", secondary_label=None),
        Image.new("1", (676, 676), 255),
    )

    assert image.getbbox() is not None
    assert image.crop((756, 570, 1200, geometry.marker_y)).getbbox() is None


@pytest.mark.parametrize(
    ("kind", "secondary_label", "expected_bounds", "white_pixels", "black_pixels"),
    [
        (
            "album",
            "Körperteil Blues",
            (0, 0, 38, 36),
            ((18, 1), (1, 18), (18, 13), (23, 12)),
            ((18, 18),),
        ),
        (
            "playlist",
            None,
            (0, 4, 48, 36),
            ((2, 9), (2, 21), (2, 33), (20, 8), (20, 20), (20, 32)),
            ((7, 9), (7, 21), (7, 33)),
        ),
        (
            "track",
            "Körperteil Blues",
            (0, 10, 51, 26),
            ((2, 18), (6, 18), (18, 17), (45, 17)),
            ((13, 18), (50, 18), (55, 0)),
        ),
    ],
)
def test_renderer_draws_locked_marker_geometry_for_each_content_type(
    kind: str,
    secondary_label: str | None,
    expected_bounds: tuple[int, int, int, int],
    white_pixels: tuple[tuple[int, int], ...],
    black_pixels: tuple[tuple[int, int], ...],
) -> None:
    geometry = CardGeometry()
    renderer = PillowCardRenderer(geometry)
    qr = Image.new("1", (geometry.qr_panel_size, geometry.qr_panel_size), 255)
    draft = make_draft(kind=kind, secondary_label=secondary_label)

    first = renderer.render(draft, qr)
    second = renderer.render(draft, qr)
    marker_box = (
        geometry.marker_x,
        geometry.marker_y,
        geometry.marker_x + geometry.marker_max_width,
        geometry.marker_y + geometry.marker_height,
    )
    marker = first.crop(marker_box)

    assert marker.getbbox() == expected_bounds
    assert ImageChops.difference(marker, second.crop(marker_box)).getbbox() is None
    for point in white_pixels:
        assert _red_channel(marker, point) >= 200
    for point in black_pixels:
        assert _red_channel(marker, point) < 10


def test_album_marker_includes_a_tonal_reflection_wedge_and_center_hole() -> None:
    geometry = CardGeometry()
    image = PillowCardRenderer(geometry).render(
        make_draft(kind="album"),
        Image.new("1", (geometry.qr_panel_size, geometry.qr_panel_size), 255),
    )
    marker = image.crop(
        (
            geometry.marker_x,
            geometry.marker_y,
            geometry.marker_x + geometry.marker_max_width,
            geometry.marker_y + geometry.marker_height,
        )
    )

    assert 150 <= _red_channel(marker, (23, 12)) < 255
    assert marker.getpixel((18, 18)) == (0, 0, 0)


@pytest.mark.parametrize("kind", ["track", "album"])
def test_secondary_label_stays_above_marker(kind: str) -> None:
    geometry = CardGeometry()
    image = PillowCardRenderer(geometry).render(
        make_draft(kind=kind),
        Image.new("1", (geometry.qr_panel_size, geometry.qr_panel_size), 255),
    )

    assert image.crop((geometry.content_x, 578, 1200, geometry.marker_y)).getbbox()
    assert image.crop((geometry.content_x, 630, 1200, geometry.marker_y)).getbbox() is None
    assert image.crop(
        (
            geometry.marker_x,
            geometry.marker_y,
            geometry.marker_x + geometry.marker_max_width,
            geometry.marker_y + geometry.marker_height,
        )
    ).getbbox()


def test_renderer_rejects_an_unknown_content_type_invariant() -> None:
    draft = make_draft()
    object.__setattr__(draft.item.reference, "kind", "episode")

    with pytest.raises(ValueError, match="Unsupported content marker kind"):
        PillowCardRenderer().render(draft, Image.new("1", (676, 676), 255))


def test_packaged_fonts_load_without_host_fallback() -> None:
    font_root = files("cardmaker") / "assets" / "fonts"
    with as_file(font_root / "DejaVuSans.ttf") as regular_path:
        assert regular_path.is_file()
    with as_file(font_root / "DejaVuSans-Bold.ttf") as bold_path:
        assert bold_path.is_file()
    assert PillowCardRenderer().font_names == ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf")


def test_fit_text_shrinks_by_two_then_ellipsizes_deterministically() -> None:
    renderer = PillowCardRenderer()
    long_label = "A deliberately very long label " * 8

    first = fit_text(
        long_label,
        font_path=renderer.bold_font_path,
        max_width=404,
        initial_size=48,
        minimum_size=20,
    )
    second = fit_text(
        long_label,
        font_path=renderer.bold_font_path,
        max_width=404,
        initial_size=48,
        minimum_size=20,
    )

    assert first == second
    assert first.font_size == 20
    assert first.text.endswith("…")
    assert first.text != long_label
    assert first.measured_width <= 404


def test_deterministic_fixture_matches_approved_spike_render() -> None:
    fixture_root = Path(__file__).parent / "fixtures"
    with Image.open(fixture_root / "artwork" / "fixture-cover.png") as source:
        artwork = source.convert("RGB")
    draft = make_draft(artwork=artwork)

    rendered = PillowCardRenderer().render(draft, SegnoQrEncoder().encode(URI))

    with Image.open(fixture_root / "approved-card.png") as expected_source:
        expected = expected_source.convert("RGB")
    assert ImageChops.difference(rendered, expected).getbbox() is None


def make_draft(
    *,
    artwork: Image.Image | None = None,
    kind: str = "track",
    secondary_label: str | None = "Körperteil Blues",
) -> CardDraft:
    reference = SpotifyReference(kind, "2takcwOaAZWiXQijPHIx7B")  # type: ignore[arg-type]
    return CardDraft(
        item=CatalogItem(
            reference=reference,
            primary_label="Lichterkinder",
            secondary_label=secondary_label,
            artwork=None,
            external_url=reference.external_url,
        ),
        artwork=artwork or Image.new("RGB", (640, 640), (220, 40, 20)),
    )


def _red_channel(image: Image.Image, point: tuple[int, int]) -> int:
    pixel = image.getpixel(point)
    assert isinstance(pixel, tuple)
    return pixel[0]
