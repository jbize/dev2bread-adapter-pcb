"""Preview-only: straight segment from each wide-head stub endpoint to the matching stem top.

Stub labels are row-A **net** ids (see ``reverser_head_stubs``). Stem: net **1** → J1 pin 1;
nets **2…N** → neck straddle waypoint for that pin. One polyline per stub — not a bus.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Literal

from adapter_gen.geometry import BoardParams, stem_layout_mil, stem_pin_y_mil
from adapter_gen.preview_waypoint_style import TRACE_WIDTH_MIL
from adapter_gen.reverser_head_stubs import reverser_head_stub_routing_mil
from adapter_gen.row_reverser_geometry import (
    polyline_points_attr,
    row_reverser_y_pad_row_a_innermost_mil,
)
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_top_straddle_waypoints_mil,
)

_STROKE = "#5599dd"


def append_wide_head_stub_stem_join_svg(
    svg: ET.Element,
    p: BoardParams,
    _sub: Callable[..., ET.Element],
    *,
    preview_traces: Literal["both", "top", "bottom"] = "both",
) -> None:
    """Emit ``cyan-wide-head-stub-stem-join`` when Top preview shows stub geometry."""
    if preview_traces == "bottom":
        return
    y_pad = row_reverser_y_pad_row_a_innermost_mil(p)
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    if rhs is None or not rhs.waypoints:
        return
    neck_list = neck_stem_top_straddle_waypoints_mil(p)
    neck_by_seq = {seq: (x, y) for x, y, seq in neck_list}
    _, x_ln, _, _ = stem_layout_mil(p)
    tw = f"{TRACE_WIDTH_MIL:.1f}"
    g = _sub(
        svg,
        "g",
        {
            "id": "cyan-wide-head-stub-stem-join",
            "fill": "none",
            "stroke": _STROKE,
            "stroke-width": tw,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "aria-label": (
                "J1 preview: wide-head stub end to stem top; not copper"
            ),
        },
    )
    for sx, sy, net_s in rhs.waypoints:
        try:
            net = int(net_s)
        except ValueError:
            continue
        if net == 1:
            ex, ey = x_ln, stem_pin_y_mil(0, p)
        elif net in neck_by_seq:
            ex, ey = neck_by_seq[net]
        else:
            continue
        _sub(
            g,
            "polyline",
            {
                "points": polyline_points_attr([(sx, sy), (ex, ey)]),
                "data-net": net_s,
            },
        )
