"""Stem neck routing geometry (mil): straddle waypoints to stem pins + J3 wide-head helpers.

Single source of truth for SVG preview and EasyEDA ``TRACK`` segments (``stem_neck_emit``).

**Left column:** nets **2 … num_cols** (no straddle waypoint for pin 1). **Right / J3:**
nets **num_cols+2 … 2*num_cols** (no straddle waypoint for net ``num_cols+1``). J3 wide-head
column stacks and head→straddle joins use ``head_column_x_mil`` / ``wide_head_y_rows_mil``.
"""

from __future__ import annotations

from adapter_gen.geometry import (
    HOLE_R,
    BoardParams,
    head_column_x_mil,
    pad_clearance_radius_mil,
    stem_layout_mil,
    stem_pin_y_mil,
    wide_head_y_rows_mil,
)
from adapter_gen.preview_waypoint_style import (
    MARKER_RADIUS_MIL,
    MIN_TRACE_CENTER_PITCH_MIL,
)

# Mil past hole edge + marker radius so dots do not overlap drills or encroach pin (N/2+1).
_EDGE_GAP_MIL = 1.5

# Pull the waypoint chain toward straddle center so vertical trace centerlines clear holes.
NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL = 8.0
# Bend each net just below the prior pin center (+Y down), then diagonal into target pin.
NECK_BEND_BELOW_PRIOR_PIN_MIL = 8.0


def neck_stem_top_straddle_waypoints_mil(
    p: BoardParams,
) -> list[tuple[float, float, int]]:
    """Waypoints ``2 … num_cols`` strictly between stem pin 1 and pin (N/2+1) holes.

    Pin 1 has no waypoint. Centers stay inside ``(x_ln, x_rn)`` with inset from pad copper
    (``pad_clearance_radius_mil(HOLE_R)``), marker radius, plus
    ``NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL``. Spacing uses at least
    ``TRACE_WIDTH + TRACE_GAP`` when the usable span allows; otherwise compressed. The chain
    is centered in the usable span when slack.
    """
    _, x_ln, x_rn, _ = stem_layout_mil(p)
    nc = p.num_cols
    if nc < 3:
        return []
    pr = pad_clearance_radius_mil(HOLE_R)
    y_neck = stem_pin_y_mil(0, p) - pr
    inset = (
        pr
        + MARKER_RADIUS_MIL
        + _EDGE_GAP_MIL
        + NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL
    )
    x_left = x_ln + inset
    x_right = x_rn - inset
    span = x_right - x_left
    if span <= 0.0:
        return []

    n_wp = nc - 1
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
        seq = k + 2
        wpts.append((x0 + k * pitch, y_neck, seq))
    return wpts


def neck_stem_top_straddle_waypoints_right_mil(
    p: BoardParams,
) -> list[tuple[float, float, int]]:
    """Waypoints for right-column pins ``(num_cols+2) … (2*num_cols)``, mirrored in X.

    Same ``y_neck``, pitch, and count as ``neck_stem_top_straddle_waypoints_mil`` (left).
    No waypoint for pin ``num_cols+1`` (J3 top / first right column), analogous to pin 1 left.
    """
    left = neck_stem_top_straddle_waypoints_mil(p)
    if not left:
        return []
    nc = p.num_cols
    _, x_ln, x_rn, _ = stem_layout_mil(p)
    pr = pad_clearance_radius_mil(HOLE_R)
    inset = (
        pr
        + MARKER_RADIUS_MIL
        + _EDGE_GAP_MIL
        + NECK_WAYPOINT_STRADDLE_SQUEEZE_MIL
    )
    x_lo = x_ln + inset
    x_hi = x_rn - inset
    out: list[tuple[float, float, int]] = []
    for x_m, y_m, seq_l in left:
        x_mir = x_lo + x_hi - x_m
        seq_r = seq_l + nc
        out.append((x_mir, y_m, seq_r))
    return out


def neck_stem_left_net_trace_polyline_mil(
    p: BoardParams,
    seq: int,
) -> list[tuple[float, float]] | None:
    """Three mil-space points for left stem net ``seq`` (2..num_cols), or ``None``.

    Path: vertical from neck waypoint to bend below pin ``seq−1``, then straight to
    ``(x_ln, pin seq)``.
    """
    if seq < 2 or seq > p.num_cols:
        return None
    wpts = neck_stem_top_straddle_waypoints_mil(p)
    if not wpts:
        return None
    _, x_ln, _, _ = stem_layout_mil(p)
    for x_m, y_m, s in wpts:
        if s != seq:
            continue
        py = stem_pin_y_mil(seq - 1, p)
        y_bend = stem_pin_y_mil(seq - 2, p) + NECK_BEND_BELOW_PRIOR_PIN_MIL
        return [(x_m, y_m), (x_m, y_bend), (x_ln, py)]
    return None


def neck_stem_right_net_trace_polyline_mil(
    p: BoardParams,
    seq: int,
) -> list[tuple[float, float]] | None:
    """Three mil-space points for right stem net ``seq`` (num_cols+2..2*num_cols), or ``None``."""
    nc = p.num_cols
    if seq < nc + 2 or seq > 2 * nc:
        return None
    wpts = neck_stem_top_straddle_waypoints_right_mil(p)
    if not wpts:
        return None
    _, _, x_rn, _ = stem_layout_mil(p)
    for x_m, y_m, s in wpts:
        if s != seq:
            continue
        row_idx = seq - nc - 1
        py = stem_pin_y_mil(row_idx, p)
        y_bend = stem_pin_y_mil(row_idx - 1, p) + NECK_BEND_BELOW_PRIOR_PIN_MIL
        return [(x_m, y_m), (x_m, y_bend), (x_rn, py)]
    return None


def wide_head_j3_row_column_vertical_trace_points_mil(
    p: BoardParams,
) -> list[tuple[int, list[tuple[float, float]]]]:
    """Per column: polyline along J3 / row-B stack at ``head_column_x_mil``, same net."""
    ys = wide_head_y_rows_mil(p=p, from_row_a=False)
    if len(ys) < 2:
        return []
    out: list[tuple[int, list[tuple[float, float]]]] = []
    for col in range(p.num_cols):
        x = head_column_x_mil(col, p)
        pts = [(x, y) for y in ys]
        out.append((col, pts))
    return out


def right_stem_straddle_or_pin_target_mil(
    p: BoardParams, seq: int
) -> tuple[float, float] | None:
    """J3 head→stem join endpoint: straddle waypoint if present, else right stem pin center.

    ``seq`` is stem net id ``num_cols+1 … 2*num_cols``. No straddle waypoint for
    ``num_cols+1``; use ``(x_rn, stem_pin_y_mil(col))`` with ``col = seq - num_cols - 1``.
    """
    nc = p.num_cols
    if seq < nc + 1 or seq > 2 * nc:
        return None
    wpts = neck_stem_top_straddle_waypoints_right_mil(p)
    by_seq = {s: (x, y) for x, y, s in wpts}
    if seq in by_seq:
        return by_seq[seq]
    col = seq - nc - 1
    _, _, x_rn, _ = stem_layout_mil(p)
    return (x_rn, stem_pin_y_mil(col, p))
