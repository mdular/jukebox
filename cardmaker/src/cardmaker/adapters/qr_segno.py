"""Segno-backed integer-grid QR encoding."""

from __future__ import annotations

from typing import Final

import segno
from PIL import Image, ImageDraw

from cardmaker.references import SpotifyReferenceParser

PANEL_SIZE: Final[int] = 676
ERROR_CORRECTION: Final[str] = "H"
QUIET_ZONE_MODULES: Final[int] = 2


class SegnoQrEncoder:
    """Render a normalized Spotify URI into its final 676-pixel panel."""

    def encode(self, uri: str) -> Image.Image:
        reference = SpotifyReferenceParser().parse(uri)
        if reference.uri != uri:
            raise ValueError("QR encoding requires a canonical Spotify URI.")

        qr = segno.make(uri, error=ERROR_CORRECTION, micro=False, boost_error=False)
        matrix = tuple(tuple(bool(module) for module in row) for row in qr.matrix)
        symbol_modules = len(matrix)
        total_modules = symbol_modules + (2 * QUIET_ZONE_MODULES)
        module_scale = PANEL_SIZE // total_modules
        rendered_size = total_modules * module_scale
        offset = (PANEL_SIZE - rendered_size) // 2
        symbol_offset = offset + (QUIET_ZONE_MODULES * module_scale)

        image = Image.new("1", (PANEL_SIZE, PANEL_SIZE), 255)
        draw = ImageDraw.Draw(image)
        for y, row in enumerate(matrix):
            for x, is_dark in enumerate(row):
                if not is_dark:
                    continue
                left = symbol_offset + (x * module_scale)
                top = symbol_offset + (y * module_scale)
                draw.rectangle(
                    (left, top, left + module_scale - 1, top + module_scale - 1),
                    fill=0,
                )
        return image
