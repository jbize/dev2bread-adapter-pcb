"""Emit stem neck TRACK segments for EasyEDA Standard.

TopLayer: wide-head stub end → stem straddle (or pin 1); straddle → left stem pins.
BottomLayer: J3 row stacks, J3 → straddle, straddle → right stem pins.
"""

from __future__ import annotations

from collections.abc import Callable

from adapter_gen.easyeda_layers import EASYEDA_BOTTOM_LAYER_ID, EASYEDA_TOP_LAYER_ID
from adapter_gen.geometry import (
    BoardParams,
    head_column_x_mil,
    stem_layout_mil,
    stem_pin_y_mil,
    wide_head_y_rows_mil,
)
from adapter_gen.preview_waypoint_style import TRACE_WIDTH_MIL
from adapter_gen.reverser_head_stubs import reverser_head_stub_routing_mil
from adapter_gen.row_reverser_geometry import row_reverser_y_pad_row_a_innermost_mil
from adapter_gen.stem_neck_routing_mil import (
    neck_stem_left_net_trace_polyline_mil,
    neck_stem_right_net_trace_polyline_mil,
    neck_stem_top_straddle_waypoints_mil,
    right_stem_straddle_or_pin_target_mil,
    wide_head_j3_row_column_vertical_trace_points_mil,
)

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


def append_wide_head_stub_stem_join_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """TopLayer: straight segment from each wide-head stub end to straddle (or J1 pin 1).

    Same geometry as ``wide_head_stub_stem_join_preview`` / ``reverser_head_stub_routing_mil``.
    Nets 2…num_cols need straddle waypoints (``num_cols`` ≥ 3); net 1 → ``(x_ln, pin 1)``.
    """
    y_pad = row_reverser_y_pad_row_a_innermost_mil(p)
    rhs = reverser_head_stub_routing_mil(p, y_pad_row=y_pad)
    if rhs is None or not rhs.waypoints:
        return
    neck_list = neck_stem_top_straddle_waypoints_mil(p)
    neck_by_seq = {seq: (x, y) for x, y, seq in neck_list}
    _, x_ln, _, _ = stem_layout_mil(p)
    sw = mil_to_u(trace_width_mil)
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
        pts = [(sx, sy), (ex, ey)]
        _append_track_polyline_segments(
            shapes,
            nid,
            pts=pts,
            layer=EASYEDA_TOP_LAYER_ID,
            mil_to_u=mil_to_u,
            sw=sw,
        )


def append_stem_neck_left_easyeda_tracks(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    p: BoardParams,
    mil_to_u: Callable[[float], float],
    trace_width_mil: float = TRACE_WIDTH_MIL,
) -> None:
    """Append TopLayer TRACK for nets 2..num_cols (straddle → left stem pins).

    Stub end → straddle is ``append_wide_head_stub_stem_join_easyeda_tracks`` (run first).
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
            layer=EASYEDA_TOP_LAYER_ID,
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
            layer=EASYEDA_BOTTOM_LAYER_ID,
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
            layer=EASYEDA_BOTTOM_LAYER_ID,
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
            layer=EASYEDA_BOTTOM_LAYER_ID,
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
