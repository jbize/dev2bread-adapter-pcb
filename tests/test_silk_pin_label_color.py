"""``[silk].pin_label_color`` validation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from adapter_gen.board_profile import load_board_profile


def test_pin_label_color_valid_uppercases() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "b.toml"
        p.write_text(
            "\n".join(
                [
                    "schema = 1",
                    'id = "x"',
                    "device_min_pins = 44",
                    "adapter_pins = 44",
                    "[silk]",
                    'pin_label_color = "#aabbcc"',
                ]
            ),
            encoding="utf-8",
        )
        prof = load_board_profile(p)
        assert prof.silk is not None
        assert prof.silk.pin_label_color == "#AABBCC"


def test_pin_label_color_invalid() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "b.toml"
        p.write_text(
            "\n".join(
                [
                    "schema = 1",
                    'id = "x"',
                    "device_min_pins = 44",
                    "adapter_pins = 44",
                    "[silk]",
                    'pin_label_color = "white"',
                ]
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="pin_label_color"):
            load_board_profile(p)


def test_deprecated_preview_silk_pin_label_color_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "b.toml"
        p.write_text(
            "\n".join(
                [
                    "schema = 1",
                    'id = "x"',
                    "device_min_pins = 44",
                    "adapter_pins = 44",
                    "[preview]",
                    'board_color = "default"',
                    'silk_pin_label_color = "#FFFFFF"',
                ]
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="\\[silk\\].pin_label_color"):
            load_board_profile(p)
