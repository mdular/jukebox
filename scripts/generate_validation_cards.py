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
        default="spec/control cards",
        help="Directory for the generated card PNGs. Defaults to spec/control cards.",
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
        )


def render_card_png(
    *,
    sips: Path | None,
    qlmanage: Path | None,
    output_path: Path,
    label: str,
    payload: str,
) -> None:
    svg = render_card_svg(label=label, payload=payload)
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

        subprocess.run(
            [str(qlmanage), "-t", "-s", str(CANVAS_WIDTH), "-o", str(temp_dir), str(temp_svg)],
            check=True,
            capture_output=True,
            text=True,
        )
        quicklook_output = temp_dir / f"{temp_svg.name}.png"
        if not quicklook_output.is_file():
            raise FileNotFoundError(f"Quick Look did not produce the expected PNG: {quicklook_output}")
        quicklook_output.replace(output_path)


def render_card_svg(*, label: str, payload: str) -> str:
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

    label_lines = wrap_label(label)
    line_height = 72
    label_block_height = line_height * len(label_lines)
    label_start_y = right_y + (right_height / 2) - (label_block_height / 2) + 10

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" '
            f'height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">'
        ),
        f"  <title>{escape(label)}</title>",
        f'  <rect width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="{CARD_BACKGROUND}"/>',
        f'  <rect x="{qr_origin_x}" y="{qr_origin_y}" width="{qr_size}" height="{qr_size}" fill="#FFFFFF"/>',
        '  <g fill="#000000">',
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
            (
                f'  <text x="{right_x + (right_width / 2):.1f}" y="{label_start_y:.1f}" '
                f'font-family="Arial, Helvetica, sans-serif" font-size="60" font-weight="700" '
                f'fill="{TEXT_COLOR}" text-anchor="middle">'
            ),
        ]
    )
    for index, line in enumerate(label_lines):
        dy = 0 if index == 0 else line_height
        lines.append(f'    <tspan x="{right_x + (right_width / 2):.1f}" dy="{dy}">{escape(line)}</tspan>')
    lines.extend(["  </text>", "</svg>"])
    return "\n".join(lines) + "\n"


def wrap_label(label: str) -> list[str]:
    words = label.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) <= 13 or not current:
            current.append(word)
            continue
        lines.append(" ".join(current))
        current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


if __name__ == "__main__":
    main()
