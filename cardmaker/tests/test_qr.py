from __future__ import annotations

import pytest
from PIL import Image

from cardmaker.adapters.qr_segno import QUIET_ZONE_MODULES, SegnoQrEncoder
from cardmaker.adapters.qr_zxing import ZxingQrVerifier
from cardmaker.errors import CardMakerError

URI = "spotify:track:2takcwOaAZWiXQijPHIx7B"


def test_qr_encoder_returns_final_panel_with_integer_aligned_modules() -> None:
    image = SegnoQrEncoder().encode(URI)

    assert image.mode == "1"
    assert image.size == (676, 676)
    assert QUIET_ZONE_MODULES == 2
    assert set(image.get_flattened_data()) == {0, 255}
    transitions = _transitions_on_first_symbol_row(image)
    assert transitions
    assert all((right - left) % 16 == 0 for left, right in transitions)


def test_qr_round_trip_uses_an_independent_decoder() -> None:
    image = SegnoQrEncoder().encode(URI).convert("RGB")

    assert ZxingQrVerifier().decode(image) == URI


@pytest.mark.parametrize(
    "value",
    [
        "https://open.spotify.com/track/2takcwOaAZWiXQijPHIx7B",
        "spotify:artist:2takcwOaAZWiXQijPHIx7B",
        "spotify:track:too-short",
    ],
)
def test_qr_encoder_only_accepts_normalized_supported_uris(value: str) -> None:
    with pytest.raises(ValueError):
        SegnoQrEncoder().encode(value)


def test_qr_verifier_rejects_missing_or_extra_codes() -> None:
    verifier = ZxingQrVerifier()

    with pytest.raises(CardMakerError, match="exactly one"):
        verifier.decode(Image.new("RGB", (1200, 756), "white"))

    two_codes = Image.new("RGB", (1352, 676), "white")
    code = SegnoQrEncoder().encode(URI).convert("RGB")
    two_codes.paste(code, (0, 0))
    two_codes.paste(code, (676, 0))
    with pytest.raises(CardMakerError, match="exactly one"):
        verifier.decode(two_codes)


def _transitions_on_first_symbol_row(image: Image.Image) -> list[tuple[int, int]]:
    for y in range(image.height):
        row = [image.getpixel((x, y)) == 0 for x in range(image.width)]
        if not any(row):
            continue
        points = [x for x in range(1, image.width) if row[x] != row[x - 1]]
        return list(zip(points, points[1:]))
    return []
