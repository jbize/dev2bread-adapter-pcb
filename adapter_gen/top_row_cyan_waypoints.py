"""Preview-only TopLayer (red) waypoints along the outermost wide row-A pad line (top row, +Y).

Order is **left → right** in mil space: position **1** is the **leftmost** column, **num_cols**
the **rightmost**. This matches ``head_column_x_mil`` (``col = num_cols - 1`` is smallest **X**).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import BoardParams, head_column_x_mil, wide_head_y_rows_mil
from adapter_gen.preview_waypoint_style import (
    LABEL_DY_MIL,
    LABEL_FONT_SIZE_MIL,
    MARKER_RADIUS_MIL,
    MARKER_STROKE_MIL,
    TOP_COPPER_PREVIEW_DOT_FILL,
    TOP_COPPER_PREVIEW_LABEL_FILL,
    TOP_COPPER_PREVIEW_STROKE,
    TRACE_WIDTH_MIL,
)
from adapter_gen.row_reverser_geometry import polyline_points_attr

_STROKE = TOP_COPPER_PREVIEW_STROKE
_WP_DOT_FILL = TOP_COPPER_PREVIEW_DOT_FILL


def top_row_a_waypoints_left_to_right_mil(
    p: BoardParams,
) -> tuple[float, list[tuple[float, float, int]]]:
    """``(y_row, [(x, y, seq_1based), ...])`` for the outermost row-A socket row only."""
    ys = wide_head_y_rows_mil(p=p, from_row_a=True)
    y0 = ys[0]
    nc = p.num_cols
    wpts: list[tuple[float, float, int]] = []
    for seq in range(1, nc + 1):
        col = nc - seq
        x = head_column_x_mil(col, p)
        wpts.append((x, y0, seq))
    return y0, wpts


def top_row_a_column_vertical_trace_points_mil(
    p: BoardParams,
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Per column: polyline points (outer row A → inner) at ``head_column_x_mil``, same net."""
    ys = wide_head_y_rows_mil(p=p, from_row_a=True)
    if len(ys) < 2:
        return []
    out: list[tuple[int, list[tuple[float, float]]]] = []
    for col in range(p.num_cols):
        x = head_column_x_mil(col, p)
        pts = [(x, y) for y in ys]
        out.append((col, pts))
    return out


def append_top_row_cyan_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
    *,
    waypoint_markers: bool = False,
) -> None:
    """Append ``<g id="cyan-top-row-waypoints">`` — row-A column traces; optional per-pad markers."""
    _, wpts = top_row_a_waypoints_left_to_right_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "cyan-top-row-waypoints",
            "aria-label": "Top row (row A) TopLayer sketch; preview only, not copper",
        },
    )
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    traces = top_row_a_column_vertical_trace_points_mil(p)
    if traces:
        g_tr = _sub(
            g,
            "g",
            {
                "id": "cyan-top-row-column-traces",
                "fill": "none",
                "stroke": _STROKE,
                "stroke-width": tw,
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
                "aria-label": "Row-A vertical traces from outer waypoint to inner pads",
            },
        )
        for col, pts in traces:
            net_a = col + 1
            _sub(
                g_tr,
                "polyline",
                {
                    "points": polyline_points_attr(pts),
                    "data-col": str(col),
                    "data-net-row-a": str(net_a),
                },
            )
    if not waypoint_markers:
        return
    r = f"{MARKER_RADIUS_MIL:.2f}"
    sw = f"{MARKER_STROKE_MIL:.2f}"
    lbl_fs = f"{LABEL_FONT_SIZE_MIL:.1f}"
    lbl_dy = f"{LABEL_DY_MIL:.2f}"
    for x_m, y_m, seq in wpts:
        g_w = _sub(
            g,
            "g",
            {
                "id": f"cyan-top-row-wp-{seq}",
                "transform": f"translate({x_m:.2f},{y_m:.2f})",
                "aria-label": f"waypoint {seq} (left-to-right along top row)",
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
                "fill": TOP_COPPER_PREVIEW_LABEL_FILL,
                "font-size": lbl_fs,
                "font-weight": "600",
                "font-family": "ui-monospace, Consolas, monospace",
                "class": "cyan-top-row-waypoint-temp-label",
            },
        ).text = str(seq)
