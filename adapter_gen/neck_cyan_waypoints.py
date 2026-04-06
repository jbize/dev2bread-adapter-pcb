"""Preview-only TopLayer (red) waypoints on the neck (stem top row, straddle).

**Neck** waypoints sit on a horizontal line level with the **top** of stem pin/hole **1**
(center minus ``HOLE_R`` in +Y-down space). Pin **1** is
the left stem hole (``x_ln``) and pin **(N/2+1)** is the right stem hole (``x_rn``). We **do
not** draw a waypoint on pin 1 (the pad is the anchor). Waypoints **2 … N/2** (i.e. ``2 …
num_cols``) sit **between** the two holes, inset so no marker reaches pin **(N/2+1)**.

**Invariant:** each neck waypoint maps to **one and only one** left-stem pin/hole
(waypoint ``k`` ↔ pin ``k``). Same-layer routes must not cross in ways that imply
unintended connectivity; see ``docs/adapter-routing-invariants.md``.

Geometry matches ``adapter_gen/stem_neck_routing_mil`` (also used by the EasyEDA generator).
Markers are **discrete** (no bus along the straddle). Pin 1 has no waypoint. Labels are
temporary.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import BoardParams, stem_layout_mil, stem_pin_y_mil
from adapter_gen.row_reverser_geometry import polyline_points_attr
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
from adapter_gen.stem_neck_routing_mil import (
    NECK_BEND_BELOW_PRIOR_PIN_MIL,
    neck_stem_top_straddle_waypoints_mil,
)

_STROKE = TOP_COPPER_PREVIEW_STROKE
_WP_DOT_FILL = TOP_COPPER_PREVIEW_DOT_FILL


def append_neck_cyan_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Append ``cyan-neck-waypoints``: traces to left stem pins, then markers (preview)."""
    wpts = neck_stem_top_straddle_waypoints_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "cyan-neck-waypoints",
            "aria-label": (
                "Neck straddle sketch: per-net traces to left stem pins; preview only"
            ),
        },
    )
    _, x_ln, _, _ = stem_layout_mil(p)
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    g_lines = _sub(
        g,
        "g",
        {
            "id": "cyan-neck-waypoint-to-left-stem-pin-traces",
            "fill": "none",
            "stroke": _STROKE,
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "aria-label": (
                "Per net: vertical to bend below prior pin, then straight to target pin"
            ),
        },
    )
    for x_m, y_m, seq in wpts:
        py = stem_pin_y_mil(seq - 1, p)
        y_bend = stem_pin_y_mil(seq - 2, p) + NECK_BEND_BELOW_PRIOR_PIN_MIL
        pts = [(x_m, y_m), (x_m, y_bend), (x_ln, py)]
        _sub(
            g_lines,
            "polyline",
            {
                "points": polyline_points_attr(pts),
                "data-neck-seq": str(seq),
                "data-left-stem-net": str(seq),
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
                "id": f"cyan-neck-wp-{seq}",
                "transform": f"translate({x_m:.2f},{y_m:.2f})",
                "aria-label": (
                    f"neck waypoint {seq} (left to right along stem straddle)"
                ),
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
                "class": "cyan-neck-waypoint-temp-label",
            },
        ).text = str(seq)
