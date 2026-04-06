"""Emit stem neck TRACK segments for EasyEDA Standard.

Left: TopLayer (red, matches EasyEDA). J3 / right: BottomLayer (blue) — row-B column stacks,
stem-side pad → straddle (or pin), straddle → right stem pins.
"""

from __future__ import annotations

from collections.abc import Callable

from adapter_gen.geometry import (
    BoardParams,
    head_column_x_mil,
    wide_head_y_rows_mil,
)
from adapter_gen.preview_waypoint_style import TRACE_WIDTH_MIL
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_left_net_trace_polyline_mil,
    neck_stem_right_net_trace_polyline_mil,
    right_stem_straddle_or_pin_target_mil,
    wide_head_j3_row_column_vertical_trace_points_mil,
)

# Match ``row_reverser_emit`` / ``build_standard_compressed`` layer ids.
LAYER_TOP_COPPER = "1"
LAYER_BOTTOM_COPPER = "2"


def _append_track_polyline_segments(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    pts: list[tuple[float, float]],
    layer: str,
    mil_to_u: Callable[[float], float],
    sw: float,
) -> None:
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        u1, u2 = mil_to_u(x1), mil_to_u(y1)
        u3, u4 = mil_to_u(x2), mil_to_u(y2)
        shapes.append(
            f"TRACK~{sw}~{layer}~~{u1} {u2} {u3} {u4}~{nid()}~0"
        )


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
        _append_track_polyline_segments(
            shapes,
            nid,
            pts=pts,
            layer=LAYER_TOP_COPPER,
            mil_to_u=mil_to_u,
            sw=sw,
        )


def append_stem_neck_right_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """BottomLayer: straddle → right stem for nets num_cols+2 … 2*num_cols."""
    nc = p.num_cols
    sw = mil_to_u(trace_width_mil)
    for seq in range(nc + 2, 2 * nc + 1):
        pts = neck_stem_right_net_trace_polyline_mil(p, seq)
        if pts is None:
            continue
        _append_track_polyline_segments(
            shapes,
            nid,
            pts=pts,
            layer=LAYER_BOTTOM_COPPER,
            mil_to_u=mil_to_u,
            sw=sw,
        )


def append_wide_head_j3_row_column_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """BottomLayer: vertical traces through J3 / row-B pad stack per column."""
    traces = wide_head_j3_row_column_vertical_trace_points_mil(p)
    if not traces:
        return
    sw = mil_to_u(trace_width_mil)
    for _col, pts in traces:
        _append_track_polyline_segments(
            shapes,
            nid,
            pts=pts,
            layer=LAYER_BOTTOM_COPPER,
            mil_to_u=mil_to_u,
            sw=sw,
        )


def append_j3_head_to_right_stem_straddle_join_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """BottomLayer: stem-side J3 pad → straddle waypoint (or top right stem pin)."""
    ys_b = wide_head_y_rows_mil(p=p, from_row_a=False)
    if not ys_b:
        return
    y_head = ys_b[0]
    nc = p.num_cols
    sw = mil_to_u(trace_width_mil)
    for col in range(nc):
        seq = nc + col + 1
        end = right_stem_straddle_or_pin_target_mil(p, seq)
        if end is None:
            continue
        x0 = head_column_x_mil(col, p)
        pts = [(x0, y_head), end]
        _append_track_polyline_segments(
            shapes,
            nid,
            pts=pts,
            layer=LAYER_BOTTOM_COPPER,
            mil_to_u=mil_to_u,
            sw=sw,
        )


def append_stem_neck_j3_bottom_routing_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """BottomLayer J3: column stacks, head→straddle joins, straddle→pins."""
    append_wide_head_j3_row_column_easyeda_tracks(
        shapes, nid, p=p, mil_to_u=mil_to_u, trace_width_mil=trace_width_mil
    )
    append_j3_head_to_right_stem_straddle_join_easyeda_tracks(
        shapes, nid, p=p, mil_to_u=mil_to_u, trace_width_mil=trace_width_mil
    )
    append_stem_neck_right_easyeda_tracks(
        shapes, nid, p=p, mil_to_u=mil_to_u, trace_width_mil=trace_width_mil
    )
