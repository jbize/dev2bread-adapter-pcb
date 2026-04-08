"""Build baked silk path JSON (matplotlib TextPath → EasyEDA-style ``d`` strings).

Used by ``scripts/bake_devkitc_gpio_silk_paths.py``. Board-specific J1/J3 label lists live in
``resources/boards/<name>.toml`` under ``[silk_bake]``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomllib

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D

TARGET_H_FILE = 4.5  # ~45 mil letter height in EasyEDA file units (÷10 = mil)


def _path_to_d(path: MPath) -> str:
    """Flatten to M/L/Z only (EasyEDA-style), coordinates as in matplotlib space."""
    path = path.interpolated(10)
    verts = path.vertices
    codes = path.codes
    parts: list[str] = []
    i = 0
    while i < len(verts):
        c = int(codes[i])
        x, y = float(verts[i, 0]), float(verts[i, 1])
        if c == MPath.MOVETO:
            parts.append(f"M {x:.2f} {y:.2f}")
        elif c == MPath.LINETO:
            parts.append(f"L {x:.2f} {y:.2f}")
        elif c == MPath.CLOSEPOLY:
            parts.append("Z")
        elif c in (MPath.CURVE3, MPath.CURVE4):
            i += 1
            continue
        i += 1
    return " ".join(parts)


def text_to_path_at_origin(
    label: str, *, target_h: float = TARGET_H_FILE
) -> str:
    fp = FontProperties(family="DejaVu Sans", size=72)
    tp = TextPath((0, 0), label, prop=fp)
    path = MPath(tp.vertices, tp.codes)
    bb = path.get_extents()
    h = max(bb.height, 1e-6)
    scale = target_h / h
    cx = (bb.x0 + bb.x1) / 2.0
    cy = (bb.y0 + bb.y1) / 2.0
    trans = (
        Affine2D()
        .translate(-cx, -cy)
        .scale(scale, -scale)
    )
    p2 = path.transformed(trans)
    return _path_to_d(p2)


def paths_map_for_labels(labels: list[str]) -> dict[str, str]:
    uniq = sorted(set(labels), key=len)
    return {s: text_to_path_at_origin(s) for s in uniq}


def default_devkitc1_gpio_json_name() -> str:
    """Legacy default filename when no profile specifies ``[silk_bake].output``."""
    return "devkitc1_gpio_silk_paths.json"


def write_numeric_silk_json(out_path: Path, *, max_pin: int = 44) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    numeric_paths = {str(i): text_to_path_at_origin(str(i)) for i in range(1, max_pin + 1)}
    numeric_paths["J1"] = text_to_path_at_origin("J1")
    numeric_paths["J3"] = text_to_path_at_origin("J3")
    meta: dict[str, Any] = {
        "variant": f"numeric-1-{max_pin}-j1-j3",
        "note": (
            "Per-pin silk: J1 side 1..N and J3 side 1..N (independent numbering, devkit style). "
            "Plus connector refs J1 / J3 (head: past pad edges; stem: past pin-1 pads ±X same margin, "
            "Y = pin-1 row; see silk_preview.numeric_connector_header_centers_mil). "
            "Paths 1..max_pin are digit glyphs; N = adapter num_cols per row."
        ),
        "paths": numeric_paths,
    }
    out_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


def write_gpio_silk_json(
    out_path: Path,
    *,
    j1_order: list[str],
    j3_order: list[str],
    variant: str,
    source: str,
    note: str,
    board_id_lines: list[dict[str, Any]] | None,
) -> None:
    """Write vendor GPIO silk JSON (paths + j1/j3 order + optional board_id_silk)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    paths = paths_map_for_labels(j1_order + j3_order)
    # J1/J3 connector ref glyphs (same style as numeric); EasyEDA + SVG.
    paths["J1"] = text_to_path_at_origin("J1")
    paths["J3"] = text_to_path_at_origin("J3")
    meta: dict[str, Any] = {
        "variant": variant,
        "source": source,
        "j1_order": j1_order,
        "j3_order": j3_order,
        "note": note,
        "paths": paths,
    }
    if board_id_lines:
        meta["board_id_silk"] = {
            "placement": "above_stem",
            "note": (
                "Top silk between J3 row and stem pads (avoids J3 GPIO labels); "
                "visible when stem is in a breadboard."
            ),
            "lines": board_id_lines,
        }
    out_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


def _parse_board_id_lines(sb: dict[str, Any]) -> list[dict[str, Any]] | None:
    raw = sb.get("board_id_lines")
    if not isinstance(raw, list) or not raw:
        return None
    lines: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        t = row.get("text")
        h = row.get("height", TARGET_H_FILE)
        if t is None:
            continue
        lines.append(
            {
                "text": str(t),
                "d": text_to_path_at_origin(str(t), target_h=float(h)),
            }
        )
    return lines or None


def bake_gpio_from_board_toml(
    toml_path: Path,
    silk_out_dir: Path,
    *,
    adapter_pins_override: int | None = None,
) -> Path:
    """Read ``[silk_bake]`` from a board profile TOML and write one GPIO silk JSON file.

    Returns the path written. Validates label counts vs ``adapter_pins`` (half each row).
    """
    raw = tomllib.loads(toml_path.read_bytes().decode("utf-8"))
    sb = raw.get("silk_bake")
    if not isinstance(sb, dict):
        raise ValueError(f"{toml_path}: missing [silk_bake] table")
    out_name = sb.get("output")
    if not out_name or not str(out_name).strip():
        raise ValueError(f"{toml_path}: [silk_bake].output is required")
    out_name = str(out_name).strip()

    j1 = sb.get("j1_labels")
    j3 = sb.get("j3_labels")
    if not isinstance(j1, list) or not isinstance(j3, list):
        raise ValueError(f"{toml_path}: [silk_bake].j1_labels and j3_labels must be arrays")
    j1s = [str(x) for x in j1]
    j3s = [str(x) for x in j3]

    ap = adapter_pins_override if adapter_pins_override is not None else int(
        raw["adapter_pins"]
    )
    nc = ap // 2
    if ap % 2 != 0:
        raise ValueError(f"{toml_path}: adapter_pins must be even")
    if len(j1s) != nc or len(j3s) != nc:
        raise ValueError(
            f"{toml_path}: j1_labels/j3_labels must each have length {nc} "
            f"(adapter_pins/2), got {len(j1s)} and {len(j3s)}"
        )

    variant = str(sb.get("variant", raw.get("id", toml_path.stem)))
    source = str(
        sb.get("source", "Board profile silk_bake (see resources/boards/*.toml)")
    )
    note = str(
        sb.get(
            "note",
            "Net i (1..N/2) = J1 column i; net i+N/2 = J3 column i. "
            "Orient module per datasheet.",
        )
    )

    bid_lines = _parse_board_id_lines(sb)
    out_path = silk_out_dir / out_name
    write_gpio_silk_json(
        out_path,
        j1_order=j1s,
        j3_order=j3s,
        variant=variant,
        source=source,
        note=note,
        board_id_lines=bid_lines,
    )
    return out_path


def iter_board_tomls_with_silk_bake(boards_dir: Path) -> list[Path]:
    """Return TOML paths that define ``[silk_bake].output``."""
    out: list[Path] = []
    for p in sorted(boards_dir.glob("*.toml")):
        try:
            data = tomllib.loads(p.read_bytes().decode("utf-8"))
        except OSError:
            continue
        sb = data.get("silk_bake")
        if isinstance(sb, dict) and sb.get("output"):
            out.append(p)
    return out
