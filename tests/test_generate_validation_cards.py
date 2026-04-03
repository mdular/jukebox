"""Tests for validation control-card rendering."""

from __future__ import annotations

import importlib
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

validation_cards = importlib.import_module("generate_validation_cards")

SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


class ValidationCardLayoutTests(unittest.TestCase):
    def test_render_card_svg_uses_half_size_qr_in_original_qr_column(self) -> None:
        svg = validation_cards.render_card_svg(
            label="Stop",
            payload="jukebox:playback:stop",
        )

        root = ET.fromstring(svg)
        rects = root.findall("./svg:rect", SVG_NS)
        qr_rect = rects[1]
        qr_area_size = validation_cards.CANVAS_HEIGHT - (2 * validation_cards.PADDING)
        expected_qr_size = qr_area_size * validation_cards.QR_SCALE
        expected_origin = validation_cards.PADDING + ((qr_area_size - expected_qr_size) / 2)
        right_x = validation_cards.PADDING + qr_area_size + validation_cards.PADDING
        right_width = validation_cards.CANVAS_WIDTH - right_x - validation_cards.PADDING

        self.assertEqual(root.attrib["width"], str(validation_cards.CANVAS_WIDTH))
        self.assertEqual(root.attrib["height"], str(validation_cards.CANVAS_HEIGHT))
        self.assertAlmostEqual(float(qr_rect.attrib["x"]), expected_origin)
        self.assertAlmostEqual(float(qr_rect.attrib["y"]), expected_origin)
        self.assertAlmostEqual(float(qr_rect.attrib["width"]), expected_qr_size)
        self.assertAlmostEqual(float(qr_rect.attrib["height"]), expected_qr_size)

        text = root.find("./svg:text", SVG_NS)
        self.assertIsNotNone(text)
        assert text is not None
        self.assertAlmostEqual(float(text.attrib["x"]), right_x + (right_width / 2))

        module_rects = root.findall("./svg:g/svg:rect", SVG_NS)
        self.assertGreater(len(module_rects), 0)
        for rect in module_rects:
            rect_x = float(rect.attrib["x"])
            rect_y = float(rect.attrib["y"])
            rect_width = float(rect.attrib["width"])
            rect_height = float(rect.attrib["height"])
            self.assertGreaterEqual(rect_x, expected_origin)
            self.assertGreaterEqual(rect_y, expected_origin)
            self.assertLessEqual(rect_x + rect_width, expected_origin + expected_qr_size + 0.001)
            self.assertLessEqual(rect_y + rect_height, expected_origin + expected_qr_size + 0.001)
