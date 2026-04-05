"""Preview-only cyan waypoints on the neck (stem top row, straddle).

**Neck** here is the first stem row at ``y_stem_top`` (see ``stem_layout_mil``). Pin **1** is
the left stem hole (``x_ln``) and pin **(N/2+1)** is the right stem hole (``x_rn``). We **do
not** draw a waypoint on pin 1 (the pad is the anchor). Waypoints **2 … N/2** (i.e. ``2 …
num_cols``) sit **between** the two holes, inset so no marker reaches pin **(N/2+1)**.

Markers are **discrete** (no polyline). Labels are temporary discussion indices, not nets.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import HOLE_R, BoardParams, stem_layout_mil
from adapter_gen.preview_waypoint_style import (
    LABEL_DY_MIL,
    LABEL_FONT_SIZE_MIL,
    MARKER_RADIUS_MIL,
    MARKER_STROKE_MIL,
    MIN_TRACE_CENTER_PITCH_MIL,
)

_STROKE = "#5599dd"
_WP_DOT_FILL = "#e8f4fc"
# Mil past hole edge + marker radius so dots do not overlap drills or encroach pin (N/2+1).
_EDGE_GAP_MIL = 1.5


def neck_stem_top_straddle_waypoints_mil(
    p: BoardParams,
) -> list[tuple[float, float, int]]:
    """Waypoints ``2 … num_cols`` strictly between stem pin 1 and pin (N/2+1) holes.

    Pin 1 has no waypoint. Centers stay inside ``(x_ln, x_rn)`` with inset from ``HOLE_R``
    and the marker radius. Spacing uses at least ``TRACE_WIDTH + TRACE_GAP`` when the usable
    span allows; otherwise compressed. The chain is centered in the usable span when slack.
    """
    _, x_ln, x_rn, y_stem_top = stem_layout_mil(p)
    nc = p.num_cols
    # Need at least two interior waypoints (labels 2 and 3) for a meaningful split.
    if nc < 3:
        return []
    # Usable X strictly between hole centers (exclude pin 1 and pin num_cols+1).
    inset = HOLE_R + MARKER_RADIUS_MIL + _EDGE_GAP_MIL
    x_left = x_ln + inset
    x_right = x_rn - inset
    span = x_right - x_left
    if span <= 0.0:
        return []

    n_wp = nc - 1  # labels 2 .. nc (waypoint 1 omitted — same as pin 1)
    natural = span / max(1, n_wp - 1)
    min_pitch = MIN_TRACE_CENTER_PITCH_MIL
    if (n_wp - 1) * min_pitch <= span:
        pitch = max(min_pitch, natural)
    else:
        pitch = natural
    total = (n_wp - 1) * pitch
    x0 = x_left + (span - total) / 2.0
    wpts: list[tuple[float, float, int]] = []
    for k in range(n_wp):
        seq = k + 2  # 2, 3, …, nc
        wpts.append((x0 + k * pitch, y_stem_top, seq))
    return wpts


def append_neck_cyan_waypoints_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Append ``<g id="cyan-neck-waypoints">`` — markers + temp labels (preview only)."""
    wpts = neck_stem_top_straddle_waypoints_mil(p)
    if not wpts:
        return

    g = _sub(
        svg,
        "g",
        {
            "id": "cyan-neck-waypoints",
            "aria-label": (
                "Neck (stem straddle) cyan waypoint markers; preview only, not copper"
            ),
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
                "fill": "#1a3a5c",
                "font-size": lbl_fs,
                "font-weight": "600",
                "font-family": "ui-monospace, Consolas, monospace",
                "class": "cyan-neck-waypoint-temp-label",
            },
        ).text = str(seq)
