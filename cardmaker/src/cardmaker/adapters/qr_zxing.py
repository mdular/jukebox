"""Independent QR verification using the zxing-cpp binding."""

from __future__ import annotations

from typing import cast

import zxingcpp  # type: ignore[import-not-found]
from PIL import Image

from cardmaker.errors import CardMakerError


class ZxingQrVerifier:
    """Decode exactly one QR from a composed card image."""

    def decode(self, image: Image.Image) -> str:
        results = zxingcpp.read_barcodes(
            image,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True,
            try_downscale=True,
        )
        if len(results) != 1:
            raise CardMakerError(
                "qr_verification_failed",
                "The composed card must contain exactly one readable QR code.",
            )
        result = results[0]
        if not result.valid or not result.text:
            raise CardMakerError(
                "qr_verification_failed", "The composed card QR code could not be decoded."
            )
        return cast(str, result.text)
