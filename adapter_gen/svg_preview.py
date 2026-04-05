"""Emit minimal SVG for board outline + drill holes (optional silk overlay)."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from adapter_gen.geometry import (
    HOLE_R,
    BoardParams,
    all_pad_centers_mil,
    board_outline_svg_path_d,
    bounds_mil,
)
from adapter_gen.silk_preview import (
    board_id_path_elements_mil,
    load_silk_label_data,
    silk_path_elements_mil,
)

# Baked silk JSON (``scripts/bake_devkitc_gpio_silk_paths.py``).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SILK_DIR = _REPO_ROOT / "out" / "intermediate" / "silk"


# SVG presentation attributes must use hyphens (stroke-width), not
# stroke_width.
def _sub(parent: ET.Element, tag: str, attrs: dict[str, str]) -> ET.Element:
    return ET.SubElement(parent, tag, attrs)


def emit_board_svg(
    p: BoardParams,
    path: Path,
    *,
    silk_mode: str | None = None,
    silk_dir: Path | None = None,
) -> None:
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
    title_bits = [f"Adapter {p.n_pins}-pin outline + holes"]
    if silk_mode and silk_mode != "none":
        title_bits.append(f"silk={silk_mode}")
    title_bits.append("(mil, +Y down)")
    t_el = ET.SubElement(svg, "title")
    t_el.text = " ".join(title_bits)

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

    if silk_mode and silk_mode != "none":
        sd = (silk_dir or _DEFAULT_SILK_DIR).resolve()
        try:
            paths_map, j1, j3, board_lines = load_silk_label_data(
                sd, silk_mode, p
            )
            ds = silk_path_elements_mil(
                p,
                paths_map,
                j1,
                j3,
                vertical_head=(silk_mode == "devkitc1"),
            )
            if board_lines:
                ds.extend(board_id_path_elements_mil(p, board_lines))
        except FileNotFoundError as e:
            print(
                f"Warning: silk data missing ({e}) — run "
                "scripts/bake_devkitc_gpio_silk_paths.py. Skipping silk.",
                file=sys.stderr,
            )
        except (KeyError, ValueError, TypeError) as e:
            print(
                f"Warning: silk overlay failed ({e}). Skipping silk.",
                file=sys.stderr,
            )
        else:
            g_silk = _sub(
                svg,
                "g",
                {
                    "id": "silk",
                    "fill": "none",
                    "stroke": "#2a2a28",
                    "stroke-width": "6",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
            for d_silk in ds:
                _sub(g_silk, "path", {"d": d_silk})

    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    path.write_text(ET.tostring(svg, encoding="unicode"), encoding="utf-8")
