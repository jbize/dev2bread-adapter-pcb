"""Emit minimal SVG for board outline + drill holes (no copper yet)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from adapter_gen.geometry import (
    HOLE_R,
    BoardParams,
    all_pad_centers_mil,
    board_outline_svg_path_d,
    bounds_mil,
)


# SVG presentation attributes must use hyphens (stroke-width), not
# stroke_width.
def _sub(parent: ET.Element, tag: str, attrs: dict[str, str]) -> ET.Element:
    return ET.SubElement(parent, tag, attrs)


def emit_board_svg(p: BoardParams, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    min_x, min_y, max_x, max_y = bounds_mil(p)
    w = max_x - min_x
    h = max_y - min_y

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{w:.1f}",
            "height": f"{h:.1f}",
            "viewBox": f"{min_x:.1f} {min_y:.1f} {w:.1f} {h:.1f}",
        },
    )
    title = f"Adapter {p.n_pins}-pin outline + holes (mil, +Y down)"
    t_el = ET.SubElement(svg, "title")
    t_el.text = title

    # Light background so outline contrast is obvious in any viewer
    _sub(
        svg,
        "rect",
        {
            "x": f"{min_x:.1f}",
            "y": f"{min_y:.1f}",
            "width": f"{w:.1f}",
            "height": f"{h:.1f}",
            "fill": "#f4f4f2",
        },
    )

    # Filled board + thin stroke so 50 mil fillets read as rounded.
    g_outline = _sub(
        svg,
        "g",
        {
            "id": "outline",
            "fill": "#e4e2dc",
            "stroke": "#1a472a",
            "stroke-width": "12",
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        },
    )
    g_holes = _sub(
        svg,
        "g",
        {"id": "holes", "fill": "#1a3a5c", "stroke": "none"},
    )

    d = board_outline_svg_path_d(p)
    _sub(g_outline, "path", {"d": d})

    for x, y, _net in all_pad_centers_mil(p):
        _sub(
            g_holes,
            "circle",
            {
                "cx": f"{x:.2f}",
                "cy": f"{y:.2f}",
                "r": f"{HOLE_R:.2f}",
            },
        )

    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    path.write_text(ET.tostring(svg, encoding="unicode"), encoding="utf-8")
