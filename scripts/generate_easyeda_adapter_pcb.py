#!/usr/bin/env python3
"""
Generate EasyEDA Standard PCB JSON for a 44-pin dev-board → breadboard adapter.

Mechanical model (matches typical “Dev2Bread” / Foreman-style boards, see
`docs/example-44pin-beradboard adapter.jpg`):
  * **Wide head (ESP32):** Two rows of 22 pins, 0.1" pitch, rows parallel to **+X**, ~1.1"
    between rows along **+Y**.
  * **Stem (breadboard end):** The narrow **T-stem** — same idea as a mushroom/wine-glass stem or
    (informally) a guitar **neck**. Rotated **90°** in the PCB vs the head; 22-pin direction **+Y**,
    straddle along **+X** (~0.5"). Placed **below** the head, centered (T shape).
  * **Wide head (optional rows):** On each side of the center gap, **four** 0.1\"-spaced holes per
    column (breadboard-style depth) — solder headers in **one** row only to match different
    dev-board widths. **TopLayer copper routing between pads is not emitted** (outline + drills +
    silk + branding only); a new router will replace the old behavior.
  * **Silk:** Optional pin-1 circles; optional per-pin text on wide head + stem — either
    **ESP32-S3-DevKitC-1 v1.1** names (`--silk-labels devkitc1`, baked paths in
    `out/intermediate/silk/devkitc1_gpio_silk_paths.json`) plus a two-line **board ID** in the neck,
    or generic **1–44** (`--silk-labels numeric`,
    `out/intermediate/silk/numeric_silk_paths.json`). Re-bake paths with
    `scripts/bake_devkitc_gpio_silk_paths.py` (writes under `out/intermediate/silk/`; not committed).

Two formats exist:
  * **Standard compressed** (this script’s default output): `head.docType` 3, `shape[]` of
    `~`-delimited strings. This is what EasyEDA Standard saves and what **EasyEDA Pro**
    imports via **File → Import → Import EasyEDA Standard Edition**.
  * **Expanded JSON** (TRACK/PAD objects): only useful for old Standard **applySource** API;
    EasyEDA Pro **File → File Source → Apply** expects Pro `.epcb` JSON Lines → "Invalid format".

See: https://docs.easyeda.com/en/DocumentFormat/3-EasyEDA-PCB-File-Format/
Storage units: file coordinates / stroke widths use **0.1 mil** steps (value 1 = 10 mil) per EasyEDA docs.
"""

from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapter_gen._venv_bootstrap import ensure_matplotlib  # noqa: E402

ensure_matplotlib()

try:
    from adapter_gen.board_profile import (
        BoardBranding,
        boards_dir,
        load_board_profile,
        resolve_board_params,
    )
    from adapter_gen.branding import append_branding_easyeda_shapes
    from adapter_gen.geometry import (
        BOARD_CORNER_RADIUS_MIL,
        BoardParams,
        HEAD_OUTLINE_EXTRA,
        HOLE_R,
        MARGIN,
        PAD_SIZE,
        SILK_OFF_HEAD_MIL,
        SILK_VERTICAL_HALF_EXTENT_MIL,
        STEM_OUTLINE_MARGIN,
        Y_W_ROW_A,
        board_outline_polyline_mil,
        head_column_x_mil,
        stem_layout_mil,
        stem_pin_y_mil,
        wide_head_y_rows_mil,
    )
    from adapter_gen.silk_preview import HEAD_SILK_ROTATE_DEG, rotate_silk_path_d
