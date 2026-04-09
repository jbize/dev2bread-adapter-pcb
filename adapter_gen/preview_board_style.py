"""Preview-only SVG colors for the board face (not used by EasyEDA export).

``default`` — neutral gray-beige shading (historical preview look).

``green`` — dark soldermask + near-black canvas + copper-toned pad holes, tuned to match common
green-PCB fab renders (e.g. ~``#1B4D2E`` face).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BoardColorMode = Literal["default", "green"]

# SVG stroke for vector silk (GPIO / numeric labels, J1/J3 refs) when TOML omits
# ``[silk].pin_label_color`` (preview + EasyEDA).
SILK_PIN_LABEL_STROKE_SVG_DEFAULT = "#2a2a28"


@dataclass(frozen=True)
class BoardPreviewPalette:
    canvas_fill: str
    board_fill: str
    board_stroke: str
    hole_fill: str


def silk_pin_label_stroke_svg(silk_pin_label_color: str | None) -> str:
    """Stroke color for per-pin / connector-ref silk paths in ``svg_preview``."""
    return (
        silk_pin_label_color
        if silk_pin_label_color is not None
        else SILK_PIN_LABEL_STROKE_SVG_DEFAULT
    )


def preview_board_palette(mode: BoardColorMode) -> BoardPreviewPalette:
    if mode == "green":
        return BoardPreviewPalette(
            canvas_fill="#0d0d0d",
            board_fill="#1B4D2E",
            board_stroke="#0d2818",
            hole_fill="#C4956A",
        )
    return BoardPreviewPalette(
        canvas_fill="#f4f4f2",
        board_fill="#e4e2dc",
        board_stroke="#1a472a",
        hole_fill="#1a3a5c",
    )
