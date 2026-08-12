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
