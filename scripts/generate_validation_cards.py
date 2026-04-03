#!/usr/bin/env python3
"""Generate printable validation card PNGs using the card dimensions from generate.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
from xml.sax.saxutils import escape

from generate_validation_qrs import PAYLOADS, build_qr_modules

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 756
PADDING = 40
QR_SCALE = 0.5
QR_BORDER_MODULES = 4
CARD_BACKGROUND = "#FFFFFF"
TEXT_COLOR = "#000000"
SYMBOL_VIEWBOX_SIZE = 200
SYMBOL_STROKE_WIDTH = 16

LABELS = {
    "control-smoke-track": "Smoke Track",
    "control-fallback-album": "Fallback Album",
    "control-fallback-playlist": "Fallback Playlist",
    "control-playback-stop": "Stop",
    "control-playback-next": "Next",
    "control-mode-replace": "Mode Replace",
    "control-mode-queue": "Mode Queue",
    "control-volume-low": "Volume Low",
    "control-volume-medium": "Volume Medium",
    "control-volume-high": "Volume High",
    "control-setup-wifi-reset": "Wi-Fi Reset",
    "control-setup-receiver-reauth": "Receiver Re-Auth",
    "control-system-shutdown": "Shutdown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate printable PNGs for the EPIC-4 validation control cards."
    )
    parser.add_argument(
        "--output-dir",
        default="docs/control cards",
        help="Directory for the generated card PNGs. Defaults to docs/control cards.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sips = shutil.which("sips")
    qlmanage = shutil.which("qlmanage")
    if sips is None and qlmanage is None:
        raise SystemExit(
            "Error: neither sips nor qlmanage is available to rasterize the printable cards to PNG."
        )

    for stem, payload in PAYLOADS:
        label = LABELS.get(stem, stem.replace("-", " ").title())
        png_path = output_dir / f"{stem}.png"
        render_card_png(
            sips=Path(sips) if sips is not None else None,
            qlmanage=Path(qlmanage) if qlmanage is not None else None,
            output_path=png_path,
            label=label,
            payload=payload,
            symbol=stem,
        )


def render_card_png(
    *,
    sips: Path | None,
    qlmanage: Path | None,
    output_path: Path,
    label: str,
    payload: str,
    symbol: str,
) -> None:
    svg = render_card_svg(label=label, payload=payload, symbol=symbol)
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_svg = temp_dir / f"{output_path.stem}.svg"
        temp_svg.write_text(svg, encoding="utf-8")
        if sips is not None:
            try:
                subprocess.run(
                    [str(sips), "-s", "format", "png", str(temp_svg), "--out", str(output_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return
            except subprocess.CalledProcessError:
                if qlmanage is None:
                    raise

        if qlmanage is None:
            raise RuntimeError("No working PNG rasterizer is available for validation cards.")

        try:
            subprocess.run(
                [str(qlmanage), "-t", "-s", str(CANVAS_WIDTH), "-o", str(temp_dir), str(temp_svg)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Quick Look rasterization failed. See docs/control cards/README.md for the "
                "recommended regeneration workflow."
            ) from exc
        quicklook_output = temp_dir / f"{temp_svg.name}.png"
        if not quicklook_output.is_file():
            raise FileNotFoundError(f"Quick Look did not produce the expected PNG: {quicklook_output}")
        quicklook_output.replace(output_path)


def render_card_svg(*, label: str, payload: str, symbol: str | None = None) -> str:
    modules = build_qr_modules(payload)
    qr_module_count = len(modules)
    qr_area_size = CANVAS_HEIGHT - (2 * PADDING)
    qr_size = qr_area_size * QR_SCALE
    qr_origin_x = PADDING + ((qr_area_size - qr_size) / 2)
    qr_origin_y = PADDING + ((qr_area_size - qr_size) / 2)
    module_size = qr_size / qr_module_count

    right_x = PADDING + qr_area_size + PADDING
    right_y = PADDING
    right_width = CANVAS_WIDTH - right_x - PADDING
    right_height = qr_area_size
    symbol_center_x = right_x + (right_width / 2)
    symbol_center_y = right_y + (right_height / 2)
    symbol_scale = (min(right_width, right_height) * 0.62) / SYMBOL_VIEWBOX_SIZE

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" '
            f'height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">'
        ),
        f"  <title>{escape(label)}</title>",
        f'  <rect width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="{CARD_BACKGROUND}"/>',
        f'  <rect x="{qr_origin_x}" y="{qr_origin_y}" width="{qr_size}" height="{qr_size}" fill="#FFFFFF"/>',
        '  <g id="qr-modules" fill="#000000">',
    ]

    for y, row in enumerate(modules):
        for x, value in enumerate(row):
            if not value:
                continue
            rect_x = qr_origin_x + x * module_size
            rect_y = qr_origin_y + y * module_size
            lines.append(
                f'    <rect x="{rect_x:.3f}" y="{rect_y:.3f}" width="{module_size:.3f}" height="{module_size:.3f}"/>'
            )

    lines.extend(
        [
            "  </g>",
            *render_symbol_svg(
                symbol=symbol or label,
                center_x=symbol_center_x,
                center_y=symbol_center_y,
                scale=symbol_scale,
            ),
        ]
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_symbol_svg(*, symbol: str, center_x: float, center_y: float, scale: float) -> list[str]:
    renderers = {
        "control-smoke-track": render_music_note_symbol,
        "control-fallback-album": render_album_symbol,
        "control-fallback-playlist": render_playlist_symbol,
        "control-playback-stop": render_stop_symbol,
        "control-playback-next": render_next_symbol,
        "control-mode-replace": render_replace_mode_symbol,
        "control-mode-queue": render_queue_mode_symbol,
        "control-volume-low": lambda: render_volume_symbol(waves=1),
        "control-volume-medium": lambda: render_volume_symbol(waves=2),
        "control-volume-high": lambda: render_volume_symbol(waves=3),
        "control-setup-wifi-reset": render_wifi_reset_symbol,
        "control-setup-receiver-reauth": render_receiver_reauth_symbol,
        "control-system-shutdown": render_shutdown_symbol,
    }
    elements = renderers.get(symbol, render_unknown_symbol)()
    return [
        (
            f'  <g id="card-symbol" data-symbol="{escape(symbol)}" '
            f'transform="translate({center_x:.1f} {center_y:.1f}) scale({scale:.3f})" '
            f'stroke="{TEXT_COLOR}" fill="none" stroke-width="{SYMBOL_STROKE_WIDTH}" '
            'stroke-linecap="round" stroke-linejoin="round">'
        ),
        *[f"    {element}" for element in elements],
        "  </g>",
    ]


def render_music_note_symbol() -> list[str]:
    return [
        '<ellipse cx="-34" cy="58" rx="24" ry="22" fill="#000000" stroke="none"/>',
        '<ellipse cx="34" cy="34" rx="24" ry="22" fill="#000000" stroke="none"/>',
        '<rect x="-8" y="-82" width="16" height="122" fill="#000000" stroke="none"/>',
        '<rect x="60" y="-104" width="16" height="114" fill="#000000" stroke="none"/>',
        '<polygon points="8,-102 76,-122 76,-56 8,-36" fill="#000000" stroke="none"/>',
    ]


def render_album_symbol() -> list[str]:
    return [
        '<circle cx="0" cy="0" r="82"/>',
        '<circle cx="0" cy="0" r="48"/>',
        '<circle cx="0" cy="0" r="12" fill="#000000" stroke="none"/>',
    ]


def render_playlist_symbol() -> list[str]:
    return [
        '<line x1="-80" y1="-46" x2="22" y2="-46"/>',
        '<line x1="-80" y1="0" x2="22" y2="0"/>',
        '<line x1="-80" y1="46" x2="22" y2="46"/>',
        '<polygon points="34,-38 88,0 34,38" fill="#000000" stroke="none"/>',
    ]


def render_stop_symbol() -> list[str]:
    return [
        '<rect x="-56" y="-56" width="112" height="112" rx="12" fill="#000000" stroke="none"/>',
    ]


def render_next_symbol() -> list[str]:
    return [
        '<polygon points="-84,-62 -28,0 -84,62" fill="#000000" stroke="none"/>',
        '<polygon points="-28,-62 28,0 -28,62" fill="#000000" stroke="none"/>',
        '<rect x="48" y="-74" width="20" height="148" rx="10" fill="#000000" stroke="none"/>',
    ]


def render_replace_mode_symbol() -> list[str]:
    return [
        '<line x1="-82" y1="-46" x2="14" y2="-46"/>',
        '<line x1="-82" y1="0" x2="14" y2="0"/>',
        '<line x1="-82" y1="46" x2="14" y2="46"/>',
        '<line x1="38" y1="-24" x2="82" y2="24"/>',
        '<line x1="82" y1="-24" x2="38" y2="24"/>',
    ]


def render_queue_mode_symbol() -> list[str]:
    return [
        '<line x1="-82" y1="-46" x2="14" y2="-46"/>',
        '<line x1="-82" y1="0" x2="14" y2="0"/>',
        '<line x1="-82" y1="46" x2="14" y2="46"/>',
        '<line x1="60" y1="-28" x2="60" y2="28"/>',
        '<line x1="32" y1="0" x2="88" y2="0"/>',
    ]


def render_volume_symbol(*, waves: int) -> list[str]:
    elements = [
        '<polygon points="-84,-28 -48,-28 -14,-60 -14,60 -48,28 -84,28" fill="#000000" stroke="none"/>',
    ]
    wave_paths = [
        '<path d="M 18 -18 Q 40 0 18 18"/>',
        '<path d="M 34 -38 Q 72 0 34 38"/>',
        '<path d="M 50 -58 Q 104 0 50 58"/>',
    ]
    elements.extend(wave_paths[:waves])
    return elements


def render_wifi_reset_symbol() -> list[str]:
    return [
        '<path d="M -78 10 Q 0 -64 78 10"/>',
        '<path d="M -52 26 Q 0 -22 52 26"/>',
        '<path d="M -26 44 Q 0 18 26 44"/>',
        '<circle cx="0" cy="64" r="8" fill="#000000" stroke="none"/>',
        '<path d="M 16 -78 A 92 92 0 1 0 82 20"/>',
        '<polyline points="60,14 82,20 76,-2"/>',
    ]


def render_receiver_reauth_symbol() -> list[str]:
    return [
        '<rect x="-84" y="-54" width="88" height="108" rx="16"/>',
        '<line x1="-62" y1="70" x2="-18" y2="70"/>',
        '<circle cx="52" cy="-8" r="22"/>',
        '<path d="M 30 -8 H -10 V 18 H 8 V 4 H 24"/>',
    ]


def render_shutdown_symbol() -> list[str]:
    return [
        '<path d="M 0 -88 V -18"/>',
        '<path d="M 48 -66 A 74 74 0 1 1 -48 -66"/>',
    ]


def render_unknown_symbol() -> list[str]:
    return [
        '<circle cx="0" cy="0" r="82"/>',
        '<line x1="-34" y1="0" x2="34" y2="0"/>',
    ]


if __name__ == "__main__":
    main()
