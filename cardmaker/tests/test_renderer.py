from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

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
    image = PillowCardRenderer().render(
        make_draft(kind="playlist", secondary_label=None),
        Image.new("1", (676, 676), 255),
    )

    assert image.getbbox() is not None
    assert image.crop((756, 570, 1200, 650)).getbbox() is None


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
