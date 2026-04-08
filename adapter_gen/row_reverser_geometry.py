"""Row-reverser block geometry (mil, +Y down) aligned with ``BoardParams`` / ``head_column_x_mil``.

Column count is ``p.num_cols`` (half of ``p.n_pins``) — any adapter size the generator accepts.
Used by ``adapter_gen.svg_preview`` and ``scripts/row_reverser_svg.py``.
See ``docs/top-row-reverser-routing.md``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from adapter_gen.geometry import (
    HOLE_R,
    PITCH,
    BoardParams,
    head_column_x_mil,
    pad_clearance_radius_mil,
    wide_head_y_rows_mil,
)

# Match ``scripts/row_reverser_svg.py`` defaults
_DEFAULT_VIA_R = min(8.0, HOLE_R * 0.4)
_TRACE_STROKE = 6.0
_DEFAULT_TRACE_GAP = 8.0
_DEFAULT_EDGE_OFFSET = 2.0 * HOLE_R + 20.0
# Gap (mil) below pad copper to first reverser lane; keeps top-layer diagonals off J1 annuli.
_DEFAULT_NECK_CLEARANCE_MIL = 10.0
# Extra +Y (down) for all reverser routing vias and the tracks that terminate on them.
REVERSER_PASSTHROUGH_Y_OFFSET_MIL = 40.0
# Straight run below innermost J1 row before diagonal to edge via (EasyEDA clearance vs preview).
REVERSER_J1_VERTICAL_STUB_MIL = 20.0


def intersect_x_horizontal_with_segment(
    y_h: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> float | None:
    """X where horizontal line y=y_h meets segment (x0,y0)-(x1,y1), or None."""
    dy = y1 - y0
    if abs(dy) < 1e-9:
        return None
    t = (y_h - y0) / dy
    if t < -1e-6 or t > 1.0 + 1e-6:
        return None
    return x0 + t * (x1 - x0)


@dataclass(frozen=True)
class RowReverserGeometry:
    """Polylines and routing-via centers for the two-layer reverser sketch."""

    red: list[list[tuple[float, float]]]
    cyan: list[list[tuple[float, float]]]
    vias: list[tuple[float, float]]
    via_cross_arm: float
    trace_stroke: float
    via_r: float
    y_first_lane: float
    lane_pitch_dy: float


def row_reverser_y_pad_row_a_innermost_mil(p: BoardParams) -> float:
    """Y center (mil) of innermost wide row-A socket row (bottom of the top/stack rows).

    That is the row-A pad line closest to the gap toward the stem — still nets ``1..N/2`` per column, not
    row B. Matches the usual “inside” header row when four rows are populated on the top block.
    """
    ys = wide_head_y_rows_mil(p=p, from_row_a=True)
    return ys[-1]


def _compute_row_reverser_core(
    n: int,
    x_col: Callable[[int], float],
    *,
    y_pad_row: float,
    edge_offset_mil: float,
    pad_r: float,
    via_r: float,
    trace_gap: float,
    neck_clearance_mil: float,
    trace_stroke: float,
    max_y_span: float | None,
    y_min_floor: float | None = None,
    row_a_y_ascending: list[float] | None = None,
) -> RowReverserGeometry | None:
    if n < 2:
        return None

    trace_half = trace_stroke / 2.0
    # Clear pad copper (not just drill); else traces sit in the annulus if HOLE_R < PAD/2.
    pad_outer_r = pad_clearance_radius_mil(pad_r)
    y_first_lane = y_pad_row + pad_outer_r + trace_half + neck_clearance_mil
    y_min_eff = y_first_lane
    if y_min_floor is not None:
        y_min_eff = max(y_min_eff, y_min_floor)
    y_min_eff += REVERSER_PASSTHROUGH_Y_OFFSET_MIL

    x_e = x_col(0) + edge_offset_mil

    def x_inner_horizontal_end(i: int) -> float | None:
        if i == n - 1:
            return None
        j = n - 1 - i
        return (x_col(j - 1) + x_col(j)) / 2.0

    if n <= 1:
        dy = 0.0
    elif max_y_span is not None:
        dy = max_y_span / (n - 1)
    else:
        dy = 2.0 * via_r + trace_gap

    y_first_lane = y_min_eff

    def y_v(i: int) -> float:
        if n <= 1:
            return y_min_eff
        return y_min_eff + i * dy

    def y_inner_terminal(i: int) -> float:
        if i == n - 2:
            return y_v(n - 1)
        return y_v(i + 1)

    stub_y = y_pad_row + REVERSER_J1_VERTICAL_STUB_MIL

    # J6 top-layer reference: vertical stub end on column n-2, then diagonal to edge via (matches cyan).
    xa_j6, ya_j6 = x_col(n - 2), stub_y
    xb_j6, yb_j6 = x_e, y_v(n - 2)

    red: list[list[tuple[float, float]]] = []
    for i in range(n):
        x_end = x_inner_horizontal_end(i)
        if x_end is None:
            continue
        y_e = y_v(i)
        y_i = y_inner_terminal(i)
        if i == n - 2:
            red.append([(x_e, y_e), (x_end, y_i)])
        elif abs(y_i - y_e) < 1e-9:
            red.append([(x_e, y_e), (x_end, y_e)])
        else:
            xp = intersect_x_horizontal_with_segment(y_e, xa_j6, ya_j6, xb_j6, yb_j6)
            x_lo, x_hi = (x_end, x_e) if x_end < x_e else (x_e, x_end)
            use_bend = xp is not None and x_lo - 1e-3 <= xp <= x_hi + 1e-3
            if use_bend:
                assert xp is not None
                red.append([(x_e, y_e), (xp, y_e), (x_end, y_i)])
            else:
                red.append([(x_e, y_e), (x_end, y_i)])

    cyan: list[list[tuple[float, float]]] = []
    # Layer A: vertical stack on each column, 20 mil straight down from innermost row, then to V_i.
    # Stub clears large PTH annuli in EasyEDA before the south-east run (preview holes are smaller).
    if row_a_y_ascending is not None and len(row_a_y_ascending) >= 2:
        ys_join = list(row_a_y_ascending)
        for i in range(n):
            xi = x_col(i)
            pts: list[tuple[float, float]] = [(xi, ys_join[0])]
            for j in range(1, len(ys_join)):
                pts.append((xi, ys_join[j]))
            pts.append((xi, stub_y))
            pts.append((x_e, y_v(i)))
            cyan.append(pts)
    else:
        for i in range(n):
            xi = x_col(i)
            cyan.append([(xi, y_pad_row), (xi, stub_y), (x_e, y_v(i))])

    vias: list[tuple[float, float]] = []
    for i in range(n):
        ye = y_v(i)
        inner_x = x_inner_horizontal_end(i)
        if inner_x is None:
            vias.append((x_e, ye))
        else:
            yi = y_inner_terminal(i)
            vias.append((x_e, ye))
            vias.append((inner_x, yi))

    via_cross = max(3.0, via_r * 0.45)
    return RowReverserGeometry(
        red=red,
        cyan=cyan,
        vias=vias,
        via_cross_arm=via_cross,
        trace_stroke=trace_stroke,
        via_r=via_r,
        y_first_lane=y_first_lane,
        lane_pitch_dy=dy,
    )


def compute_row_reverser_geometry_mil(
    p: BoardParams,
    *,
    y_pad_row: float,
    edge_offset_mil: float = _DEFAULT_EDGE_OFFSET,
    pad_r: float = HOLE_R,
    via_r: float = _DEFAULT_VIA_R,
    trace_gap: float = _DEFAULT_TRACE_GAP,
    neck_clearance_mil: float = _DEFAULT_NECK_CLEARANCE_MIL,
    trace_stroke: float = _TRACE_STROKE,
    max_y_span: float | None = None,
    y_min_floor: float | None = None,
) -> RowReverserGeometry | None:
    """Compute polylines and via positions in board mil coordinates.

    Uses ``n = p.num_cols`` (no fixed pin count — whatever ``BoardParams`` the adapter build uses).
    Column ``i`` matches ``head_column_x_mil(i, p)``. Edge via column is to the right of
    column 0 at ``head_column_x_mil(0, p) + edge_offset_mil``.

    On layer A (cyan), when there are multiple row-A socket rows, each column first gets vertical
    segments joining all of those pad centers at ``x(i)``, then the usual diagonal from the
    innermost row-A pad (``y_pad_row``) to edge via ``V_i``.

    Wide-head exit stubs (below the socket rows, not stem copper) are **not** part of this struct;
    see ``reverser_head_stubs`` and ``row_reverser_emit``.
    """
    n = p.num_cols

    def x_col(i: int) -> float:
        return head_column_x_mil(i, p)

    ys_a = wide_head_y_rows_mil(p=p, from_row_a=True)
    return _compute_row_reverser_core(
        n,
        x_col,
        y_pad_row=y_pad_row,
        edge_offset_mil=edge_offset_mil,
        pad_r=pad_r,
        via_r=via_r,
        trace_gap=trace_gap,
        neck_clearance_mil=neck_clearance_mil,
        trace_stroke=trace_stroke,
        max_y_span=max_y_span,
        y_min_floor=y_min_floor,
        row_a_y_ascending=ys_a,
    )


def compute_row_reverser_geometry_mil_standalone(
    n: int,
    *,
    pitch: float = PITCH,
    x_origin_left: float = 0.0,
    y_pad_row: float = 0.0,
    edge_offset_mil: float = _DEFAULT_EDGE_OFFSET,
    pad_r: float = HOLE_R,
    via_r: float = _DEFAULT_VIA_R,
    trace_gap: float = _DEFAULT_TRACE_GAP,
    neck_clearance_mil: float = _DEFAULT_NECK_CLEARANCE_MIL,
    trace_stroke: float = _TRACE_STROKE,
    max_y_span: float | None = None,
    y_min_floor: float | None = None,
) -> RowReverserGeometry | None:
    """Same geometry as ``row_reverser_svg.py`` (left column at ``x_origin_left``)."""

    def x_col(i: int) -> float:
        return x_origin_left + (n - 1 - i) * pitch

    return _compute_row_reverser_core(
        n,
        x_col,
        y_pad_row=y_pad_row,
        edge_offset_mil=edge_offset_mil,
        pad_r=pad_r,
        via_r=via_r,
        trace_gap=trace_gap,
        neck_clearance_mil=neck_clearance_mil,
        trace_stroke=trace_stroke,
        max_y_span=max_y_span,
        y_min_floor=y_min_floor,
        row_a_y_ascending=None,
    )


def polyline_points_attr(points: list[tuple[float, float]]) -> str:
    """SVG ``points`` attribute string."""
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