except ImportError as e:
    print(
        "Cannot import adapter_gen — run from the repository root.\n"
        f"  Expected: {_ROOT / 'adapter_gen'}\n"
        f"  ImportError: {e}\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from e

# Legacy expanded JSON only (copper routing). Geometry + pads use adapter_gen.geometry.
TRACK_WIDTH = 24
OUTLINE_STROKE = 5
ROUTE_JOG_MIL = 40

# Full 44-pin / 4-deep layout for ``build_legacy_expanded`` until that path is removed.
_LEGACY_BP = BoardParams(n_pins=44, n_rows_top=4, n_rows_bottom=4)


def mil_to_u(m: float) -> float:
    """EasyEDA PCB file uses 0.1 mil granularity (doc: stroke 1 = 10 mil)."""
    return m / 10.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _out_dir() -> Path:
    return _repo_root() / "out"


def _easyeda_dir() -> Path:
    """Importable EasyEDA Standard PCB JSON (product for CAD import)."""
    return _out_dir() / "easyeda"


def _intermediate_silk_dir() -> Path:
    """Baked silk vector paths (matplotlib output); not the board file."""
    return _out_dir() / "intermediate" / "silk"


def _offset_silk_path_d(d: str, dx: float, dy: float) -> str:
    """Translate an EasyEDA-style M/L/Z path (centered at origin) by (dx, dy) in file units."""
    parts = d.split()
    out: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if p == "Z":
            out.append("Z")
            i += 1
            continue
        if p in ("M", "L"):
            out.append(p)
            x = float(parts[i + 1]) + dx
            y = float(parts[i + 2]) + dy
            out.append(f"{x:.2f}")
            out.append(f"{y:.2f}")
            i += 3
            continue
        raise ValueError(f"unexpected path token {p!r} in silk path")
    return " ".join(out)


def _above_stem_board_id_center_mil(bp: BoardParams) -> tuple[float, float]:
    """Center for board-ID silk: below J3 row labels, above stem pads (same X as stem)."""
    xc, _, _, y_stem_top = stem_layout_mil(bp)
    pad_half = PAD_SIZE / 2.0
    # J3 per-pin silk sits near row B + off_head; keep ID lower in the throat.
    # ~120 mil above stem pad row centers clears two larger lines without overlapping stem pads.
    y_mid = y_stem_top - pad_half - 120.0
    return xc, y_mid


def _append_devkitc_board_id_silk(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    lines: list[dict[str, str]],
    bp: BoardParams,
) -> None:
    """Two-line kit label between J3 row and stem (visible when stem is in a breadboard)."""
    if not lines:
        return
    cx_mil, y_mid_mil = _above_stem_board_id_center_mil(bp)
    cx = mil_to_u(cx_mil)
    # Stack lines: index 0 above center, index 1 below (reading top-to-bottom on the PCB +Y down).
    n = len(lines)
    if n == 1:
        offs = [0.0]
    else:
        gap_mil = 64.0
        total = gap_mil * (n - 1)
        offs = [-total / 2.0 + i * gap_mil for i in range(n)]
    for i, row in enumerate(lines):
        lab = row["text"]
        d0 = row["d"]
        cy = mil_to_u(y_mid_mil + offs[i])
        dabs = _offset_silk_path_d(d0, cx, cy)
        shapes.append(f"TEXT~L~{cx}~{cy}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}")


def _append_labeled_silk(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    paths_map: dict[str, str],
    j1: list[str],
    j3: list[str],
    vertical_head: bool = False,
    bp: BoardParams,
) -> None:
    """Top silk at wide head + stem using parallel label lists (length ``bp.num_cols`` each).

    When ``vertical_head`` is True (devkitc1), head labels are rotated so they do not
    overlap along the row; stem labels stay horizontal.
    """
    xc, x_ln, x_rn, _ = stem_layout_mil(bp)
    y_row_b = bp.y_row_b
    off_head = float(SILK_OFF_HEAD_MIL)
    # Stem silk in the straddle gap (between pad columns and center), not outside the stem.
    cx_stem_left = mil_to_u((x_ln + xc) / 2.0)
    cx_stem_right = mil_to_u((xc + x_rn) / 2.0)

    def _head_d(lab: str) -> str:
        d0 = paths_map[lab]
        if vertical_head:
            d0 = rotate_silk_path_d(d0, HEAD_SILK_ROTATE_DEG)
        return d0

    for i in range(bp.num_cols):
        lab = j1[i]
        d0 = _head_d(lab)
        cx = mil_to_u(head_column_x_mil(i, bp))
        cy = mil_to_u(Y_W_ROW_A - off_head)
        dabs = _offset_silk_path_d(d0, cx, cy)
        shapes.append(f"TEXT~L~{cx}~{cy}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}")
    for i in range(bp.num_cols):
        lab = j3[i]
        d0 = _head_d(lab)
        cx = mil_to_u(head_column_x_mil(i, bp))
        cy = mil_to_u(y_row_b + off_head)
        dabs = _offset_silk_path_d(d0, cx, cy)
        shapes.append(f"TEXT~L~{cx}~{cy}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}")
    for i in range(bp.num_cols):
        lab = j1[i]
        d0 = paths_map[lab]
        cy = mil_to_u(stem_pin_y_mil(i, bp))
        dabs = _offset_silk_path_d(d0, cx_stem_left, cy)
        shapes.append(f"TEXT~L~{cx_stem_left}~{cy}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}")
    for i in range(bp.num_cols):
        lab = j3[i]
        d0 = paths_map[lab]
        cy = mil_to_u(stem_pin_y_mil(i, bp))
        dabs = _offset_silk_path_d(d0, cx_stem_right, cy)
        shapes.append(f"TEXT~L~{cx_stem_right}~{cy}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}")


def _numeric_silk_row_labels(bp: BoardParams) -> tuple[list[str], list[str]]:
    """J1 side = 1..N, J3 side = N+1..2N (matches pad numbering)."""
    nc = bp.num_cols
    j1 = [str(i) for i in range(1, nc + 1)]
    j3 = [str(i) for i in range(nc + 1, 2 * nc + 1)]
    return j1, j3


def _silk_pin1_circles_mil(bp: BoardParams) -> list[tuple[float, float, float]]:
    """Small open circles on Top Silk marking pin 1 (wide row A, stem). (cx, cy, r) in mil."""
    _, x_ln, _, y_stem_top = stem_layout_mil(bp)
    ys_a = wide_head_y_rows_mil(p=bp, from_row_a=True)
    x_pad = head_column_x_mil(0, bp)
    y_pad = ys_a[0]
    offset = 48.0
    r = 22.0
    # Northwest of pad centers — visible, avoids overlapping pads at usual fab rules
    return [
        (x_pad - offset, y_pad - offset, r),
        (x_ln - offset, y_stem_top - offset, r),
    ]


def build_standard_compressed(
    *,
    bp: BoardParams,
    margin_mil: float | None = None,
    stem_outline_margin_mil: float | None = None,
    head_outline_extra_mil: float | None = None,
    silk_pin1: bool = True,
    silk_labels: str = "devkitc1",
    branding: BoardBranding | None = None,
) -> dict:
    """EasyEDA Standard Edition JSON with `shape` array (tilde-delimited strings).

    ``bp`` must match ``resolve_board_params`` / preview SVG (``adapter_gen.geometry``).
    """
    if silk_labels not in ("none", "devkitc1", "numeric"):
        raise ValueError(f"invalid silk_labels: {silk_labels!r}")

    margin = margin_mil if margin_mil is not None else MARGIN
    stem_om = stem_outline_margin_mil if stem_outline_margin_mil is not None else STEM_OUTLINE_MARGIN
    head_ex = head_outline_extra_mil if head_outline_extra_mil is not None else HEAD_OUTLINE_EXTRA

    gid = 0

    def nid() -> str:
        nonlocal gid
        gid += 1
        return f"gge{gid}"

    shapes: list[str] = []

    poly_mil = board_outline_polyline_mil(
        bp,
        corner_radius_mil=BOARD_CORNER_RADIUS_MIL,
        arc_segments=8,
    )
    ow = mil_to_u(OUTLINE_STROKE) or 0.5
    for i in range(len(poly_mil)):
        x1, y1 = poly_mil[i]
        x2, y2 = poly_mil[(i + 1) % len(poly_mil)]
        shapes.append(
            f"TRACK~{ow}~10~~{mil_to_u(x1)} {mil_to_u(y1)} {mil_to_u(x2)} {mil_to_u(y2)}~{nid()}~0"
        )

    pw = mil_to_u(PAD_SIZE)
    hr = mil_to_u(HOLE_R)
    _, x_ln, x_rn, _ = stem_layout_mil(bp)

    x_ln_u = mil_to_u(x_ln)
    x_rn_u = mil_to_u(x_rn)

    # Wide side A: PTH pads only (no TopLayer copper between them — router TBD).
    for i in range(bp.num_cols):
        x = mil_to_u(head_column_x_mil(i, bp))
        y_s = mil_to_u(stem_pin_y_mil(i, bp))
        num = str(i + 1)
        ys_mil = wide_head_y_rows_mil(p=bp, from_row_a=True)
        for yk in ys_mil:
            shapes.append(
                f"PAD~ELLIPSE~{x}~{mil_to_u(yk)}~{pw}~{pw}~11~~{num}~{hr}~~0~{nid()}"
            )
        shapes.append(
            f"PAD~ELLIPSE~{x_ln_u}~{y_s}~{pw}~{pw}~11~~{num}~{hr}~~0~{nid()}"
        )

    # Wide side B: PTH pads only.
    nc = bp.num_cols
    for i in range(nc):
        x = mil_to_u(head_column_x_mil(i, bp))
        y_s = mil_to_u(stem_pin_y_mil(i, bp))
        num = str(i + nc + 1)
        ys_mil = wide_head_y_rows_mil(p=bp, from_row_a=False)
        for yk in ys_mil:
            shapes.append(
                f"PAD~ELLIPSE~{x}~{mil_to_u(yk)}~{pw}~{pw}~11~~{num}~{hr}~~0~{nid()}"
            )
        shapes.append(
            f"PAD~ELLIPSE~{x_rn_u}~{y_s}~{pw}~{pw}~11~~{num}~{hr}~~0~{nid()}"
        )

    if silk_pin1:
        sw = max(mil_to_u(5.0), 0.5)
        for cx, cy, r in _silk_pin1_circles_mil(bp):
            shapes.append(
                f"CIRCLE~{mil_to_u(cx)}~{mil_to_u(cy)}~{mil_to_u(r)}~{sw}~3~{nid()}"
            )

    if silk_labels == "devkitc1":
        data_path = _intermediate_silk_dir() / "devkitc1_gpio_silk_paths.json"
        if not data_path.is_file():
            print(
                f"Warning: {data_path} missing — run scripts/bake_devkitc_gpio_silk_paths.py "
                "(needs matplotlib in a venv). Skipping silk text.",
                file=sys.stderr,
            )
        else:
            raw = json.loads(data_path.read_text(encoding="utf-8"))
            paths_map: dict[str, str] = raw["paths"]
            j1: list[str] = raw["j1_order"]
            j3: list[str] = raw["j3_order"]
            if bp.num_cols != 22 or len(j1) != 22 or len(j3) != 22:
                print(
                    "Warning: devkitc1 silk is baked for 22 columns (44-pin class); "
                    "use --silk-labels numeric for other pin counts. Skipping silk text.",
                    file=sys.stderr,
                )
            else:
                _append_labeled_silk(
                    shapes,
                    nid,
                    paths_map=paths_map,
                    j1=j1,
                    j3=j3,
                    vertical_head=True,
                    bp=bp,
                )
                bid = raw.get("board_id_silk")
                if isinstance(bid, dict) and isinstance(bid.get("lines"), list):
                    _append_devkitc_board_id_silk(
                        shapes, nid, lines=bid["lines"], bp=bp
                    )
    elif silk_labels == "numeric":
        data_path = _intermediate_silk_dir() / "numeric_silk_paths.json"
        if not data_path.is_file():
            print(
                f"Warning: {data_path} missing — run scripts/bake_devkitc_gpio_silk_paths.py. "
                "Skipping silk text.",
                file=sys.stderr,
            )
        else:
            raw = json.loads(data_path.read_text(encoding="utf-8"))
            paths_map = raw["paths"]
            j1, j3 = _numeric_silk_row_labels(bp)
            _append_labeled_silk(
                shapes,
                nid,
                paths_map=paths_map,
                j1=j1,
                j3=j3,
                bp=bp,
            )

    if branding is not None:
        append_branding_easyeda_shapes(
            shapes,
            nid,
            branding=branding,
            p=bp,
            mil_to_u=mil_to_u,
        )

    xs = [pt[0] for pt in poly_mil]
    ys = [pt[1] for pt in poly_mil]
    xa, xb = mil_to_u(min(xs)), mil_to_u(max(xs))
    ya, yd = mil_to_u(min(ys)), mil_to_u(max(ys))
    bx, by, bw, bh = xa, ya, xb - xa, yd - ya

    # Canvas / origin — place origin near lower-left of content (file units)
    ox = (xa + xb) / 2
    oy = (ya + yd) / 2
    canvas = (
        f"CA~2400~2400~#000000~yes~#FFFFFF~10~1200~1200~line~1~mil~1~45~visible~0.5~{ox}~{oy}~0~yes"
    )

    layers = [
        "1~TopLayer~#FF0000~true~true~true~",
        "2~BottomLayer~#0000FF~true~false~true~",
        "3~TopSilkLayer~#FFCC00~true~false~true~",
        "4~BottomSilkLayer~#66CC33~true~false~true~",
        "5~TopPasteMaskLayer~#808080~true~false~true~",
        "6~BottomPasteMaskLayer~#800000~true~false~true~",
        "7~TopSolderMaskLayer~#800080~true~false~true~0.3",
        "8~BottomSolderMaskLayer~#AA00FF~true~false~true~0.3",
        "9~Ratlines~#6464FF~true~false~true~",
        "10~BoardOutline~#FF00FF~true~false~true~",
        "11~Multi-Layer~#C0C0C0~true~false~true~",
        "12~Document~#FFFFFF~true~false~true~",
    ]

    objects = [
        "All~true~false",
        "Component~true~true",
        "Prefix~true~true",
        "Name~true~false",
        "Track~true~true",
        "Pad~true~true",
        "Via~true~true",
        "Hole~true~true",
        "Copper_Area~true~true",
        "Circle~true~true",
        "Arc~true~true",
        "Solid_Region~true~true",
        "Text~true~true",
        "Image~true~true",
        "Rect~true~true",
        "Dimension~true~true",
        "Protractor~true~true",
    ]

    return {
        "head": {
            "docType": "3",
            "editorVersion": "6.5.0",
            "newgId": True,
            "c_para": {},
            "hasIdFlag": True,
        },
        "canvas": canvas,
        "shape": shapes,
        "layers": layers,
        "objects": objects,
        "BBox": {"x": bx, "y": by, "width": bw, "height": bh},
        "preference": {"hideFootprints": "", "hideNets": ""},
        "DRCRULE": {
            "Default": {
                "trackWidth": 1,
                "clearance": 0.6,
                "viaHoleDiameter": 2.4,
                "viaHoleD": 1.2,
            },
            "isRealtime": False,
            "isDrcOnRoutingOrPlaceVia": False,
            "checkObjectToCopperarea": True,
            "showDRCRangeLine": True,
        },
        "netColors": {},
    }


def build_legacy_expanded() -> dict:
    """Legacy expanded object graph with full copper routing (Standard applySource).

    Not for EasyEDA Pro File Source. **Scheduled for removal** once the new router exists;
    default Standard JSON no longer emits TopLayer tracks (see ``build_standard_compressed``).
    """

    gid = 0

    def next_id() -> str:
        nonlocal gid
        gid += 1
        return f"gge{gid}"

    tracks: dict = {}
    pads: dict = {}

    signals: dict[str, list] = {f"NET{n}": [] for n in range(1, 45)}
    signals[""] = []

    poly_mil = board_outline_polyline_mil(
        _LEGACY_BP,
        corner_radius_mil=BOARD_CORNER_RADIUS_MIL,
        arc_segments=8,
    )
    xs = [pt[0] for pt in poly_mil]
    ys = [pt[1] for pt in poly_mil]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    w = x_max - x_min
    h = y_max - y_min

    for i in range(len(poly_mil)):
        xa, ya = poly_mil[i]
        xb, yb = poly_mil[(i + 1) % len(poly_mil)]
        oid = next_id()
        tracks[oid] = {
            "gId": oid,
            "layerid": "10",
            "net": "",
            "pointArr": [{"x": xa, "y": ya}, {"x": xb, "y": yb}],
            "strokeWidth": OUTLINE_STROKE,
        }
        signals[""].append(
            {"gId": oid, "cmd": "TRACK", "layerid": 10, "fid": 0}
        )

    def add_signal(net: str, obj: dict, cmd: str) -> None:
        signals[net].append(
            {
                "gId": obj["gId"],
                "cmd": cmd,
                "layerid": obj.get("layerid", "11"),
                "fid": 0,
            }
        )

    item_order: list[str] = list(tracks.keys())

    leg = _LEGACY_BP
    _, x_ln, x_rn, _ = stem_layout_mil(leg)
    nc = leg.num_cols
    nra = leg.n_rows_top
    nrb = leg.n_rows_bottom

    for i in range(nc):
        net = f"NET{i + 1}"
        x = head_column_x_mil(i, leg)
        xj = x - ROUTE_JOG_MIL
        ys_stem = stem_pin_y_mil(i, leg)
        ys_head = wide_head_y_rows_mil(p=leg, from_row_a=True)
        y_inner = ys_head[-1]
        for yk in ys_head:
            pid = next_id()
            pads[pid] = pad_dict(pid, x, yk, str(i + 1), net)
            add_signal(net, pads[pid], "PAD")
            item_order.append(pid)
        for k in range(nra - 1):
            lk = next_id()
            tracks[lk] = {
                "gId": lk,
                "layerid": "1",
                "net": net,
                "pointArr": [
                    {"x": x, "y": ys_head[k]},
                    {"x": x, "y": ys_head[k + 1]},
                ],
                "strokeWidth": TRACK_WIDTH,
            }
            add_signal(net, tracks[lk], "TRACK")
            item_order.append(lk)
        pw = next_id()
        pads[pw] = pad_dict(pw, x_ln, ys_stem, str(i + 1), net)
        tr = next_id()
        tracks[tr] = {
            "gId": tr,
            "layerid": "1",
            "net": net,
            "pointArr": [
                {"x": x, "y": y_inner},
                {"x": xj, "y": y_inner},
                {"x": xj, "y": ys_stem},
                {"x": x_ln, "y": ys_stem},
            ],
            "strokeWidth": TRACK_WIDTH,
        }
        add_signal(net, pads[pw], "PAD")
        add_signal(net, tracks[tr], "TRACK")
        item_order.extend([pw, tr])

    for i in range(nc):
        net = f"NET{i + nc + 1}"
        x = head_column_x_mil(i, leg)
        xj = x + ROUTE_JOG_MIL
        ys_stem = stem_pin_y_mil(i, leg)
        ys_head = wide_head_y_rows_mil(p=leg, from_row_a=False)
        y_inner = ys_head[-1]
        for yk in ys_head:
            pid = next_id()
            pads[pid] = pad_dict(pid, x, yk, str(i + nc + 1), net)
            add_signal(net, pads[pid], "PAD")
            item_order.append(pid)
        for k in range(nrb - 1):
            lk = next_id()
            tracks[lk] = {
                "gId": lk,
                "layerid": "1",
                "net": net,
                "pointArr": [
                    {"x": x, "y": ys_head[k]},
                    {"x": x, "y": ys_head[k + 1]},
                ],
                "strokeWidth": TRACK_WIDTH,
            }
            add_signal(net, tracks[lk], "TRACK")
            item_order.append(lk)
        pw = next_id()
        pads[pw] = pad_dict(pw, x_rn, ys_stem, str(i + nc + 1), net)
        tr = next_id()
        tracks[tr] = {
            "gId": tr,
            "layerid": "1",
            "net": net,
            "pointArr": [
                {"x": x, "y": y_inner},
                {"x": xj, "y": y_inner},
                {"x": xj, "y": ys_stem},
                {"x": x_rn, "y": ys_stem},
            ],
            "strokeWidth": TRACK_WIDTH,
        }
        add_signal(net, pads[pw], "PAD")
        add_signal(net, tracks[tr], "TRACK")
        item_order.extend([pw, tr])

    return {
        "TRACK": tracks,
        "PAD": pads,
        "VIA": {},
        "TEXT": {},
        "DIMENSION": {},
        "FOOTPRINT": {},
        "ARC": {},
        "RECT": {},
        "CIRCLE": {},
        "IMAGE": {},
        "COPPERAREA": {},
        "SOLIDREGION": {},
        "DRCRULE": {
            "trackWidth": 6,
            "track2Track": 6,
            "pad2Pad": 8,
            "track2Pad": 8,
            "hole2Hole": 10,
            "holeSize": HOLE_R * 2,
            "isRealtime": False,
        },
        "FABRICATION": {},
        "SIGNALS": signals,
        "head": {"c_para": None},
        "systemColor": {
            "background": "#000000",
            "grid": "#FFFFFF",
            "highLight": "#FFFFFF",
            "hole": "#000000",
            "DRCError": "#FFFFFF",
        },
        "preference": {"hideNets": [], "hideFootprints": [], "unit": "mil"},
        "layers": _layers_expanded(),
        "BBox": {
            "x": int(x_min),
            "y": int(y_min),
            "width": int(w),
            "height": int(h),
        },
        "canvas": {
            "viewWidth": "2400",
            "viewHeight": "2400",
            "backGround": "#000000",
            "gridVisible": "yes",
            "gridColor": "#FFFFFF",
            "gridSize": "10",
            "canvasWidth": 2400,
            "canvasHeight": 2400,
            "gridStyle": "line",
            "snapSize": "1",
            "unit": "mil",
            "routingWidth": "10",
            "routingAngle": "45",
            "copperAreaDisplay": "invisible",
            "altSnapSize": "0.5",
        },
        "itemOrder": item_order,
    }


def pad_dict(gid: str, x: float, y: float, number: str, net: str) -> dict:
    return {
        "gId": gid,
        "layerid": "11",
        "shape": "ELLIPSE",
        "x": x,
        "y": y,
        "net": net,
        "width": PAD_SIZE,
        "height": PAD_SIZE,
        "number": number,
        "holeR": HOLE_R,
        "pointArr": [],
        "rotation": "0",
    }


def _layers_expanded() -> dict:
    return {
        "1": {
            "name": "TopLayer",
            "color": "#FF0000",
            "darkColor": "#CC0000",
            "visible": True,
            "active": True,
            "config": True,
        },
        "2": {
            "name": "BottomLayer",
            "color": "#0000FF",
            "darkColor": "#000080",
            "visible": True,
            "active": False,
            "config": True,
        },
        "3": {
            "name": "TopSilkLayer",
            "color": "#FFFF00",
            "darkColor": "#B9B900",
            "visible": True,
            "active": False,
            "config": True,
        },
        "4": {
            "name": "BottomSilkLayer",
            "color": "#808000",
            "darkColor": "#535300",
            "visible": True,
            "active": False,
            "config": True,
        },
        "5": {
            "name": "TopPasterLayer",
            "color": "#808080",
            "darkColor": "#666666",
            "visible": False,
            "active": False,
            "config": False,
        },
        "6": {
            "name": "BottomPasterLayer",
            "color": "#800000",
            "darkColor": "#660000",
            "visible": False,
            "active": False,
            "config": False,
        },
        "7": {
            "name": "TopSolderLayer",
            "color": "#800080",
            "darkColor": "#660066",
            "visible": False,
            "active": False,
            "config": False,
        },
        "8": {
            "name": "BottomSolderLayer",
            "color": "#AA00FF",
            "darkColor": "#8800CC",
            "visible": False,
            "active": False,
            "config": False,
        },
        "9": {
            "name": "Ratlines",
            "color": "#6464FF",
            "darkColor": "#5050CC",
            "visible": False,
            "active": False,
            "config": True,
        },
        "10": {
            "name": "BoardOutline",
            "color": "#FF00FF",
            "darkColor": "#CC00CC",
            "visible": True,
            "active": False,
            "config": True,
        },
        "11": {
            "name": "Multi-Layer",
            "color": "#C0C0C0",
            "darkColor": "#999999",
            "visible": True,
            "active": False,
            "config": True,
        },
        "12": {
            "name": "Document",
            "color": "#FFFFFF",
            "darkColor": "#CCCCCC",
            "visible": True,
            "active": False,
            "config": True,
        },
        "21": {
            "name": "Inner1",
            "color": "#800000",
            "darkColor": "#660000",
            "visible": False,
            "active": False,
            "config": False,
        },
        "22": {
            "name": "Inner2",
            "color": "#008000",
            "darkColor": "#006600",
            "visible": False,
            "active": False,
            "config": False,
        },
        "23": {
            "name": "Inner3",
            "color": "#00FF00",
            "darkColor": "#00CC00",
            "visible": False,
            "active": False,
            "config": False,
        },
        "24": {
            "name": "Inner4",
            "color": "#000080",
            "darkColor": "#000066",
            "visible": False,
            "active": False,
            "config": False,
        },
    }


def _default_standard_path(
    repo: Path, silk_labels: str, *, board_stem: str | None
) -> Path:
    """Default JSON path; ``board_stem`` from ``--board`` / ``--profile`` sets the basename."""
    base = repo / "out" / "easyeda"
    if board_stem:
        if silk_labels == "none":
            return base / f"{board_stem}.standard.json"
        return base / f"{board_stem}.{silk_labels}.standard.json"
    if silk_labels == "none":
        return base / "easyeda-adapter-44pin-dev2bread.standard.json"
    return base / f"easyeda-adapter-44pin-dev2bread.{silk_labels}.standard.json"


def _legacy_expanded_pcb_path(repo: Path, board_stem: str | None) -> Path:
    name = (
        f"{board_stem}.pcb.json"
        if board_stem
        else "easyeda-adapter-44pin-dev2bread.pcb.json"
    )
    return _easyeda_dir() / name


def _write_standard(
    path: Path,
    args: Namespace,
    *,
    bp: BoardParams,
    branding: BoardBranding | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            build_standard_compressed(
                bp=bp,
                margin_mil=args.margin_mil,
                stem_outline_margin_mil=args.stem_outline_margin_mil,
                head_outline_extra_mil=args.head_outline_extra_mil,
                silk_pin1=not args.no_silk_pin1,
                silk_labels=args.silk_labels,
                branding=branding,
            ),
            f,
            indent=1,
        )
    print(path)


def main() -> None:
    repo = _repo_root()
    p = argparse.ArgumentParser(
        description="Generate EasyEDA Standard PCB JSON for the 44-pin dev-to-breadboard adapter.",
    )
    p.add_argument(
        "--legacy-expanded",
        action="store_true",
        help="Also write legacy expanded JSON with full copper routing "
        "(out/easyeda/<board>.pcb.json; not for Pro; to be removed).",
    )
    p.add_argument(
        "--no-branding",
        action="store_true",
        help="Omit optional board branding from TOML ([branding] text / image), even if defined.",
    )
    p.add_argument(
        "--no-silk-pin1",
        action="store_true",
        help="Omit Top Silk circles marking pin 1 (wide + stem).",
    )
    p.add_argument(
        "--silk-labels",
        choices=("devkitc1", "numeric", "none"),
        default="devkitc1",
        help="Per-pin silk on head+stem: ESP32-S3-DevKitC-1 v1.1 names, logical 1–44, or text off.",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument(
        "--profile",
        type=Path,
        default=None,
        metavar="FILE",
        help="Board TOML; file stem is used for default output names (alternative to --board).",
    )
    src.add_argument(
        "--board",
        type=str,
        default=None,
        metavar="NAME",
        help="Load resources/boards/<NAME>.toml; name is used for default output filenames.",
    )
    p.add_argument(
        "--pins",
        type=int,
        default=None,
        metavar="N",
        help="Total pin count (even). Overrides profile.adapter_pins when set. "
        "When no --board/--profile, defaults to 44.",
    )
    p.add_argument(
        "--rows-top",
        type=int,
        default=None,
        metavar="N",
        help="Override: socket depth rows from row A (1..4). Same as preview_adapter_board.",
    )
    p.add_argument(
        "--rows-bottom",
        type=int,
        default=None,
        metavar="N",
        help="Override: socket depth rows from row B (1..4).",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help="Override output path (default: out/easyeda/<board>.<silk>.standard.json, or "
        "legacy easyeda-adapter-44pin-dev2bread.* when no --board/--profile).",
    )
    p.add_argument(
        "--all-variants",
        action="store_true",
        help="Write devkitc1 + numeric to default paths (ignores -o).",
    )
    p.add_argument(
        "--margin-mil",
        type=float,
        default=None,
        metavar="M",
        help=f"Board outline inset from outermost pads (default {MARGIN}). Larger = more FR4 around pins.",
    )
    p.add_argument(
        "--stem-outline-margin-mil",
        type=float,
        default=None,
        metavar="M",
        help=f"Extra width beyond stem pad columns (default {STEM_OUTLINE_MARGIN}).",
    )
    p.add_argument(
        "--head-outline-extra-mil",
        type=float,
        default=None,
        metavar="M",
        help=f"Extra board beyond wide head left/right (default {HEAD_OUTLINE_EXTRA}).",
    )
    args = p.parse_args()

    if args.board is not None:
        board_path = boards_dir(repo) / f"{args.board}.toml"
        if not board_path.is_file():
            p.error(f"Board profile not found: {board_path}")
    if args.profile is not None and not args.profile.is_file():
        p.error(f"Board profile not found: {args.profile}")

    board_stem: str | None = None
    profile = None
    if args.profile is not None:
        board_stem = args.profile.resolve().stem
        profile = load_board_profile(args.profile.resolve())
    elif args.board is not None:
        board_stem = args.board
        profile = load_board_profile(boards_dir(repo) / f"{args.board}.toml")

    branding: BoardBranding | None = None
    if (
        profile is not None
        and profile.branding is not None
        and not args.no_branding
    ):
        branding = profile.branding

    if profile is None:
        pins_eff = args.pins if args.pins is not None else 44
        bp = resolve_board_params(
            None,
            pins=pins_eff,
            rows_top=args.rows_top,
            rows_bottom=args.rows_bottom,
        )
    else:
        bp = resolve_board_params(
            profile,
            pins=args.pins,
            rows_top=args.rows_top,
            rows_bottom=args.rows_bottom,
        )

    if args.all_variants:
        for variant in ("devkitc1", "numeric"):
            args.silk_labels = variant
            outp = _default_standard_path(repo, variant, board_stem=board_stem)
            _write_standard(outp, args, bp=bp, branding=branding)
    else:
        out = args.output or _default_standard_path(
            repo, args.silk_labels, board_stem=board_stem
        )
        _write_standard(out, args, bp=bp, branding=branding)

    if args.legacy_expanded:
        leg_path = _legacy_expanded_pcb_path(repo, board_stem)
        leg_path.parent.mkdir(parents=True, exist_ok=True)
        with leg_path.open("w", encoding="utf-8") as f:
            json.dump(build_legacy_expanded(), f, indent=1)
        print(leg_path)


if __name__ == "__main__":
    main()
