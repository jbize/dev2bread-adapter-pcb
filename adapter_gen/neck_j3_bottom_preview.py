"""Preview-only: red straddle markers + bent neck routing to J3 pins for ``--bottom-only``.

Also: vertical **wide-head J3 row** column polylines, and straight **stem-side J3 pad → right
straddle waypoint** joins (bottom-copper preview) when ``preview_traces`` is ``bottom`` or
``both`` — one segment per net, not a bus across columns.

Traces use ``neck_stem_right_net_trace_polyline_mil`` (same bend as left ``neck_cyan``).
Stroke #cc3333 matches row-reverser red (reference only).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import (
    BoardParams,
    head_column_x_mil,
    stem_layout_mil,
    stem_pin_y_mil,
    wide_head_y_rows_mil,
)
from adapter_gen.preview_waypoint_style import (
    LABEL_DY_MIL,
    LABEL_FONT_SIZE_MIL,
    MARKER_RADIUS_MIL,
    MARKER_STROKE_MIL,
    TRACE_WIDTH_MIL,
)
from adapter_gen.row_reverser_geometry import polyline_points_attr
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_right_net_trace_polyline_mil,
    neck_stem_top_straddle_waypoints_right_mil,
)

_STROKE = "#cc3333"
_WP_DOT_FILL = "#fce8e8"
_LBL_FILL = "#5c1a1a"


def wide_head_j3_row_column_vertical_trace_points_mil(
    p: BoardParams,
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Per column: polyline along J3 / row-B stack at ``head_column_x_mil``, same net."""
    ys = wide_head_y_rows_mil(p=p, from_row_a=False)
    if len(ys) < 2:
        return []
    out: list[tuple[int, list[tuple[float, float]]]] = []
    for col in range(p.num_cols):
        x = head_column_x_mil(col, p)
        pts = [(x, y) for y in ys]
        out.append((col, pts))
    return out


def append_wide_head_j3_row_column_traces_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Red vertical column stacks in the wide-head J3 row (bottom-copper preview only)."""
    traces = wide_head_j3_row_column_vertical_trace_points_mil(p)
    if not traces:
        return
    nc = p.num_cols
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    g = _sub(
        svg,
        "g",
        {
            "id": "red-wide-head-j3-row-column-traces",
            "aria-label": (
                "Wide head J3 row column stacks (bottom preview); preview only, not copper"
            ),
        },
    )
    g_tr = _sub(
        g,
        "g",
        {
            "id": "red-wide-head-j3-row-column-traces-inner",
            "fill": "none",
            "stroke": _STROKE,
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "aria-label": "J3 row vertical traces per column (stem-side toward gap)",
        },
    )
    for col, pts in traces:
        net_j3 = nc + col + 1
        _sub(
            g_tr,
            "polyline",
            {
                "points": polyline_points_attr(pts),
                "data-col": str(col),
                "data-net-j3-row": str(net_j3),
            },
        )


def _right_stem_straddle_or_pin_target_mil(
    p: BoardParams, seq: int
) -> tuple[float, float] | None:
    """Target for J3 head→stem join: straddle waypoint if present, else right stem pin center.

    ``seq`` is stem net id ``num_cols+1 … 2*num_cols``. No straddle waypoint for
    ``num_cols+1`` (mirrors pin 1 on the left); use ``(x_rn, stem_pin_y_mil(0))``.
    """
    nc = p.num_cols
    if seq < nc + 1 or seq > 2 * nc:
        return None
    wpts = neck_stem_top_straddle_waypoints_right_mil(p)
    by_seq = {s: (x, y) for x, y, s in wpts}
    if seq in by_seq:
        return by_seq[seq]
    col = seq - nc - 1
    _, _, x_rn, _ = stem_layout_mil(p)
    return (x_rn, stem_pin_y_mil(col, p))


def append_j3_head_to_right_stem_waypoint_join_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Straight segments: stem-side J3 pad per column → matching right straddle waypoint (or pin)."""
    ys_b = wide_head_y_rows_mil(p=p, from_row_a=False)
    if not ys_b:
        return
    y_head = ys_b[0]
    nc = p.num_cols
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    g = _sub(
        svg,
        "g",
        {
            "id": "red-j3-head-to-right-stem-straddle-join",
            "fill": "none",
            "stroke": _STROKE,
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "aria-label": (
                "J3 head stem-side pad to right straddle waypoint; preview only, not copper"
            ),
        },
    )
    for col in range(nc):
        seq = nc + col + 1
        end = _right_stem_straddle_or_pin_target_mil(p, seq)
        if end is None:
            continue
        x0 = head_column_x_mil(col, p)
        _sub(
            g,
            "polyline",
            {
                "points": polyline_points_attr([(x0, y_head), end]),
                "data-net": str(seq),
                "data-col": str(col),
            },
        )


def append_neck_j3_stem_right_red_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Emit ``red-stem-j3-neck-ref-bottom-only`` — bent straddle → right pin (same as left neck)."""
    wpts = neck_stem_top_straddle_waypoints_right_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "red-stem-j3-neck-ref-bottom-only",
            "aria-label": (
                "Bottom preview: J3 straddle ref + bent routing to pins; not copper"
            ),
        },
    )
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    g_tr = _sub(
        g,
        "g",
        {
            "id": "red-stem-j3-straddle-to-right-pin-traces-bottom-only",
            "fill": "none",
            "stroke": _STROKE,
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "aria-label": (
                "Bent straddle→right pin (same algorithm as neck J1); bottom preview"
            ),
        },
    )
    for _x, _y, seq in wpts:
        pts = neck_stem_right_net_trace_polyline_mil(p, seq)
        if pts is None:
            continue
        _sub(
            g_tr,
            "polyline",
            {
                "points": polyline_points_attr(pts),
                "data-neck-seq": str(seq),
                "data-right-stem-net": str(seq),
            },
        )
    r = f"{MARKER_RADIUS_MIL:.2f}"
    sw = f"{MARKER_STROKE_MIL:.2f}"
    lbl_fs = f"{LABEL_FONT_SIZE_MIL:.1f}"
    lbl_dy = f"{LABEL_DY_MIL:.2f}"
    for x_m, y_m, seq in wpts:
        g_w = _sub(
            g,
            "g",
            {
                "id": f"red-stem-j3-wp-{seq}",
                "transform": f"translate({x_m:.2f},{y_m:.2f})",
                "aria-label": f"J3 straddle ref pin {seq} (bottom preview)",
                "data-seq": str(seq),
                "data-x-mil": f"{x_m:.2f}",
                "data-y-mil": f"{y_m:.2f}",
                "data-temp-preview-label": "true",
            },
        )
        _sub(
            g_w,
            "circle",
            {
                "r": r,
                "fill": _WP_DOT_FILL,
                "stroke": _STROKE,
                "stroke-width": sw,
            },
        )
        _sub(
            g_w,
            "text",
            {
                "x": "0",
                "y": lbl_dy,
                "text-anchor": "middle",
                "fill": _LBL_FILL,
                "font-size": lbl_fs,
                "font-weight": "600",
                "font-family": "ui-monospace, Consolas, monospace",
                "class": "red-stem-j3-bottom-preview-label",
            },
        ).text = str(seq)
