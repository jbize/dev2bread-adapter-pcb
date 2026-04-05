"""Emit row-reverser preview (SVG) and EasyEDA Standard shapes from shared geometry.

Single source: ``compute_row_reverser_geometry_mil`` + ``row_reverser_y_pad_row_a_innermost_mil``.
Cyan polylines → Top copper (layer 1); red → Bottom copper (layer 2). Matches
``docs/top-row-reverser-routing.md`` and ``emit_board_svg(..., row_reverser=True)``.

At each routing pass-through center in ``geom.vias``, EasyEDA JSON also emits a **VIA**
(``VIA~x~y~diameter~~holeR~gId``) so Top and Bottom tracks meet through a plated hole.
SVG still draws decorative crosses at those centers for clarity.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import BoardParams
from adapter_gen.row_reverser_geometry import (
    compute_row_reverser_geometry_mil,
    polyline_points_attr,
    row_reverser_y_pad_row_a_innermost_mil,
)

# Same layer table as ``build_standard_compressed`` in generate_easyeda_adapter_pcb.py
LAYER_TOP_COPPER = "1"
LAYER_BOTTOM_COPPER = "2"

# Plated routing vias (file units: 1 = 10 mil, same as ``mil_to_u`` in generate_easyeda_adapter_pcb).
# Outer 32 mil / 8 mil drill (4 mil radius) — typical signal via; matches LCEDA doc examples.
_ROUTING_VIA_OUTER_DIAM_MIL = 32.0
_ROUTING_VIA_HOLE_RADIUS_MIL = 4.0


def _dedupe_via_centers_mil(centers: list[tuple[float, float]]) -> list[tuple[float, float]]:
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

    def add_segments(
        seg: list[tuple[float, float]], layer: str
    ) -> None:
        if len(seg) < 2:
            return
        for i in range(len(seg) - 1):
            x1, y1 = seg[i]
            x2, y2 = seg[i + 1]
            shapes.append(
                f"TRACK~{sw}~{layer}~~{mil_to_u(x1)} {mil_to_u(y1)} "
                f"{mil_to_u(x2)} {mil_to_u(y2)}~{nid()}~0"
            )

    for seg in geom.cyan:
        add_segments(seg, LAYER_TOP_COPPER)
    for seg in geom.red:
        add_segments(seg, LAYER_BOTTOM_COPPER)

    d_u = mil_to_u(_ROUTING_VIA_OUTER_DIAM_MIL)
    hr_u = mil_to_u(_ROUTING_VIA_HOLE_RADIUS_MIL)
    for vx_m, vy_m in _dedupe_via_centers_mil(list(geom.vias)):
        shapes.append(
            f"VIA~{mil_to_u(vx_m)}~{mil_to_u(vy_m)}~{d_u}~~{hr_u}~{nid()}"
        )


def append_row_reverser_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
) -> None:
    """Append ``<g id=\"row-reverser\">`` children (same layout as prior ``svg_preview`` inline)."""
    y_pad = row_reverser_y_pad_row_a_innermost_mil(p)
    geom = compute_row_reverser_geometry_mil(p, y_pad_row=y_pad)
    if geom is None:
        return
    tw = f"{geom.trace_stroke:.1f}"
    g_rr = _sub(svg, "g", {"id": "row-reverser"})
    g_in = _sub(
        g_rr,
        "g",
        {
            "id": "row-reverser-inner",
            "fill": "none",
            "stroke": "#cc3333",
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
    g_out = _sub(
        g_rr,
        "g",
        {
            "id": "row-reverser-outer",
            "fill": "none",
            "stroke": "#5599dd",
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )
    for seg in geom.cyan:
        _sub(
            g_out,
            "polyline",
            {"points": polyline_points_attr(seg)},
        )
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
