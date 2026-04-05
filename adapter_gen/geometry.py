"""Board layout in **mil** (+Y down).

Conventions align with ``scripts/generate_easyeda_adapter_pcb.py``.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Literal, Sequence

# 2D point in mil (+Y down), same as legacy scripts.
Point2 = tuple[float, float]
PolygonMil = Sequence[Point2]

# --- Defaults (mil) — align with scripts/generate_easyeda_adapter_pcb.py ---
PITCH = 100.0  # 0.1"
NARROW_ROW_GAP = 500.0  # breadboard straddle
WIDE_ROW_GAP = 1100.0  # ~1.1" between wide head rows
NECK_GAP = 500.0  # gap below wide rows before stem block
X0 = 400.0  # leftmost wide-column reference
Y_W_ROW_A = 280.0  # wide row A (nets 1..N/2), smaller Y = "top" of head
PAD_SIZE = 55.0
HOLE_R = 20.0  # drill / pad hole radius for preview
MARGIN = 150.0
HEAD_OUTLINE_EXTRA = 160.0
STEM_OUTLINE_MARGIN = 130.0
# Wide-head silk (devkitc1 vertical): anchor offset from wide-row Y center toward board edge.
# Tight to pads: just enough that rotated glyphs do not sit on drill/pad annuli (~PAD/2 + hole).
SILK_OFF_HEAD_MIL = 110.0
# Half of max span along Y of a rotated horizontal glyph (mil); ~max label width at bake size.
SILK_VERTICAL_HALF_EXTENT_MIL = 75.0
# Board outline corner fillet (mil); clamped to ~half the shortest edge.
BOARD_CORNER_RADIUS_MIL = 50.0


@dataclass(frozen=True)
class BoardParams:
    """One build configuration."""

    n_pins: int
    n_rows_top: int  # 1..4: socket depth from row A toward gap
    # 1..4: socket depth from row B toward gap
    n_rows_bottom: int

    def __post_init__(self) -> None:
        if self.n_pins % 2 != 0 or not (14 <= self.n_pins <= 44):
            raise ValueError("n_pins must be even and in [14, 44]")
        if not (1 <= self.n_rows_top <= 4) or not (1 <= self.n_rows_bottom <= 4):
            raise ValueError("n_rows_top and n_rows_bottom must be in 1..4")

    @property
    def num_cols(self) -> int:
        return self.n_pins // 2

    @property
    def y_row_b(self) -> float:
        return Y_W_ROW_A + WIDE_ROW_GAP


def stem_layout_mil(p: BoardParams) -> tuple[float, float, float, float]:
    """xc, x_left_narrow, x_right_narrow, y_stem_top (first stem row)."""
    nc = p.num_cols
    xc = X0 + (nc - 1) * PITCH / 2.0
    x_ln = xc - NARROW_ROW_GAP / 2.0
    x_rn = xc + NARROW_ROW_GAP / 2.0
    y_stem_top = p.y_row_b + NECK_GAP
    return xc, x_ln, x_rn, y_stem_top


def stem_silk_x_mil_left_column(p: BoardParams) -> float:
    """X center (mil) for stem silk labels on the J1 side (straddle gap, right of left holes)."""
    xc, x_ln, _, _ = stem_layout_mil(p)
    return (x_ln + xc) / 2.0


def stem_silk_x_mil_right_column(p: BoardParams) -> float:
    """X center (mil) for stem silk on the J3 side (straddle gap, left of right holes)."""
    xc, _, x_rn, _ = stem_layout_mil(p)
    return (xc + x_rn) / 2.0


def head_column_x_mil(i: int, p: BoardParams) -> float:
    """Column index i in 0..num_cols-1 (same net ordering as legacy)."""
    return X0 + (p.num_cols - 1 - i) * PITCH


def stem_pin_y_mil(i: int, p: BoardParams) -> float:
    _, _, _, y0 = stem_layout_mil(p)
    return y0 + i * PITCH


def wide_head_y_rows_mil(*, p: BoardParams, from_row_a: bool) -> list[float]:
    """Y centers for socket depth on row-A or row-B side."""
    n = p.n_rows_top if from_row_a else p.n_rows_bottom
    if from_row_a:
        return [Y_W_ROW_A + k * PITCH for k in range(n)]
    return [p.y_row_b - k * PITCH for k in range(n)]


def header_branding_region_mil(p: BoardParams) -> tuple[float, float, float, float]:
    """Blank strip between innermost wide-head rows (mil): ``(left, top, width, height)``.

    Innermost rows are the socket rows closest to the gap between J1-side and J3-side
    blocks (+Y down). The rectangle is inset from pad centers by ``PAD_SIZE/2``.
    """
    ys_a = wide_head_y_rows_mil(p=p, from_row_a=True)
    ys_b = wide_head_y_rows_mil(p=p, from_row_a=False)
    y_inner_a = ys_a[-1]
    y_inner_b = ys_b[-1]
    pad_half = PAD_SIZE / 2.0
    top = y_inner_a + pad_half
    bottom = y_inner_b - pad_half
    if bottom <= top + 1e-6:
        y_mid = 0.5 * (y_inner_a + y_inner_b)
        top = y_mid - 50.0
        bottom = y_mid + 50.0
    height = bottom - top

    xs = [head_column_x_mil(i, p) for i in range(p.num_cols)]
    x_min = min(xs) - pad_half
    x_max = max(xs) + pad_half
    width = x_max - x_min
    left = x_min
    return (left, top, width, height)


def board_outline_polygon_mil(p: BoardParams) -> list[Point2]:
    """Closed T outline (CCW), sharp corners — same vertices as legacy."""
    _, x_ln, x_rn, y_stem_top = stem_layout_mil(p)
    nc = p.num_cols
    x_left = X0 - MARGIN
    x_right = X0 + (nc - 1) * PITCH + MARGIN
    x_head_l = x_left - HEAD_OUTLINE_EXTRA
    x_head_r = x_right + HEAD_OUTLINE_EXTRA
    x_stem_l = x_ln - STEM_OUTLINE_MARGIN
    x_stem_r = x_rn + STEM_OUTLINE_MARGIN
    # Extend FR4 above row A so vertical silk fits between outline edge and pad holes.
    y_top = (
        Y_W_ROW_A
        - SILK_OFF_HEAD_MIL
        - SILK_VERTICAL_HALF_EXTENT_MIL
        - MARGIN
    )
    y_bot = stem_pin_y_mil(nc - 1, p) + MARGIN
    y_neck = y_stem_top - 50.0
    return [
        (x_head_l, y_top),
        (x_head_r, y_top),
        (x_head_r, y_neck),
        (x_stem_r, y_neck),
        (x_stem_r, y_bot),
        (x_stem_l, y_bot),
        (x_stem_l, y_neck),
        (x_head_l, y_neck),
    ]


def _min_edge_length_mil(poly: PolygonMil) -> float:
    n = len(poly)
    best = float("inf")
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        best = min(best, math.hypot(x1 - x0, y1 - y0))
    return best


def _unit(vx: float, vy: float) -> tuple[float, float]:
    h = math.hypot(vx, vy)
    if h < 1e-12:
        raise ValueError("zero edge in outline")
    return (vx / h, vy / h)


def _effective_corner_radius_mil(poly: PolygonMil, r: float) -> float:
    """Keep fillets inside each edge (orthogonal 90° corners, ~r from each vertex)."""
    m = _min_edge_length_mil(poly)
    # Need length >= 2*r on every edge for two adjacent fillets.
    r_max = max(0.0, 0.5 * m - 1.0)
    return min(r, r_max)


def _point_in_polygon_mil(poly: PolygonMil, x: float, y: float) -> bool:
    """Even-odd test; poly closed CCW, orthogonal outline only."""
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            x_int = (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi
            if x < x_int:
                inside = not inside
        j = i
    return inside


def _vertex_turn_z(p_prev: Point2, p0: Point2, p_next: Point2) -> float:
    """Signed z-component of edge_in × edge_out; CCW simple poly → convex > 0, concave < 0."""
    e_in = (p0[0] - p_prev[0], p0[1] - p_prev[1])
    e_out = (p_next[0] - p0[0], p_next[1] - p0[1])
    return e_in[0] * e_out[1] - e_in[1] * e_out[0]


def _arc_center_orthogonal(
    t1: Point2,
    v_in: tuple[float, float],
    t2: Point2,
    r: float,
    *,
    poly: PolygonMil,
    p_prev: Point2,
    p0: Point2,
    p_next: Point2,
) -> Point2:
    """Center of the r-radius arc from T1 to T2; v_in is unit along edge into the corner.

    Convex corners (outer): center lies **inside** the board polygon.
    Concave corners (re-entrant): center lies **outside** (in the notch).
    """
    n1 = (-v_in[1], v_in[0])
    n2 = (v_in[1], -v_in[0])
    candidates: list[Point2] = []
    for nx, ny in (n1, n2):
        nu = _unit(nx, ny)
        c = (t1[0] + nu[0] * r, t1[1] + nu[1] * r)
        d = math.hypot(t2[0] - c[0], t2[1] - c[1])
        if abs(d - r) < 1e-3:
            candidates.append(c)
    if not candidates:
        raise ValueError("failed to place arc center (check outline / radius)")
    turn = _vertex_turn_z(p_prev, p0, p_next)
    convex = turn > 0.0
    for c in candidates:
        ins = _point_in_polygon_mil(poly, c[0], c[1])
        if convex and ins:
            return c
        if not convex and not ins:
            return c
    return candidates[0]


@dataclass(frozen=True)
class _OutlineFillet:
    """One rounded 90° corner: tangent points ``t1``→``t2``, arc ``center``, SVG sweep."""

    t1: Point2
    t2: Point2
    center: Point2
    radius: float
    sweep_svg: Literal[0, 1]


def _svg_arc_sweep_y_down(t1: Point2, t2: Point2, c: Point2) -> int:
    """Sweep flag for the short arc t1→t2 in SVG user space (+Y down)."""
    ax, ay = t1[0] - c[0], t1[1] - c[1]
    bx, by = t2[0] - c[0], t2[1] - c[1]
    det = ax * by - ay * bx
    return 1 if det > 0 else 0


def _outline_fillets(poly: list[Point2], r: float) -> list[_OutlineFillet]:
    """Fillet geometry for every vertex of the orthogonal T outline."""
    n = len(poly)
    out: list[_OutlineFillet] = []
    for i in range(n):
        p_prev = poly[i - 1]
        p0 = poly[i]
        p_next = poly[(i + 1) % n]
        v_in = _unit(p0[0] - p_prev[0], p0[1] - p_prev[1])
        v_out = _unit(p_next[0] - p0[0], p_next[1] - p0[1])
        t1 = (p0[0] - v_in[0] * r, p0[1] - v_in[1] * r)
        t2 = (p0[0] + v_out[0] * r, p0[1] + v_out[1] * r)
        center = _arc_center_orthogonal(
            t1,
            v_in,
            t2,
            r,
            poly=poly,
            p_prev=p_prev,
            p0=p0,
            p_next=p_next,
        )
        sweep = _svg_arc_sweep_y_down(t1, t2, center)
        out.append(_OutlineFillet(t1, t2, center, r, sweep))
    return out


def _normalize_quarter_arc_delta(delta: complex) -> float:
    """``cmath.phase(v/u)`` for 90° corners may be ±π/2 or ±3π/2; keep the short ±π/2 turn."""
    d = cmath.phase(delta)
    while d <= -math.pi:
        d += 2 * math.pi
    while d > math.pi:
        d -= 2 * math.pi
    if abs(abs(d) - 3 * math.pi / 2) < 0.06:
        d = -math.copysign(math.pi / 2, d)
    return d


def _arc_polyline_points(
    t1: Point2,
    t2: Point2,
    c: Point2,
    r: float,
    nseg: int,
) -> list[Point2]:
    """``nseg`` straight segments (``nseg+1`` points) along the short arc from ``t1`` to ``t2``."""
    z1 = complex(t1[0] - c[0], t1[1] - c[1])
    z2 = complex(t2[0] - c[0], t2[1] - c[1])
    u = z1 / abs(z1)
    v = z2 / abs(z2)
    delta = _normalize_quarter_arc_delta(v / u)
    out: list[Point2] = []
    for k in range(nseg + 1):
        s = k / nseg
        z = u * cmath.exp(1j * s * delta)
        out.append((c[0] + r * z.real, c[1] + r * z.imag))
    return out


def board_outline_polyline_mil(
    p: BoardParams,
    *,
    corner_radius_mil: float = BOARD_CORNER_RADIUS_MIL,
    arc_segments: int = 8,
) -> list[Point2]:
    """Closed board outline as a dense polyline (mil) for tools that only support line segments.

    Corners are 90° circular fillets with radius ``corner_radius_mil``; each fillet is split into
    ``arc_segments`` chords (default 8 ≈ 11.25° per step).
    """
    poly = board_outline_polygon_mil(p)
    r = _effective_corner_radius_mil(poly, corner_radius_mil)
    if r <= 0.0:
        return list(poly)

    eps = 1e-6
    pts: list[Point2] = []

    def append_distinct(xy: Point2) -> None:
        if not pts or (
            abs(pts[-1][0] - xy[0]) > eps or abs(pts[-1][1] - xy[1]) > eps
        ):
            pts.append(xy)

    for fil in _outline_fillets(poly, r):
        for q in _arc_polyline_points(
            fil.t1, fil.t2, fil.center, fil.radius, arc_segments
        ):
            append_distinct(q)

    return pts


def board_outline_svg_path_d(
    p: BoardParams, *, corner_radius_mil: float = BOARD_CORNER_RADIUS_MIL
) -> str:
    """Closed board outline as SVG path ``d`` with circular arc fillets (mil space).

    Orthogonal T polygon only; interior is CCW; arcs use ``A`` with rx = ry = r.
    """
    poly = board_outline_polygon_mil(p)
    r = _effective_corner_radius_mil(poly, corner_radius_mil)
    if r <= 0.0:
        parts = [f"M {poly[0][0]:.2f} {poly[0][1]:.2f}"]
        for x, y in poly[1:]:
            parts.append(f"L {x:.2f} {y:.2f}")
        parts.append("Z")
        return " ".join(parts)

    parts: list[str] = []
    for i, fil in enumerate(_outline_fillets(poly, r)):
        if i == 0:
            parts.append(f"M {fil.t1[0]:.2f} {fil.t1[1]:.2f}")
        else:
            parts.append(f"L {fil.t1[0]:.2f} {fil.t1[1]:.2f}")
        parts.append(
            f"A {fil.radius:.2f} {fil.radius:.2f} 0 0 {fil.sweep_svg} "
            f"{fil.t2[0]:.2f} {fil.t2[1]:.2f}"
        )

    parts.append("Z")
    return " ".join(parts)


def all_pad_centers_mil(p: BoardParams) -> list[tuple[float, float, int]]:
    """Each PTH: ``(x, y, net_index)`` with net_index 1..n_pins."""
    pts: list[tuple[float, float, int]] = []
    ys_a = wide_head_y_rows_mil(p=p, from_row_a=True)
    ys_b = wide_head_y_rows_mil(p=p, from_row_a=False)
    for col in range(p.num_cols):
        x = head_column_x_mil(col, p)
        net_lo = col + 1
        net_hi = p.num_cols + col + 1
        for y in ys_a:
            pts.append((x, y, net_lo))
        for y in ys_b:
            pts.append((x, y, net_hi))
    _, x_ln, x_rn, _ = stem_layout_mil(p)
    for i in range(p.num_cols):
        y = stem_pin_y_mil(i, p)
        n1 = i + 1
        n2 = p.num_cols + i + 1
        pts.append((x_ln, y, n1))
        pts.append((x_rn, y, n2))
    return pts


def bounds_mil(
    p: BoardParams, *, pad: float = 80.0
) -> tuple[float, float, float, float]:
    """min_x, min_y, max_x, max_y with padding around outline."""
    poly = board_outline_polygon_mil(p)
    xs = [a for a, _ in poly]
    ys = [b for _, b in poly]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
