"""Emit stem neck TopLayer TRACK segments for EasyEDA Standard.

Uses the same geometry as the cyan neck SVG preview.
"""

from __future__ import annotations

from collections.abc import Callable

from adapter_gen.geometry import BoardParams
from adapter_gen.preview_waypoint_style import TRACE_WIDTH_MIL
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_left_net_trace_polyline_mil,
)

# Match ``row_reverser_emit`` / ``build_standard_compressed`` TopLayer id.
LAYER_TOP_COPPER = "1"


def append_stem_neck_left_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """Append TopLayer TRACK pairs for nets 2..num_cols (straddle → left stem).

    Pin 1 has no neck leg; head-to-neck connection is not drawn here.
    """
    sw = mil_to_u(trace_width_mil)
    for seq in range(2, p.num_cols + 1):
        pts = neck_stem_left_net_trace_polyline_mil(p, seq)
        if pts is None:
            continue
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            u1, u2 = mil_to_u(x1), mil_to_u(y1)
            u3, u4 = mil_to_u(x2), mil_to_u(y2)
            shapes.append(
                f"TRACK~{sw}~{LAYER_TOP_COPPER}~~{u1} {u2} {u3} {u4}~{nid()}~0"
            )
