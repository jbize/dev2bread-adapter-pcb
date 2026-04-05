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
    Y_W_ROW_A,
    BoardParams,
    head_column_x_mil,
    stem_layout_mil,
    stem_pin_y_mil,
    stem_silk_x_mil_left_column,
    stem_silk_x_mil_right_column,
)

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
) -> tuple[dict[str, str], list[str], list[str], list[dict[str, str]] | None]:
    """Return paths map, j1 labels, j3 labels, optional board_id line dicts."""
    nc = p.num_cols
    if mode == "devkitc1":
        path = silk_dir / "devkitc1_gpio_silk_paths.json"
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
        j3 = [str(nc + i) for i in range(1, nc + 1)]
        return paths_map, j1, j3, None
    raise ValueError(f"unknown silk mode: {mode!r}")


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
