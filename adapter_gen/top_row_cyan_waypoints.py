"""Preview-only cyan waypoints along the outermost wide row-A pad line (top row, +Y down).

Order is **left → right** in mil space: position **1** is the **leftmost** column, **num_cols**
the **rightmost**. This matches ``head_column_x_mil`` (``col = num_cols - 1`` is smallest **X**).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import BoardParams, head_column_x_mil, wide_head_y_rows_mil

_STROKE = "#5599dd"
# Discrete markers only — no segment connecting pads (that would imply a copper short).
_WP_DOT_R = "7.0"
_WP_DOT_FILL = "#e8f4fc"
_WP_DOT_STROKE_W = "2.5"


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


def append_top_row_cyan_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Append ``<g id="cyan-top-row-waypoints">`` — per-pad markers + temp 1…N labels (preview only)."""
    _, wpts = top_row_a_waypoints_left_to_right_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "cyan-top-row-waypoints",
            "aria-label": "Top row (row A outer) waypoint markers; preview only, not copper",
        },
    )
    tw = 6.0
    lbl_fs = max(12.0, tw * 1.35)
    lbl_dy = max(16.0, tw * 1.55)
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
                "r": _WP_DOT_R,
                "fill": _WP_DOT_FILL,
                "stroke": _STROKE,
                "stroke-width": _WP_DOT_STROKE_W,
            },
        )
        _sub(
            g_w,
            "text",
            {
                "x": "0",
                "y": f"{lbl_dy:.2f}",
                "text-anchor": "middle",
                "fill": "#1a3a5c",
                "font-size": f"{lbl_fs:.1f}",
                "font-weight": "600",
                "font-family": "ui-monospace, Consolas, monospace",
                "class": "cyan-top-row-waypoint-temp-label",
            },
        ).text = str(seq)
