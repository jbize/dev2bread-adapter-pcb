#!/usr/bin/env python3
"""
One-off: build EasyEDA TEXT path strings for adapter silk (DejaVu Sans).

Requires: **matplotlib** (third-party). If you run with system ``python3`` and it is missing,
this script re-executes with ``repo/.venv/bin/python`` when that exists; otherwise it prints
how to install.

Writes (under repo `out/intermediate/silk/`; gitignored — run before board generation):
  * devkitc1_gpio_silk_paths.json — ESP32-S3-DevKitC-1 v1.1 J1/J3 names
  * numeric_silk_paths.json — strings "1" .. "44" (generic pin index silk)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REEXEC_ENV = "_DEV2BREAD_SILK_BAKE_REEXEC"


def _venv_python(repo: Path) -> Path | None:
    if sys.platform == "win32":
        cand = repo / ".venv" / "Scripts" / "python.exe"
    else:
        cand = repo / ".venv" / "bin" / "python"
    return cand if cand.is_file() else None


def _print_matplotlib_help() -> None:
    print(
        "bake_devkitc_gpio_silk_paths.py requires the third-party package 'matplotlib'\n"
        "  (vector text → paths for EasyEDA silk).\n\n"
        "Install it in a project virtualenv (from the repo root):\n"
        "  python3 -m venv .venv && .venv/bin/pip install matplotlib\n\n"
        "Then run this script again. If .venv exists, it is used automatically when\n"
        "  system Python does not have matplotlib.\n",
        file=sys.stderr,
    )


def _ensure_matplotlib() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        pass
    else:
        return

    if os.environ.get(_REEXEC_ENV):
        _print_matplotlib_help()
        raise SystemExit(1)

    vpy = _venv_python(_REPO_ROOT)
    if vpy is not None:
        env = {**os.environ, _REEXEC_ENV: "1"}
        script = Path(__file__).resolve()
        os.execve(str(vpy), [str(vpy), str(script)] + sys.argv[1:], env)

    _print_matplotlib_help()
    raise SystemExit(1)


_ensure_matplotlib()

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D

# Short silk strings matching Espressif J1/J3 "Name" column (v1.1), nets 1–22 per row.
# Net 1–22 = J1 pin 1–22 along +X; net 23–44 = J3 pin 1–22 along +X.
# User must orient the dev board so J1 faces side A and J3 faces side B.
J1_SILK = [
    "3V3",
    "3V3",
    "RST",
    "4",
    "5",
    "6",
    "7",
    "15",
    "16",
    "17",
    "18",
    "8",
    "3",
    "46",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "5V",
    "GND",
]
J3_SILK = [
    "GND",
    "TX",
    "RX",
    "1",
    "2",
    "42",
    "41",
    "40",
    "39",
    "38",
    "37",
    "36",
    "35",
    "0",
    "45",
    "48",
    "47",
    "21",
    "20",
    "19",
    "GND",
    "GND",
]

TARGET_H_FILE = 4.5  # ~45 mil letter height in EasyEDA file units (÷10 = mil)
# Board identification (neck / base of head), devkitc1 silk only — not per-pin strings.
BOARD_ID_LINES: tuple[tuple[str, float], ...] = (
    ("ESP32-S3-DevKitC-1", 5.5),
    ("v1.1 · J1/J3", 4.5),
)


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
            # Should not appear after interpolated()
            i += 1
            continue
        i += 1
    return " ".join(parts)


def text_to_path_at_origin(label: str, *, target_h: float = TARGET_H_FILE) -> str:
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


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "out" / "intermediate" / "silk"
    root.mkdir(parents=True, exist_ok=True)

    uniq = sorted(set(J1_SILK + J3_SILK), key=len)
    paths = {s: text_to_path_at_origin(s) for s in uniq}
    out_devkitc = root / "devkitc1_gpio_silk_paths.json"
    board_lines = [
        {"text": t, "d": text_to_path_at_origin(t, target_h=h)}
        for t, h in BOARD_ID_LINES
    ]
    meta = {
        "variant": "esp32-s3-devkitc-1-v1.1",
        "source": "Espressif ESP32-S3-DevKitC-1 v1.1 header tables (J1, J3)",
        "j1_order": J1_SILK,
        "j3_order": J3_SILK,
        "note": "Net i (1..22) = J1 pin i; net i+22 (23..44) = J3 pin i. Board orientation: J1 toward side A.",
        "board_id_silk": {
            "placement": "above_stem",
            "note": (
                "Top silk between J3 row and stem pads (avoids J3 GPIO labels); "
                "visible when stem is in a breadboard."
            ),
            "lines": board_lines,
        },
        "paths": paths,
    }
    out_devkitc.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(out_devkitc, len(paths), "unique DevKitC strings")

    numeric_paths = {str(i): text_to_path_at_origin(str(i)) for i in range(1, 45)}
    out_num = root / "numeric_silk_paths.json"
    meta_n = {
        "variant": "numeric-1-44",
        "note": "Silk shows logical pin index 1–44 (same as copper net labels). Not board-vendor-specific.",
        "paths": numeric_paths,
    }
    out_num.write_text(json.dumps(meta_n, indent=1), encoding="utf-8")
    print(out_num, len(numeric_paths), "numeric strings")


if __name__ == "__main__":
    main()
