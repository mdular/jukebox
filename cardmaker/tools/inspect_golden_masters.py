#!/usr/bin/env python3
"""Report pixel geometry and QR metadata from the checked-in card masters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import zxingcpp  # type: ignore[import-not-found]
from PIL import Image

CONTENT_X = 756
QR_PANEL_REGION = (40, 40, 716, 716)


def inspect_master(path: Path) -> dict[str, object]:
    """Return stable, JSON-safe measurements for one master PNG."""

    with Image.open(path) as source:
        image = source.convert("RGB")
        metadata = {key: _json_safe(value) for key, value in source.info.items()}

    decoded = zxingcpp.read_barcodes(
        image,
        formats=zxingcpp.BarcodeFormat.QRCode,
        try_rotate=True,
        try_downscale=True,
    )
    if len(decoded) != 1 or not decoded[0].valid:
        raise ValueError(f"Expected exactly one readable QR in {path}")

    artwork_bounds, text_bounds = _content_bounds(image)

    return {
        "filename": path.name,
        "mode": image.mode,
        "size": list(image.size),
        "png_metadata": metadata,
        "non_black_bounds": _visible_bounds(image, (0, 0, image.width, image.height)),
        "qr_panel_bounds": _visible_bounds(image, (0, 0, CONTENT_X, image.height)),
        "qr_dark_bounds": _dark_bounds(image, QR_PANEL_REGION),
        "visible_artwork_bounds": artwork_bounds,
        "text_bounds": text_bounds,
        "decoded_qr": decoded[0].text,
        "qr_error_correction": decoded[0].ec_level,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Master PNGs. Defaults to every PNG under ../docs/cards.",
    )
    args = parser.parse_args()
    default_root = Path(__file__).resolve().parents[2] / "docs" / "cards"
    paths = args.paths or sorted(default_root.glob("*.png"))
    reports = [inspect_master(path) for path in paths]
    print(json.dumps(reports, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _visible_bounds(
    image: Image.Image, region: tuple[int, int, int, int]
) -> list[int] | None:
    left, top, right, bottom = region
    bounds = image.crop(region).getbbox()
    if bounds is None:
        return None
    return [
        left + bounds[0],
        top + bounds[1],
        left + bounds[2] - 1,
        top + bounds[3] - 1,
    ]


def _dark_bounds(
    image: Image.Image, region: tuple[int, int, int, int]
) -> list[int] | None:
    grayscale = image.crop(region).convert("L")
    dark_mask = grayscale.point(lambda value: 255 if value < 16 else 0)
    bounds = dark_mask.getbbox()
    if bounds is None:
        return None
    return [
        region[0] + bounds[0],
        region[1] + bounds[1],
        region[0] + bounds[2] - 1,
        region[1] + bounds[3] - 1,
    ]


def _content_bounds(image: Image.Image) -> tuple[list[int] | None, list[int] | None]:
    """Separate visible artwork and text at the largest blank row gap."""

    rows_with_content = [
        y
        for y in range(image.height)
        if image.crop((CONTENT_X, y, image.width, y + 1)).getbbox() is not None
    ]
    runs: list[tuple[int, int]] = []
    for y in rows_with_content:
        if not runs or y > runs[-1][1] + 1:
            runs.append((y, y))
        else:
            runs[-1] = (runs[-1][0], y)
    if len(runs) < 2:
        return _visible_bounds(image, (CONTENT_X, 0, image.width, image.height)), None

    split_index = max(
        range(len(runs) - 1),
        key=lambda index: runs[index + 1][0] - runs[index][1],
    )
    text_start = runs[split_index + 1][0]
    return (
        _visible_bounds(image, (CONTENT_X, 0, image.width, text_start)),
        _visible_bounds(image, (CONTENT_X, text_start, image.width, image.height)),
    )


def _json_safe(value: Any) -> object:
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


if __name__ == "__main__":
    raise SystemExit(main())
