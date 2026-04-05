"""Emit row-reverser preview (SVG) and EasyEDA Standard shapes from shared geometry.

Geometry: ``compute_row_reverser_geometry_mil`` + ``row_reverser_y_pad_row_a_innermost_mil``;
wide-head stub routing from ``reverser_head_stub_routing_mil`` (cyan + optional bottom PTHs;
not T-stem / neck copper).
Cyan polylines → Top copper (layer 1); red → Bottom copper (layer 2). Matches
``docs/top-row-reverser-routing.md`` and ``emit_board_svg(..., row_reverser=True)``.

At each routing pass-through center in ``geom.vias``, EasyEDA JSON also emits a **VIA**
(``VIA~x~y~diameter~~holeR~gId``) so Top and Bottom tracks meet through a plated hole.
SVG still draws decorative crosses at those centers for clarity.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable

from adapter_gen.geometry import HOLE_R, PAD_SIZE, BoardParams
from adapter_gen.reverser_head_stubs import reverser_head_stub_routing_mil
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
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    cyan = list(geom.cyan) + ([] if rhs is None else rhs.cyan_segments)

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

    for seg in cyan:
        add_segments(seg, LAYER_TOP_COPPER)
    for seg in geom.red:
        add_segments(seg, LAYER_BOTTOM_COPPER)

    d_u = mil_to_u(_ROUTING_VIA_OUTER_DIAM_MIL)
    hr_u = mil_to_u(_ROUTING_VIA_HOLE_RADIUS_MIL)
    for vx_m, vy_m in _dedupe_via_centers_mil(list(geom.vias)):
        shapes.append(
            f"VIA~{mil_to_u(vx_m)}~{mil_to_u(vy_m)}~{d_u}~~{hr_u}~{nid()}"
        )

    if rhs is not None:
        pw = mil_to_u(PAD_SIZE)
        hr_pad = mil_to_u(HOLE_R)
        for x_m, y_m, net in rhs.bottom_pads:
            shapes.append(
                f"PAD~ELLIPSE~{mil_to_u(x_m)}~{mil_to_u(y_m)}~{pw}~{pw}~11~~{net}~{hr_pad}~~0~{nid()}"
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
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    cyan = list(geom.cyan) + ([] if rhs is None else rhs.cyan_segments)
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
    for seg in cyan:
        _sub(
            g_out,
            "polyline",
            {"points": polyline_points_attr(seg)},
        )
    pr = f"{PAD_SIZE * 0.5:.2f}"
    if rhs is not None:
        sw_ns = max(1.0, float(tw) * 0.35)
        g_ns = _sub(
            g_rr,
            "g",
            {
                "id": "reverser-head-stub-pads",
                "fill": "#3a3a3a",
                "stroke": "#888888",
                "stroke-width": f"{sw_ns:.2f}",
            },
        )
        tpad = max(8.0, float(PAD_SIZE) * 0.22)
        for x_m, y_m, net in rhs.bottom_pads:
            g_p = _sub(
                g_ns,
                "g",
                {
                    "id": f"reverser-head-stub-pad-net-{net}",
                    "transform": f"translate({x_m:.2f},{y_m:.2f})",
                },
            )
            _sub(g_p, "circle", {"r": pr})
            _sub(
                g_p,
                "text",
                {
                    "x": "0",
                    "y": f"{float(pr) * 0.35:.2f}",
                    "text-anchor": "middle",
                    "fill": "#9cf",
                    "font-size": f"{tpad:.1f}",
                    "font-family": "ui-monospace, Consolas, monospace",
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
    lbl_fs = max(8.0, geom.via_r * 1.25)
    lbl_y = float(vr) + max(5.0, geom.via_r * 0.45)
    for (vx_m, vy_m), vlab in zip(geom.vias, geom.via_labels, strict=True):
        g_one = _sub(
            g_v,
            "g",
            {
                "id": f"via-{vlab}",
                "transform": f"translate({vx_m:.2f},{vy_m:.2f})",
                "aria-label": f"passthrough {vlab}",
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
        _sub(
            g_one,
            "text",
            {
                "x": "0",
                "y": f"{lbl_y:.2f}",
                "text-anchor": "middle",
                "fill": "#b8e6c8",
                "font-size": f"{lbl_fs:.1f}",
                "font-family": "ui-monospace, Consolas, monospace",
            },
        ).text = vlab
