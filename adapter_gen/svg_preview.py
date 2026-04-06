"""Emit minimal SVG for board outline + drill holes (optional silk overlay).

The row-reverser sketch is not tied to a specific pin count: it uses ``p.num_cols`` and the
innermost row-A pad line (bottom of the top socket stack) for whatever ``BoardParams`` you pass.

Preview **trace** visibility: ``preview_traces`` selects Top vs Bottom sketch strokes (cyan vs red
in the row-reverser group, and top-row / neck cyan sketches are Top-only).
"""

from __future__ import annotations

import sys
from typing import Literal
import xml.etree.ElementTree as ET
from pathlib import Path

from adapter_gen.board_profile import BoardBranding
from adapter_gen.geometry import (
    HOLE_R,
    BoardParams,
    all_pad_centers_mil,
    board_outline_svg_path_d,
    bounds_mil,
)
from adapter_gen.row_reverser_emit import append_row_reverser_svg
from adapter_gen.neck_cyan_waypoints import append_neck_cyan_waypoints_svg
from adapter_gen.wide_head_stub_stem_join_preview import (
    append_wide_head_stub_stem_join_svg,
)
from adapter_gen.top_row_cyan_waypoints import append_top_row_cyan_waypoints_svg
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
    branding: BoardBranding | None = None,
    row_reverser: bool = False,
    silk_gpio_paths_json: str | None = None,
    top_row_cyan_waypoints: bool = True,
    neck_cyan_waypoints: bool = True,
    preview_traces: Literal["both", "top", "bottom"] = "both",
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
    if branding is not None:
        title_bits.append("branding")
    show_top_cyan = top_row_cyan_waypoints and preview_traces != "bottom"
    show_neck_cyan = neck_cyan_waypoints and preview_traces != "bottom"
    if row_reverser:
        title_bits.append("row-A inner reverser sketch")
    if show_top_cyan:
        title_bits.append("cyan top-row waypoints")
    if show_neck_cyan:
        title_bits.append("cyan neck waypoints")
    if preview_traces == "top":
        title_bits.append("preview traces top only")
    elif preview_traces == "bottom":
        title_bits.append("preview traces bottom only")
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

    if row_reverser:
        append_row_reverser_svg(
            svg,
            p,
            _sub,
            preview_traces=preview_traces,
        )

    if silk_mode and silk_mode != "none":
        sd = (silk_dir or _DEFAULT_SILK_DIR).resolve()
        try:
            paths_map, j1, j3, board_lines = load_silk_label_data(
                sd,
                silk_mode,
                p,
                silk_gpio_paths_json=silk_gpio_paths_json,
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

    if branding is not None:
        from adapter_gen._venv_bootstrap import ensure_matplotlib

        ensure_matplotlib()
        from adapter_gen.branding import build_branding_svg_overlay

        overlay = build_branding_svg_overlay(p, branding)
        if overlay is not None:
            text_paths_mil, images = overlay
            g_brand = _sub(svg, "g", {"id": "branding"})
            g_bimg = _sub(g_brand, "g", {"id": "branding-image"})
            for left_m, top_m, w_m, h_m, data_uri in images:
                _sub(
                    g_bimg,
                    "image",
                    {
                        "x": f"{left_m:.2f}",
                        "y": f"{top_m:.2f}",
                        "width": f"{w_m:.2f}",
                        "height": f"{h_m:.2f}",
                        "href": data_uri,
                    },
                )
            g_btxt = _sub(
                g_brand,
                "g",
                {
                    "id": "branding-text",
                    "fill": "none",
                    "stroke": "#2a2a28",
                    "stroke-width": "6",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
            for d_txt in text_paths_mil:
                _sub(g_btxt, "path", {"d": d_txt})

    # Stub-end → stem top (under top-row / neck cyan markers).
    if row_reverser:
        append_wide_head_stub_stem_join_svg(
            svg,
            p,
            _sub,
            preview_traces=preview_traces,
        )

    # After silk/branding so temp labels and cyan markers are not covered by stroke overlays.
    if show_top_cyan:
        append_top_row_cyan_waypoints_svg(svg, p, _sub)
    if show_neck_cyan:
        append_neck_cyan_waypoints_svg(svg, p, _sub)

    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    path.write_text(ET.tostring(svg, encoding="unicode"), encoding="utf-8")
