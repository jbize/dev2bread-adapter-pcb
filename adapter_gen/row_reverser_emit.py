"""Emit row-reverser preview (SVG) and EasyEDA Standard shapes from shared geometry.

Geometry: ``compute_row_reverser_geometry_mil`` + ``row_reverser_y_pad_row_a_innermost_mil``;
wide-head stub routing from ``reverser_head_stub_routing_mil`` (top layer; stub-end waypoints
for naming only — not T-stem copper).
Top-copper polylines → red strokes; bottom-copper → blue (EasyEDA layer colors). Matches
``docs/top-row-reverser-routing.md`` and ``emit_board_svg(..., row_reverser=True)``.

At each routing pass-through center in ``geom.vias``, EasyEDA JSON also emits a **VIA**
(``VIA~x~y~diameter~~holeR~gId``) so Top and Bottom tracks meet through a plated hole.
SVG still draws decorative crosses at those centers for clarity.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Literal

from adapter_gen.easyeda_layers import (
    EASYEDA_BOTTOM_LAYER_ID,
    EASYEDA_TOP_LAYER_ID,
    ROUTING_VIA_HOLE_RADIUS_MIL,
    ROUTING_VIA_OUTER_DIAM_MIL,
)
from adapter_gen.geometry import BoardParams
from adapter_gen.preview_waypoint_style import (
    BOTTOM_COPPER_PREVIEW_STROKE,
    TOP_COPPER_PREVIEW_LABEL_FILL,
    TOP_COPPER_PREVIEW_STROKE,
)
from adapter_gen.reverser_head_stubs import reverser_head_stub_routing_mil
from adapter_gen.row_reverser_geometry import (
    compute_row_reverser_geometry_mil,
    polyline_points_attr,
    row_reverser_y_pad_row_a_innermost_mil,
)


def _dedupe_via_centers_mil(
    centers: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    seen: set[tuple[float, float]] = set()
    out: list[tuple[float, float]] = []
    for x, y in centers:
        key = (round(x, 6), round(y, 6))
        if key in seen:
            continue
        seen.add(key)
        out.append((x, y))
    return out


def append_row_reverser_easyeda_shapes(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
) -> None:
    """Append TRACK segments (Top + Bottom) for the row-reverser sketch."""
    y_pad = row_reverser_y_pad_row_a_innermost_mil(p)
    geom = compute_row_reverser_geometry_mil(p, y_pad_row=y_pad)
    if geom is None:
        return
    sw = mil_to_u(geom.trace_stroke)
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    cyan = list(geom.cyan) + ([] if rhs is None else rhs.cyan_segments)

    def add_segments(seg: list[tuple[float, float]], layer: str) -> None:
        if len(seg) < 2:
            return
        for i in range(len(seg) - 1):
            x1, y1 = seg[i]
            x2, y2 = seg[i + 1]
            shapes.append(
                f"TRACK~{sw}~{layer}~~{mil_to_u(x1)} {mil_to_u(y1)} "
                f"{mil_to_u(x2)} {mil_to_u(y2)}~{nid()}~0"
            )

    for seg in cyan:
        add_segments(seg, EASYEDA_TOP_LAYER_ID)
    for seg in geom.red:
        add_segments(seg, EASYEDA_BOTTOM_LAYER_ID)

    d_u = mil_to_u(ROUTING_VIA_OUTER_DIAM_MIL)
    hr_u = mil_to_u(ROUTING_VIA_HOLE_RADIUS_MIL)
    for vx_m, vy_m in _dedupe_via_centers_mil(list(geom.vias)):
        shapes.append(f"VIA~{mil_to_u(vx_m)}~{mil_to_u(vy_m)}~{d_u}~~{hr_u}~{nid()}")


def append_row_reverser_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
    *,
    preview_traces: Literal["both", "top", "bottom"] = "both",
) -> None:
    """Append ``<g id=\"row-reverser\">`` (same layout as prior ``svg_preview`` inline).

    ``preview_traces`` (SVG only): ``top`` = Top copper (red) polylines + stub sketch;
    ``bottom`` = Bottom copper (blue) polylines; ``both`` = both. Vias draw whenever
    geometry exists.
    """
    y_pad = row_reverser_y_pad_row_a_innermost_mil(p)
    geom = compute_row_reverser_geometry_mil(p, y_pad_row=y_pad)
    if geom is None:
        return
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    cyan = list(geom.cyan) + ([] if rhs is None else rhs.cyan_segments)
    tw = f"{geom.trace_stroke:.1f}"
    g_rr = _sub(svg, "g", {"id": "row-reverser"})
    show_bottom = preview_traces in ("both", "bottom")
    show_top = preview_traces in ("both", "top")
    if show_bottom:
        g_in = _sub(
            g_rr,
            "g",
            {
                "id": "row-reverser-inner",
                "fill": "none",
                "stroke": BOTTOM_COPPER_PREVIEW_STROKE,
                "stroke-width": tw,
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
            },
        )
        for seg in geom.red:
            _sub(
                g_in,
                "polyline",
                {"points": polyline_points_attr(seg)},
            )
    if show_top:
        g_out = _sub(
            g_rr,
            "g",
            {
                "id": "row-reverser-outer",
                "fill": "none",
                "stroke": TOP_COPPER_PREVIEW_STROKE,
                "stroke-width": tw,
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
            },
        )
        for seg in cyan:
            _sub(
                g_out,
                "polyline",
                {"points": polyline_points_attr(seg)},
            )
    if rhs is not None and show_top:
        g_wp = _sub(
            g_rr,
            "g",
            {
                "id": "reverser-head-stub-waypoints",
                "aria-label": "wide-head stub trace bottoms (preview only; not copper)",
            },
        )
        tw_num = float(tw)
        lbl_fs = max(10.0, tw_num * 1.15)
        lbl_dy = max(14.0, tw_num * 1.4)
        for x_m, y_m, net in rhs.waypoints:
            g_w = _sub(
                g_wp,
                "g",
                {
                    "id": f"reverser-head-tp-{net}",
                    "transform": f"translate({x_m:.2f},{y_m:.2f})",
                    "aria-label": f"stub endpoint net {net}",
                    "data-net": net,
                    "data-x-mil": f"{x_m:.2f}",
                    "data-y-mil": f"{y_m:.2f}",
                    "data-temp-preview-label": "true",
                },
            )
            _sub(
                g_w,
                "text",
                {
                    "x": "0",
                    "y": f"{lbl_dy:.2f}",
                    "text-anchor": "middle",
                    "fill": TOP_COPPER_PREVIEW_LABEL_FILL,
                    "font-size": f"{lbl_fs:.1f}",
                    "font-family": "ui-monospace, Consolas, monospace",
                    "class": "reverser-head-stub-temp-label",
                },
            ).text = net
    vx = geom.via_cross_arm
    vr = f"{geom.via_r:.2f}"
    g_v = _sub(
        g_rr,
        "g",
        {
            "id": "row-reverser-vias",
            "fill": "#2a6644",
            "stroke": "#88cc88",
            "stroke-width": "1.5",
            "stroke-linecap": "round",
        },
    )
    for vx_m, vy_m in geom.vias:
        g_one = _sub(
            g_v,
            "g",
            {
                "transform": f"translate({vx_m:.2f},{vy_m:.2f})",
            },
        )
        _sub(g_one, "circle", {"r": vr})
        _sub(
            g_one,
            "line",
            {
                "x1": f"{-vx:.2f}",
                "y1": "0",
                "x2": f"{vx:.2f}",
                "y2": "0",
                "stroke": "#eef6ee",
                "stroke-width": f"{max(0.8, geom.via_r * 0.12):.2f}",
            },
        )
        _sub(
            g_one,
            "line",
            {
                "x1": "0",
                "y1": f"{-vx:.2f}",
                "x2": "0",
                "y2": f"{vx:.2f}",
                "stroke": "#eef6ee",
                "stroke-width": f"{max(0.8, geom.via_r * 0.12):.2f}",
            },
        )
