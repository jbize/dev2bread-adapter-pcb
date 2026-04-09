"""Emit minimal SVG for board outline + drill holes (optional silk overlay).

The row-reverser sketch is not tied to a specific pin count: it uses ``p.num_cols`` and the
innermost row-A pad line (bottom of the top socket stack) for whatever ``BoardParams`` you pass.

Preview **trace** colors match EasyEDA: **TopLayer = red**, **BottomLayer = blue**.
``preview_traces`` selects Top vs Bottom in the row-reverser group.

**Routing sketches** (row reverser, stub→stem, row-A columns, neck straddle→pins, wide-head J3,
J3→straddle) follow the generator geometry and draw by default. **Cyan waypoint dots and temporary
index labels** are developer-only; pass ``routing_waypoint_overlays=True`` (CLI:
``--routing-waypoints``) to add them — default off so previews stay clean for sharing.

**Board tint** — ``board_color`` / ``--board-color`` selects neutral gray (default) vs green
soldermask-style fill for branding/silk color checks (preview only).

**Silk stroke** — ``pin_label_color`` from ``[silk]`` (or default gray) sets vector GPIO /
numeric / kit-ID / J1·J3 ref stroke — same hex is emitted in EasyEDA ``TEXT`` by the generator.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from adapter_gen.board_profile import BoardBranding
from adapter_gen.branding import BRANDING_PREVIEW_STROKE_MIL
from adapter_gen.geometry import (
    HOLE_R,
    BoardParams,
    all_pad_centers_mil,
    board_outline_svg_path_d,
    bounds_mil,
)
from adapter_gen.neck_cyan_waypoints import append_neck_cyan_waypoints_svg
from adapter_gen.neck_j3_bottom_preview import (
    append_j3_head_to_right_stem_waypoint_join_svg,
    append_neck_j3_stem_right_red_waypoints_svg,
    append_wide_head_j3_row_column_traces_svg,
)
from adapter_gen.preview_board_style import (
    BoardColorMode,
    preview_board_palette,
    silk_pin_label_stroke_svg,
)
from adapter_gen.row_reverser_emit import append_row_reverser_svg
from adapter_gen.silk_preview import (
    board_id_path_elements_mil,
    load_silk_label_data,
    numeric_connector_ref_path_elements_mil,
    paths_map_with_connector_ref_glyphs,
    silk_path_elements_mil,
)
from adapter_gen.top_row_cyan_waypoints import append_top_row_cyan_waypoints_svg
from adapter_gen.wide_head_stub_stem_join_preview import (
    append_wide_head_stub_stem_join_svg,
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
    routing_waypoint_overlays: bool = False,
    preview_traces: Literal["both", "top", "bottom"] = "both",
    board_color: BoardColorMode = "default",
    silk_pin_label_color: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    palette = preview_board_palette(board_color)
    silk_stroke = silk_pin_label_stroke_svg(silk_pin_label_color)
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
    if board_color != "default":
        title_bits.append(f"board_color={board_color}")
    if silk_mode and silk_mode != "none":
        title_bits.append(f"silk={silk_mode}")
    if branding is not None:
        title_bits.append("branding")
    if row_reverser:
        title_bits.append("row-A inner reverser sketch")
    show_bottom_routing = preview_traces != "top"
    show_top_layer_routing = preview_traces != "bottom"
    if routing_waypoint_overlays and show_top_layer_routing:
        title_bits.append("TopLayer waypoint dots (row A + neck straddle)")
    if preview_traces == "top":
        title_bits.append("preview traces top only")
    elif preview_traces == "bottom":
        title_bits.append("preview traces bottom only")
    if routing_waypoint_overlays and show_bottom_routing:
        title_bits.append("J3 straddle waypoint dots (BottomLayer)")
    if show_bottom_routing:
        title_bits.append("blue J3 head row column traces (BottomLayer)")
        title_bits.append("blue J3 head to stem straddle joins (BottomLayer)")
    title_bits.append("(mil, +Y down)")
    t_el = ET.SubElement(svg, "title")
    t_el.text = " ".join(title_bits)

    _sub(
        svg,
        "rect",
        {
            "x": f"{min_x:.1f}",
            "y": f"{min_y:.1f}",
            "width": f"{w:.1f}",
            "height": f"{h:.1f}",
            "fill": palette.canvas_fill,
        },
    )

    # Filled board + thin stroke so 50 mil fillets read as rounded.
    g_outline = _sub(
        svg,
        "g",
        {
            "id": "outline",
            "fill": palette.board_fill,
            "stroke": palette.board_stroke,
            "stroke-width": "12",
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        },
    )
    g_holes = _sub(
        svg,
        "g",
        {"id": "holes", "fill": palette.hole_fill, "stroke": "none"},
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

    numeric_cref_ds: list[str] = []
    if silk_mode and silk_mode != "none":
        sd = (silk_dir or _DEFAULT_SILK_DIR).resolve()
        try:
            paths_map, j1, j3, board_lines = load_silk_label_data(
                sd,
                silk_mode,
                p,
                silk_gpio_paths_json=silk_gpio_paths_json,
            )
            paths_map = paths_map_with_connector_ref_glyphs(paths_map, sd)
            ds = silk_path_elements_mil(
                p,
                paths_map,
                j1,
                j3,
                vertical_head=(silk_mode == "devkitc1"),
            )
            if silk_mode in ("numeric", "devkitc1"):
                numeric_cref_ds = numeric_connector_ref_path_elements_mil(p, paths_map)
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
                    "stroke": silk_stroke,
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
                    "stroke": branding.preview_silk_color,
                    "stroke-width": f"{BRANDING_PREVIEW_STROKE_MIL:.1f}",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
            for d_txt in text_paths_mil:
                _sub(g_btxt, "path", {"d": d_txt})

    # Stub-end → stem top (under top-row / neck TopLayer markers).
    if row_reverser:
        append_wide_head_stub_stem_join_svg(
            svg,
            p,
            _sub,
            preview_traces=preview_traces,
        )

    # Stem / neck routing sketches (same geometry as EasyEDA); waypoint dots optional (see title).
    if show_top_layer_routing:
        append_top_row_cyan_waypoints_svg(
            svg,
            p,
            _sub,
            waypoint_markers=routing_waypoint_overlays,
        )
    if show_bottom_routing:
        append_neck_j3_stem_right_red_waypoints_svg(
            svg,
            p,
            _sub,
            waypoint_markers=routing_waypoint_overlays,
        )
        append_wide_head_j3_row_column_traces_svg(svg, p, _sub)
        append_j3_head_to_right_stem_waypoint_join_svg(svg, p, _sub)
    if show_top_layer_routing:
        append_neck_cyan_waypoints_svg(
            svg,
            p,
            _sub,
            waypoint_markers=routing_waypoint_overlays,
        )

    # J1/J3 connector refs (numeric or devkitc GPIO silk) on top of routing sketches.
    if numeric_cref_ds:
        g_cref = _sub(
            svg,
            "g",
            {
                "id": "silk-connector-refs",
                "fill": "none",
                "stroke": silk_stroke,
                "stroke-width": "6",
                "stroke-linejoin": "round",
                "stroke-linecap": "round",
            },
        )
        for d_cref in numeric_cref_ds:
            _sub(g_cref, "path", {"d": d_cref})

    tree = ET.ElementTree(svg)
    ET.indent(tree, space="  ")
    path.write_text(ET.tostring(svg, encoding="unicode"), encoding="utf-8")
