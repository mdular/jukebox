from __future__ import annotations

from pathlib import Path

from PIL import Image

from cardmaker.adapters.render_pillow import CardGeometry

GOLDENS = Path(__file__).parents[2] / "docs" / "cards"


def test_all_golden_masters_share_locked_canvas_panel_and_column_anchors() -> None:
    geometry = CardGeometry()
    paths = sorted(GOLDENS.glob("*.png"))

    assert len(paths) == 4
    for path in paths:
        with Image.open(path) as image:
            assert image.mode == "RGB"
            assert image.size == (geometry.canvas_width, geometry.canvas_height)
            # macOS reports a 72-DPI default, but the checked-in bytes have no pHYs chunk.
            assert image.info.get("dpi") is None
            assert _nonblack_bounds(image)[:2] == (40, 40)
            assert image.getpixel((geometry.qr_x, geometry.qr_y)) != (0, 0, 0)
            assert image.getpixel((geometry.content_x - 1, geometry.qr_y)) == (0, 0, 0)
            assert any(
                image.getpixel((geometry.content_x, y)) != (0, 0, 0)
                for y in range(geometry.canvas_height)
            )


def test_recovered_baseline_geometry_is_frozen() -> None:
    geometry = CardGeometry()

    assert geometry.canvas_width == 1200
    assert geometry.canvas_height == 756
    assert geometry.margin == 40
    assert geometry.qr_panel_size == 676
    assert (geometry.qr_x, geometry.qr_y) == (40, 40)
    assert geometry.content_x == 756
    assert geometry.content_width == 404
    assert geometry.artwork_y == 40
    assert geometry.artwork_height == 453
    assert geometry.text_top_gap == 20
    assert geometry.text_line_gap == 65
    assert geometry.primary_font_size == 48
    assert geometry.secondary_font_size == 42
    assert geometry.minimum_font_size == 20


def test_cm1_marker_geometry_is_frozen_at_the_bottom_left_anchor() -> None:
    geometry = CardGeometry()

    assert (geometry.marker_x, geometry.marker_y) == (756, 680)
    assert geometry.marker_x == geometry.content_x
    assert geometry.marker_y + geometry.marker_height == (
        geometry.canvas_height - geometry.margin
    )
    assert geometry.marker_height == 36
    assert geometry.marker_max_width == 56
    assert geometry.marker_render_scale == 4
    assert geometry.album_marker_size == 36
    assert geometry.album_outline_width == 3
    assert geometry.album_reflection_inset == 7
    assert geometry.album_hub_size == 10
    assert geometry.album_hole_size == 4
    assert geometry.playlist_y_offset == 7
    assert geometry.playlist_row_gap == 12
    assert geometry.playlist_dot_size == 5
    assert geometry.playlist_dash_x_offset == 11
    assert geometry.playlist_dash_widths == (30, 34, 26)
    assert geometry.playlist_dash_height == 4
    assert geometry.track_dot_x_offset == 1
    assert geometry.track_y_offset == 13
    assert geometry.track_dot_size == 10
    assert geometry.track_dash_x_offset == 17
    assert geometry.track_dash_y_offset == 15
    assert geometry.track_dash_width == 31
    assert geometry.track_dash_height == 5


def _nonblack_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    points = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y)) != (0, 0, 0)
    ]
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points),
        max(y for _, y in points),
    )
