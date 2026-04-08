"""Silk label overlay for SVG preview (mil space, +Y down).

Baked JSON paths use EasyEDA file units (coordinate in path = mil/10); placement matches
``scripts/generate_easyeda_adapter_pcb.py`` offsets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from adapter_gen.geometry import (
    PAD_SIZE,
    SILK_OFF_HEAD_MIL,
    SILK_CONNECTOR_REF_MARGIN_PAST_PAD_MIL,
    SILK_CONNECTOR_REF_STEM_STRADDLE_PAST_PAD_MIL,
    Y_W_ROW_A,
    BoardParams,
    head_column_x_mil,
    stem_layout_mil,
    stem_pin_y_mil,
    stem_silk_x_mil_left_column,
    stem_silk_x_mil_right_column,
    wide_head_y_rows_mil,
)
from adapter_gen.silk_bake import default_devkitc1_gpio_json_name

# Head silk: rotate baked horizontal glyphs so label width runs along +Y (column direction),
# avoiding overlap along the row. CCW in file space (y-down); -90° maps +X extent toward +Y.
HEAD_SILK_ROTATE_DEG = -90.0


def rotate_silk_path_d(d: str, deg: float) -> str:
    """Rotate ``d`` around origin in EasyEDA file units (+X right, +Y down).

    ``deg`` is counter-clockwise in the y-down plane (θ=-90° turns horizontal text vertical).
    """
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    parts = d.split()
    out: list[str] = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok == "Z":
            out.append("Z")
            i += 1
            continue
        if tok in ("M", "L"):
            out.append(tok)
            x = float(parts[i + 1])
            y = float(parts[i + 2])
            xp = x * c + y * s
            yp = -x * s + y * c
            out.append(f"{xp:.2f}")
            out.append(f"{yp:.2f}")
            i += 3
            continue
        raise ValueError(f"unexpected path token {tok!r} in silk path")
    return " ".join(out)


def translate_silk_path_d_to_mil(d: str, cx_mil: float, cy_mil: float) -> str:
    """Translate baked path (file units, origin-centered) to absolute ``d`` in mil."""
    cx_f = cx_mil / 10.0
    cy_f = cy_mil / 10.0
    parts = d.split()
    out: list[str] = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok == "Z":
            out.append("Z")
            i += 1
            continue
        if tok in ("M", "L"):
            out.append(tok)
            x = (float(parts[i + 1]) + cx_f) * 10.0
            y = (float(parts[i + 2]) + cy_f) * 10.0
            out.append(f"{x:.2f}")
            out.append(f"{y:.2f}")
            i += 3
            continue
        raise ValueError(f"unexpected path token {tok!r} in silk path")
    return " ".join(out)


def _above_stem_board_id_center_mil(p: BoardParams) -> tuple[float, float]:
    xc, _, _, y_stem_top = stem_layout_mil(p)
    pad_half = PAD_SIZE / 2.0
    y_mid = y_stem_top - pad_half - 120.0
    return xc, y_mid


def load_silk_label_data(
    silk_dir: Path,
    mode: str,
    p: BoardParams,
    *,
    silk_gpio_paths_json: str | None = None,
) -> tuple[dict[str, str], list[str], list[str], list[dict[str, str]] | None]:
    """Return paths map, j1 labels, j3 labels, optional board_id line dicts."""
    nc = p.num_cols
    if mode == "devkitc1":
        name = silk_gpio_paths_json or default_devkitc1_gpio_json_name()
        path = silk_dir / name
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        paths_map: dict[str, str] = raw["paths"]
        j1: list[str] = list(raw["j1_order"][:nc])
        j3: list[str] = list(raw["j3_order"][:nc])
        bid = raw.get("board_id_silk") or {}
        lines_raw = bid.get("lines")
        lines: list[dict[str, str]] | None = (
            lines_raw if isinstance(lines_raw, list) else None
        )
        return paths_map, j1, j3, lines
    if mode == "numeric":
        path = silk_dir / "numeric_silk_paths.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        paths_map = raw["paths"]
        j1 = [str(i) for i in range(1, nc + 1)]
        j3 = [str(i) for i in range(1, nc + 1)]
        return paths_map, j1, j3, None
    raise ValueError(f"unknown silk mode: {mode!r}")


def paths_map_with_connector_ref_glyphs(
    paths_map: dict[str, str],
    silk_dir: Path,
) -> dict[str, str]:
    """Ensure ``J1`` and ``J3`` path entries for connector refs (GPIO bakes omit them pre-fix)."""
    if "J1" in paths_map and "J3" in paths_map:
        return paths_map
    num = (silk_dir / "numeric_silk_paths.json").resolve()
    if not num.is_file():
        return paths_map
    raw = json.loads(num.read_text(encoding="utf-8"))
    extra = raw.get("paths")
    if not isinstance(extra, dict):
        return paths_map
    out = dict(paths_map)
    if "J1" in extra:
        out["J1"] = extra["J1"]
    if "J3" in extra:
        out["J3"] = extra["J3"]
    return out


def numeric_connector_header_centers_mil(
    p: BoardParams,
) -> list[tuple[str, float, float]]:
    """(label, cx_mil, cy_mil) for numeric silk: **outside** pads, not on hole centers.

    Anchor = pad center ± (pad radius + ``SILK_CONNECTOR_REF_MARGIN_PAST_PAD_MIL``) in the
    outward direction: head col 0 **+X**, row A **−Y**, row B **+Y**.

    Stem: **Y** = pin-1 row (``stem_pin_y_mil(0)``). J1 **X** = **−X** past the J1-side pin-1 pad
    (``x_ln`` − pad radius − ``SILK_CONNECTOR_REF_STEM_STRADDLE_PAST_PAD_MIL``). J3 **X** = **+X**
    past the J3-side pin-1 pad (mirror). Same past-pad distance as each other; tighter than
    wide-head margin.
    """
    m = SILK_CONNECTOR_REF_MARGIN_PAST_PAD_MIL
    pr = PAD_SIZE / 2.0
    delta = pr + m
    m_stem = SILK_CONNECTOR_REF_STEM_STRADDLE_PAST_PAD_MIL
    ys_a = wide_head_y_rows_mil(p=p, from_row_a=True)
    ys_b = wide_head_y_rows_mil(p=p, from_row_a=False)
    x_pin1_out = head_column_x_mil(0, p) + delta
    cy_j1_head = ys_a[0] - delta
    cy_j3_head = ys_b[0] + delta
    _, x_ln, x_rn, _ = stem_layout_mil(p)
    cx_j1_stem_out = x_ln - pr - m_stem
    cx_j3_stem_out = x_rn + pr + m_stem
    cy_stem_pin1 = stem_pin_y_mil(0, p)
    return [
        ("J1", x_pin1_out, cy_j1_head),
        ("J3", x_pin1_out, cy_j3_head),
        ("J1", cx_j1_stem_out, cy_stem_pin1),
        ("J3", cx_j3_stem_out, cy_stem_pin1),
    ]


def numeric_connector_ref_path_elements_mil(
    p: BoardParams,
    paths_map: dict[str, str],
) -> list[str]:
    """J1/J3 connector ref paths (numeric or devkitc GPIO silk); same centers as EasyEDA headers."""
    if "J1" not in paths_map or "J3" not in paths_map:
        return []
    out: list[str] = []
    for lab, cx_m, cy_m in numeric_connector_header_centers_mil(p):
        d0 = paths_map[lab]
        out.append(translate_silk_path_d_to_mil(d0, cx_m, cy_m))
    return out


def silk_path_elements_mil(
    p: BoardParams,
    paths_map: dict[str, str],
    j1: list[str],
    j3: list[str],
    *,
    vertical_head: bool = False,
) -> list[str]:
    """``d`` strings in mil for each per-pin silk path (head + stem).

    When ``vertical_head`` is True (devkitc1), head row glyphs are rotated so they do not
    overlap along X; stem labels stay horizontal.

    Numeric J1/J3 connector refs are **not** included — emit those separately via
    ``numeric_connector_ref_path_elements_mil`` after routing overlays in SVG preview so they
    are not covered by trace strokes.
    """
    nc = p.num_cols
    yb = p.y_row_b
    out: list[str] = []

    def _head_d(lab: str) -> str:
        d0 = paths_map[lab]
        if vertical_head:
            d0 = rotate_silk_path_d(d0, HEAD_SILK_ROTATE_DEG)
        return d0

    for i in range(nc):
        lab = j1[i]
        cx = head_column_x_mil(i, p)
        cy = Y_W_ROW_A - SILK_OFF_HEAD_MIL
        out.append(translate_silk_path_d_to_mil(_head_d(lab), cx, cy))
    for i in range(nc):
        lab = j3[i]
        cx = head_column_x_mil(i, p)
        cy = yb + SILK_OFF_HEAD_MIL
        out.append(translate_silk_path_d_to_mil(_head_d(lab), cx, cy))
    cx_left = stem_silk_x_mil_left_column(p)
    cx_right = stem_silk_x_mil_right_column(p)
    for i in range(nc):
        lab = j1[i]
        cy = stem_pin_y_mil(i, p)
        out.append(translate_silk_path_d_to_mil(paths_map[lab], cx_left, cy))
    for i in range(nc):
        lab = j3[i]
        cy = stem_pin_y_mil(i, p)
        out.append(translate_silk_path_d_to_mil(paths_map[lab], cx_right, cy))
    return out


def board_id_path_elements_mil(
    p: BoardParams,
    lines: list[dict[str, str]],
) -> list[str]:
    """Two-line (or N-line) kit ID above stem (each row has ``text`` + ``d`` from bake)."""
    cx_mil, y_mid_mil = _above_stem_board_id_center_mil(p)
    n = len(lines)
    if n == 0:
        return []
    if n == 1:
        offs = [0.0]
    else:
        gap_mil = 64.0
        total = gap_mil * (n - 1)
        offs = [-total / 2.0 + i * gap_mil for i in range(n)]
    ds: list[str] = []
    for i, row in enumerate(lines):
        d0 = row["d"]
        cy = y_mid_mil + offs[i]
        ds.append(translate_silk_path_d_to_mil(d0, cx_mil, cy))
    return ds
