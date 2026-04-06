"""Top-copper stubs on the wide head after the row-reverser block (adapter layer).

They run from ``E_n`` and each gap ``G_1 … G_{n-1}`` down to ``y_end`` just below the stem-side
row of wide-head socket holes. **Not** T-stem copper: the narrow stem toward the breadboard is
still unimplemented here.

Not part of ``row_reverser_geometry``. See ``docs/top-row-reverser-routing.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from adapter_gen.geometry import (
    BoardParams,
    HOLE_R,
    head_column_x_mil,
    pad_clearance_radius_mil,
    wide_head_y_rows_mil,
)
from adapter_gen.row_reverser_geometry import REVERSER_PASSTHROUGH_Y_OFFSET_MIL

# Match ``row_reverser_geometry.py`` defaults
_DEFAULT_VIA_R = min(8.0, HOLE_R * 0.4)
_TRACE_STROKE = 6.0
_DEFAULT_TRACE_GAP = 8.0
_DEFAULT_EDGE_OFFSET = 2.0 * HOLE_R + 20.0
_DEFAULT_NECK_CLEARANCE_MIL = 10.0


@dataclass(frozen=True)
class ReverserHeadStubRouting:
    """Cyan segments and stub-end waypoints (order: ``E_n``, then ``G_1 … G_{n-1}``)."""

    cyan_segments: list[list[tuple[float, float]]]
    # (x_mil, y_mil, net_str). Reference-only TP waypoints — not PCB copper/silk.
    waypoints: list[tuple[float, float, str]]


def reverser_head_stub_routing_mil(
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
) -> ReverserHeadStubRouting | None:
    """Wide-head stub geometry or ``None`` if not applicable."""
    n = p.num_cols
    if n < 2:
        return None

    def x_col(i: int) -> float:
        return head_column_x_mil(i, p)

    x_e = x_col(0) + edge_offset_mil

    trace_half = trace_stroke / 2.0
    pad_outer_r = pad_clearance_radius_mil(pad_r)
    y_first_lane = y_pad_row + pad_outer_r + trace_half + neck_clearance_mil
    y_min_eff = y_first_lane
    if y_min_floor is not None:
        y_min_eff = max(y_min_eff, y_min_floor)
    y_min_eff += REVERSER_PASSTHROUGH_Y_OFFSET_MIL

    if max_y_span is not None:
        dy = max_y_span / (n - 1)
    else:
        dy = 2.0 * via_r + trace_gap

    def y_v(i: int) -> float:
        return y_min_eff + i * dy

    def x_inner_horizontal_end(i: int) -> float | None:
        if i == n - 1:
            return None
        j = n - 1 - i
        return (x_col(j - 1) + x_col(j)) / 2.0

    def y_inner_terminal(i: int) -> float:
        if i == n - 2:
            return y_v(n - 1)
        return y_v(i + 1)

    y_bottom_right_via = y_v(n - 1)
    stem_side_row_b_y = wide_head_y_rows_mil(p=p, from_row_a=False)[0]
    y_end = stem_side_row_b_y + pad_outer_r + neck_clearance_mil + trace_stroke / 2.0

    if y_end <= y_bottom_right_via + 1e-6:
        return None
    cyan: list[list[tuple[float, float]]] = [
        [(x_e, y_bottom_right_via), (x_e, y_end)],
    ]
    # Stub-end waypoints (same net labels as row-A column): E_n → n; G_k → k.
    wpts: list[tuple[float, float, str]] = [(x_e, y_end, str(n))]
    for i in range(n - 1):
        ix = x_inner_horizontal_end(i)
        if ix is None:
            continue
        yt = y_inner_terminal(i)
        if y_end > yt + 1e-6:
            cyan.append([(ix, yt), (ix, y_end)])
            wpts.append((ix, y_end, str(i + 1)))
    return ReverserHeadStubRouting(cyan_segments=cyan, waypoints=wpts)


def reverser_head_stub_cyan_segments_mil(
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
) -> list[list[tuple[float, float]]]:
    """Extra layer-A polylines (mil) for wide-head stubs; empty if not applicable."""
    r = reverser_head_stub_routing_mil(
        p,
        y_pad_row=y_pad_row,
        edge_offset_mil=edge_offset_mil,
        pad_r=pad_r,
        via_r=via_r,
        trace_gap=trace_gap,
        neck_clearance_mil=neck_clearance_mil,
        trace_stroke=trace_stroke,
        max_y_span=max_y_span,
        y_min_floor=y_min_floor,
    )
    return [] if r is None else r.cyan_segments
