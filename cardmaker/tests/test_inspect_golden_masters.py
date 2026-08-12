from __future__ import annotations

from pathlib import Path

from tools.inspect_golden_masters import inspect_master


def test_inspector_reports_geometry_metadata_and_independent_qr_decode() -> None:
    path = Path(__file__).parents[2] / "docs" / "cards" / "laternenlauf_card.png"

    report = inspect_master(path)

    assert report["filename"] == "laternenlauf_card.png"
    assert report["mode"] == "RGB"
    assert report["size"] == [1200, 756]
    assert report["non_black_bounds"] == [40, 40, 1159, 715]
    assert report["qr_panel_bounds"] == [40, 40, 715, 715]
    assert report["visible_artwork_bounds"] == [756, 40, 1159, 454]
    assert report["text_bounds"] == [760, 494, 1132, 534]
    assert report["png_metadata"] == {}
    assert report["decoded_qr"] == "spotify:track:2F9VY2gYvXz47Xbh9Ranea"
    assert report["qr_error_correction"] == "H"
