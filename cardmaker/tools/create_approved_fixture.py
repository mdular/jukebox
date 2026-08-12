#!/usr/bin/env python3
"""Create the synthetic artwork and initial approved renderer fixture once."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from cardmaker.adapters.qr_segno import SegnoQrEncoder
from cardmaker.adapters.render_pillow import PillowCardRenderer
from cardmaker.models import CardDraft, CatalogItem, SpotifyReference

URI = "spotify:track:2takcwOaAZWiXQijPHIx7B"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path(__file__).parents[1] / "tests" / "fixtures",
    )
    args = parser.parse_args()
    artwork_path = args.fixture_root / "artwork" / "fixture-cover.png"
    approved_path = args.fixture_root / "approved-card.png"
    if approved_path.exists():
        raise SystemExit(f"Refusing to overwrite approved fixture: {approved_path}")
    approved_path.parent.mkdir(parents=True, exist_ok=True)

    if artwork_path.exists():
        with Image.open(artwork_path) as source:
            artwork = source.convert("RGB")
    else:
        artwork_path.parent.mkdir(parents=True, exist_ok=True)
        artwork = _fixture_artwork()
        artwork.save(artwork_path, format="PNG")

    reference = SpotifyReference("track", URI.rsplit(":", 1)[1])
    draft = CardDraft(
        item=CatalogItem(
            reference=reference,
            primary_label="Lichterkinder",
            secondary_label="Körperteil Blues",
            artwork=None,
            external_url=reference.external_url,
        ),
        artwork=artwork,
    )
    card = PillowCardRenderer().render(draft, SegnoQrEncoder().encode(URI))
    card.save(approved_path, format="PNG")
    print(artwork_path)
    print(approved_path)
    return 0


def _fixture_artwork() -> Image.Image:
    image = Image.new("RGB", (640, 720), "#17365d")
    draw = ImageDraw.Draw(image)
    for y in range(image.height):
        green = 54 + ((y * 110) // image.height)
        blue = 93 + ((y * 130) // image.height)
        draw.line((0, y, image.width, y), fill=(23, green, blue))
    draw.ellipse((80, 80, 280, 280), fill="#ffd166")
    draw.ellipse((245, 205, 570, 530), fill="#ef476f")
    draw.rounded_rectangle((90, 510, 550, 650), radius=28, fill="#06d6a0")
    return image


if __name__ == "__main__":
    raise SystemExit(main())
