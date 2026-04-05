#!/usr/bin/env python3
"""
Emit an SVG sketch of the two-layer row reverser: head pads → edge vias → gap vias.

Coordinates are **mil** (+Y down), matching ``adapter_gen.geometry`` (breadboard **0.1"**
column pitch = **100 mil**).

Column index i matches docs/top-row-reverser-routing.md:
  i = 0 … n-1, i = 0 is the right column (largest X), i = n-1 is the left.

  - Cyan: outer layer — diagonal from pad at column i to edge via V_i.
  - Red: inner layer — **i ≤ n−3**: **horizontal** from **V_i** only **until** **intersection** with
    **J6** cyan (**column** **n−2**: **P_{n−2} → V_{n−2}**), then **straight** to **(gap x, y_v(i+1))**;
    inner **Y** = **y_v(i+1)**. If no valid intersection on the red span, **one diagonal** to the gap.
    **i = n−2**: **one straight diagonal** to **(gap x, y_v(n−1))** (horizontal leg length **0** at
    **J6** intersection). **Edge** vias unchanged.
  - Green: vias at endpoints. PTH holes use ``HOLE_R``; routing vias use ``via_r``.

Vertical spacing: **as tight as reasonable** — lane spacing ``dy = 2*via_r + trace_gap``.
The **first** lane **Y** is **below** the PTH row (**pad center + hole radius + trace/2 +
clearance**) so **red** traces and **vias** do not intersect pad holes. Override with
``--max-y-span`` to cap total stack height (then dy = span/(n-1)).

Usage (repo root):
  ./scripts/row_reverser_svg.py --columns 7
  ./scripts/row_reverser_svg.py --columns 22
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from adapter_gen.geometry import HOLE_R, PAD_SIZE, PITCH
except ImportError as e:
    raise SystemExit(
        f"Import adapter_gen from repo root (need geometry constants). {e}"
    ) from e

# Inner-layer routing via (drill) — smaller than PTH pad hole for illustration
_DEFAULT_VIA_R = min(8.0, HOLE_R * 0.4)
# Copper width for preview strokes (mil)
_TRACE_STROKE = 6.0
# Minimum gap between adjacent horizontal traces (mil)
_DEFAULT_TRACE_GAP = 8.0
# Edge via column: ~one pad diameter + neck past last pad center (mil)
_DEFAULT_EDGE_OFFSET = 2.0 * HOLE_R + 20.0
# Red horizontals + vias start below PTH holes (center + pad_r + stroke/2 + this gap)
_DEFAULT_NECK_CLEARANCE_MIL = 4.0


def _pad_label_j(i: int) -> str:
    """J1…Jn: J1 at i=0 (right), Jn at i=n−1 (left)."""
    return f"J{i + 1}"


def _intersect_x_horizontal_with_segment(
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


def emit_svg(
    n: int,
    *,
    pitch: float = PITCH,
    pad_r: float = HOLE_R,
    via_r: float = _DEFAULT_VIA_R,
    edge_offset: float = _DEFAULT_EDGE_OFFSET,
    y_pad: float = 0.0,
    y_min: float | None = None,
    neck_clearance_mil: float = _DEFAULT_NECK_CLEARANCE_MIL,
    trace_gap: float = _DEFAULT_TRACE_GAP,
    max_y_span: float | None = None,
) -> str:
    if n < 2:
        raise ValueError("columns must be >= 2")

    # Stack edge vias / red traces below pad hole bottoms so horizontals don't cross holes.
    trace_half = _TRACE_STROKE / 2.0
    y_first_lane = y_pad + pad_r + trace_half + neck_clearance_mil
    if y_min is None:
        y_min_eff = y_first_lane
    else:
        y_min_eff = max(y_min, y_first_lane)

    def x_pad(i: int) -> float:
        return (n - 1 - i) * pitch

    x_e = (n - 1) * pitch + edge_offset

    def x_inner_horizontal_end(i: int) -> float | None:
        if i == n - 1:
            return None
        j = n - 1 - i
        assert j >= 1
        return (x_pad(j - 1) + x_pad(j)) / 2

    # Vertical lane spacing: tight default, or squeezed to max_y_span
    if n <= 1:
        dy = 0.0
    elif max_y_span is not None:
        dy = max_y_span / (n - 1)
    else:
        dy = 2.0 * via_r + trace_gap
    y_max = y_min_eff + (n - 1) * dy

    def y_v(i: int) -> float:
        if n <= 1:
            return y_min_eff
        return y_min_eff + i * dy

    def y_inner_terminal(i: int) -> float:
        """Y for the gap (inner) end of layer B for column ``i`` (``i <= n-2``)."""
        if i == n - 2:
            return y_v(n - 1)
        return y_v(i + 1)

    margin = 100.0
    w = x_e + via_r + margin + 120
    h = y_max + pad_r + margin + 120
    ox = -margin
    w = round(w, 2)
    h = round(h, 2)

    cx_note = (w + 2 * ox) / 2 + ox
    font_px = max(18.0, min(48.0, pitch * 0.35))
    lbl_dy = pad_r * 0.35

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{ox} {-120} {w} {h}" '
        f'font-family="system-ui, Segoe UI, sans-serif" font-size="{font_px:.1f}">',
        f"  <title>Row reverser preview (mil): J1 right … J{n} left ({n} columns)</title>",
        "  <defs>",
        '    <style type="text/css"><![CDATA[',
        f"      .trace-cyan {{ fill: none; stroke: #6cf; stroke-width: {_TRACE_STROKE}; stroke-linecap: round; stroke-linejoin: round; }}",
        f"      .trace-red {{ fill: none; stroke: #e33; stroke-width: {_TRACE_STROKE}; stroke-linecap: round; stroke-linejoin: round; }}",
        f"      .via {{ fill: #284; stroke: #8f8; stroke-width: {max(1.0, _TRACE_STROKE * 0.25)}; }}",
        f"      .via-x {{ stroke: #efe; stroke-width: {max(0.8, via_r * 0.12)}; }}",
        f"      .pad {{ fill: #444; stroke: #888; stroke-width: {round(max(1.5, _TRACE_STROKE * 0.35), 2)}; }}",
        f"      .lbl {{ fill: #9cf; font-size: {font_px * 0.85:.1f}px; font-weight: 500; }}",
        "      .note { fill: #888; font-size: 11px; }",
        "      .dim { fill: #666; font-size: 10px; }",
        "    ]]></style>",
        "  </defs>",
        f'  <rect x="{ox}" y="-120" width="{w}" height="{h}" fill="#0a0a0a"/>',
        f'  <text x="{cx_note:.1f}" y="-100" text-anchor="middle" class="dim">'
        f"Units: mil — pitch {pitch:.0f} (0.1″), PTH r={pad_r:.0f}, via r={via_r:.1f}</text>",
        "  <!-- Layer B: red — horizontal to J6 cyan (i=n-2), then to gap; i=n-2 diagonal -->",
        '  <g class="trace-red" aria-label="inner layer horizontals">',
    ]

    # J6 cyan (second column from left): P_{n-2} -> V_{n-2} — shared horizontal stop for i <= n-3.
    xa_j6, ya_j6 = x_pad(n - 2), y_pad
    xb_j6, yb_j6 = x_e, y_v(n - 2)

    for i in range(n):
        x_end = x_inner_horizontal_end(i)
        if x_end is None:
            continue
        y_e = y_v(i)
        y_i = y_inner_terminal(i)
        if i == n - 2:
            lines.append(
                f'    <polyline points="{x_e:.2f},{y_e:.2f} {x_end:.2f},{y_i:.2f}"/>'
            )
        elif abs(y_i - y_e) < 1e-9:
            lines.append(
                f'    <polyline points="{x_e:.2f},{y_e:.2f} {x_end:.2f},{y_e:.2f}"/>'
            )
        else:
            xp = _intersect_x_horizontal_with_segment(
                y_e, xa_j6, ya_j6, xb_j6, yb_j6
            )
            x_lo, x_hi = (x_end, x_e) if x_end < x_e else (x_e, x_end)
            use_bend = xp is not None and x_lo - 1e-3 <= xp <= x_hi + 1e-3
            if use_bend:
                lines.append(
                    f'    <polyline points="{x_e:.2f},{y_e:.2f} {xp:.2f},{y_e:.2f} '
                    f'{x_end:.2f},{y_i:.2f}"/>'
                )
            else:
                lines.append(
                    f'    <polyline points="{x_e:.2f},{y_e:.2f} {x_end:.2f},{y_i:.2f}"/>'
                )

    lines.append("  </g>")
    lines.append('  <!-- Layer A: cyan diagonals -->')
    lines.append('  <g class="trace-cyan" aria-label="outer layer diagonals">')

    for i in range(n):
        xp = x_pad(i)
        y = y_v(i)
        lines.append(
            f'    <polyline points="{xp:.2f},{y_pad:.2f} {x_e:.2f},{y:.2f}"/>'
        )

    lines.append("  </g>")

    lines.append('  <g aria-label="head pads">')
    for i in range(n):
        x = x_pad(i)
        lines.append(
            f'    <circle cx="{x:.2f}" cy="{y_pad:.2f}" r="{pad_r}" class="pad"/>'
        )
        lines.append(
            f'    <text x="{x:.2f}" y="{y_pad + lbl_dy:.2f}" text-anchor="middle" class="lbl">'
            f"{_pad_label_j(i)}</text>"
        )
    lines.append("  </g>")

    vx = max(3.0, via_r * 0.45)
    lines.append('  <g aria-label="vias" stroke-linecap="round">')
    for i in range(n):
        ye = y_v(i)
        inner_x = x_inner_horizontal_end(i)
        if inner_x is None:
            pts = ((x_e, ye),)
        else:
            yi = y_inner_terminal(i)
            pts = ((x_e, ye), (inner_x, yi))
        for x, y in pts:
            lines.append(f'    <g transform="translate({x:.2f},{y:.2f})">')
            lines.append(f'      <circle r="{via_r}" class="via"/>')
            lines.append(
                f'      <line x1="{-vx:.2f}" y1="0" x2="{vx:.2f}" y2="0" class="via-x"/>'
            )
            lines.append(
                f'      <line x1="0" y1="{-vx:.2f}" x2="0" y2="{vx:.2f}" class="via-x"/>'
            )
            lines.append("    </g>")
    lines.append("  </g>")

    span_note = f"dy={dy:.1f} mil" + (
        f", max_y_span={max_y_span:.0f}" if max_y_span is not None else f", trace_gap={trace_gap:.0f}"
    )
    lines.append(
        f'  <text x="{cx_note:.1f}" y="-78" text-anchor="middle" class="note">'
        f"{n} columns — J1 right … J{n} left. First lane y={y_min_eff:.1f} mil (below holes). "
        f"{span_note}.</text>"
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Row reverser preview SVG (mil, 0.1″ pitch): red horizontal to J6 cyan (i=n-2), "
            "then to gap; i=n-2 one diagonal; geometry from adapter_gen."
        )
    )
    p.add_argument(
        "--columns",
        type=int,
        required=True,
        metavar="N",
        help="Number of columns (adapter N/2, e.g. 22).",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help="Output path (default: out/preview/row-reverser-<N>.svg).",
    )
    p.add_argument(
        "--pitch",
        type=float,
        default=PITCH,
        help=f"Column pitch in mil (default {PITCH} = 0.1″).",
    )
    p.add_argument(
        "--via-r",
        type=float,
        default=_DEFAULT_VIA_R,
        metavar="MIL",
        help=f"Routing via radius in mil (default {_DEFAULT_VIA_R:.1f}).",
    )
    p.add_argument(
        "--trace-gap",
        type=float,
        default=_DEFAULT_TRACE_GAP,
        metavar="MIL",
        help=f"Minimum gap between adjacent horizontal traces, mil (default {_DEFAULT_TRACE_GAP:.0f}).",
    )
    p.add_argument(
        "--max-y-span",
        type=float,
        default=None,
        metavar="MIL",
        help="If set, lane pitch dy = span/(n-1), overriding trace-gap-based dy.",
    )
    p.add_argument(
        "--neck-clearance",
        type=float,
        default=_DEFAULT_NECK_CLEARANCE_MIL,
        metavar="MIL",
        help=f"Gap (mil) from pad hole bottom to first red/via row (default {_DEFAULT_NECK_CLEARANCE_MIL}).",
    )
    args = p.parse_args()

    out = args.output
    if out is None:
        out = _REPO_ROOT / "out" / "preview" / f"row-reverser-{args.columns}.svg"

    svg = emit_svg(
        args.columns,
        pitch=args.pitch,
        via_r=args.via_r,
        trace_gap=args.trace_gap,
        max_y_span=args.max_y_span,
        neck_clearance_mil=args.neck_clearance,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(out.resolve())


if __name__ == "__main__":
    main()
