"""Preview-only cyan waypoints on the neck (stem top row, straddle).

**Neck** waypoints sit on a horizontal line level with the **top** of stem pin/hole **1**
(center minus ``HOLE_R`` in +Y-down space). Pin **1** is
the left stem hole (``x_ln``) and pin **(N/2+1)** is the right stem hole (``x_rn``). We **do
not** draw a waypoint on pin 1 (the pad is the anchor). Waypoints **2 … N/2** (i.e. ``2 …
num_cols``) sit **between** the two holes, inset so no marker reaches pin **(N/2+1)**.

**Invariant:** each neck waypoint maps to **one and only one** left-stem pin/hole
(waypoint ``k`` ↔ pin ``k``). Same-layer routes must not cross in ways that imply
unintended connectivity; see ``docs/adapter-routing-invariants.md``.

Markers are **discrete** (no bus along the straddle). Cyan paths to pin **k**: vertical
down from the waypoint, then horizontal to ``(x_ln, pin k)`` (no lateral step at the neck).
Waypoints are placed with **extra inset** toward the straddle center so those verticals sit
clear of the hole columns. Pin 1 has no waypoint. Labels are temporary.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import HOLE_R, BoardParams, stem_layout_mil, stem_pin_y_mil
from adapter_gen.row_reverser_geometry import polyline_points_attr
from adapter_gen.preview_waypoint_style import (
    LABEL_DY_MIL,
    LABEL_FONT_SIZE_MIL,
    MARKER_RADIUS_MIL,
    MARKER_STROKE_MIL,
    MIN_TRACE_CENTER_PITCH_MIL,
    TRACE_WIDTH_MIL,
)

_STROKE = "#5599dd"
_WP_DOT_FILL = "#e8f4fc"
# Mil past hole edge + marker radius so dots do not overlap drills or encroach pin (N/2+1).
_EDGE_GAP_MIL = 1.5
# Pull the waypoint chain toward straddle center (both sides) so vertical trace
# centerlines clear hole copper; verticals still drop straight from each waypoint (x_m).
_NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL = 8.0


def neck_stem_top_straddle_waypoints_mil(
    p: BoardParams,
) -> list[tuple[float, float, int]]:
    """Waypoints ``2 … num_cols`` strictly between stem pin 1 and pin (N/2+1) holes.

    Pin 1 has no waypoint. Centers stay inside ``(x_ln, x_rn)`` with inset from ``HOLE_R``,
    marker radius, plus ``_NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL`` so trace centerlines stay
    past hole copper (``HOLE_R + trace/2 + TRACE_GAP`` from each column). Spacing uses at least
    ``TRACE_WIDTH + TRACE_GAP`` when the usable span allows; otherwise compressed. The chain
    is centered in the usable span when slack.
    """
    _, x_ln, x_rn, _ = stem_layout_mil(p)
    nc = p.num_cols
    # Need at least two interior waypoints (labels 2 and 3) for a meaningful split.
    if nc < 3:
        return []
    # Same Y for all neck markers: top of pin-1 hole (not drill center — sits slightly up).
    y_neck = stem_pin_y_mil(0, p) - HOLE_R
    # Usable X between hole centers: marker clearance + squeeze toward center straddle.
    inset = (
        HOLE_R
        + MARKER_RADIUS_MIL
        + _EDGE_GAP_MIL
        + _NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL
    )
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
        wpts.append((x0 + k * pitch, y_neck, seq))
    return wpts


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
                "Per net: vertical then horizontal to left stem pin (not a bus)"
            ),
        },
    )
    for x_m, y_m, seq in wpts:
        py = stem_pin_y_mil(seq - 1, p)
        pts = [(x_m, y_m), (x_m, py), (x_ln, py)]
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
                "fill": "#1a3a5c",
                "font-size": lbl_fs,
                "font-weight": "600",
                "font-family": "ui-monospace, Consolas, monospace",
                "class": "cyan-neck-waypoint-temp-label",
            },
        ).text = str(seq)
