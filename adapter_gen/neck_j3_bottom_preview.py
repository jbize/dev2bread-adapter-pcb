"""Preview-only: red straddle markers + straight lines to J3 pins for ``--bottom-only``.

Stroke #cc3333 matches row-reverser red (reference only — real neck is Top in EasyEDA).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import BoardParams, stem_layout_mil, stem_pin_y_mil
from adapter_gen.preview_waypoint_style import (
    LABEL_DY_MIL,
    LABEL_FONT_SIZE_MIL,
    MARKER_RADIUS_MIL,
    MARKER_STROKE_MIL,
    TRACE_WIDTH_MIL,
)
from adapter_gen.row_reverser_geometry import polyline_points_attr
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_top_straddle_waypoints_right_mil,
)

_STROKE = "#cc3333"
_WP_DOT_FILL = "#fce8e8"
_LBL_FILL = "#5c1a1a"


def append_neck_j3_stem_right_red_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Emit ``red-stem-j3-neck-ref-bottom-only`` — straight straddle → right pin."""
    wpts = neck_stem_top_straddle_waypoints_right_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "red-stem-j3-neck-ref-bottom-only",
            "aria-label": "Bottom preview: J3 straddle ref + straight to pins; not copper",
        },
    )
    nc = p.num_cols
    _, _, x_rn, _ = stem_layout_mil(p)
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
            "aria-label": "Straight straddle waypoint to right stem pin (bottom preview)",
        },
    )
    for x_m, y_m, seq in wpts:
        row_idx = seq - nc - 1
        py = stem_pin_y_mil(row_idx, p)
        pts = [(x_m, y_m), (x_rn, py)]
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
