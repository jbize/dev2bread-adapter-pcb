#!/usr/bin/env python3
"""Extract branding IMAGE + TEXT (+ SVGNODE logo) from EasyEDA Standard JSON; render SVG.

Reads ``IMAGE~`` / ``TEXT~L~`` (file units: 1 = 10 mil). Our generator uses
``~0~none~3~~5~`` for silk text; EasyEDA re-exports often use ``~0~0~3~~5~`` — both are
accepted. Logos may be ``IMAGE~`` (base64 PNG) from our tool or ``SVGNODE~`` path data
from the editor — both are handled when on Top Silk (layer 3).

Usage (repo root)::

  ./scripts/branding_box_from_easyeda_json.py \\
      out/easyeda/esp32-s3-devkitc-1.devkitc1.standard.json
  ./scripts/branding_box_from_easyeda_json.py -o /tmp/brand.svg path/to/board.standard.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _parse_image_shape(s: str) -> tuple[float, float, float, float, str] | None:
    """Return (x, y, w, h file units), base64 payload, or None."""
    if not s.startswith("IMAGE~"):
        return None
    m = re.match(
        r"^IMAGE~([^~]+)~([^~]+)~([^~]+)~([^~]+)~([^~]+)~(.+)~([^~]+)$",
        s,
    )
    if not m:
        return None
    x, y, w, h, layer, b64, _nid = m.groups()
    if layer != "3":
        return None
    return float(x), float(y), float(w), float(h), b64


def _parse_branding_text_shape(
    s: str,
) -> tuple[float, float, float, str, str] | None:
    """Return (cx, cy, stroke file units), label, path d (file units), or None.

    Matches Top Silk ``TEXT~L~`` with ``…~(stroke)~(rot)~(fill)~3~~5~(label)~(path)~~(id)``.
    ``fill`` is ``none`` from our emitter or ``0`` from EasyEDA export; ``id`` may have
    extra trailing ``~`` from the editor.
    """
    if not s.startswith("TEXT~L~"):
        return None
    m = re.match(
        r"^TEXT~L~([^~]+)~([^~]+)~([^~]+)~[^~]+~[^~]+~3~~5~([^~]+)~(M.*)~~([^~]+)~*$",
        s,
    )
    if not m:
        return None
    cx, cy, stroke, lab, d, _nid = m.groups()
    return float(cx), float(cy), float(stroke), lab, d


def _parse_svgnode_silk_path(s: str) -> tuple[str, float] | None:
    """Top Silk (layer 3) ``SVGNODE`` path ``d`` and stroke width in file units, or None."""
    if not s.startswith("SVGNODE~"):
        return None
    try:
        payload = json.loads(s.split("~", 1)[1])
    except (json.JSONDecodeError, IndexError):
        return None
    if str(payload.get("layerid")) != "3":
        return None
    attrs = payload.get("attrs") or {}
    d = attrs.get("d")
    if not isinstance(d, str) or not d.strip():
        return None
    sw = attrs.get("stroke")
    if sw == "none" or sw is None:
        stroke_u = 0.5
    else:
        try:
            stroke_u = float(sw)
        except (TypeError, ValueError):
            stroke_u = 0.5
    return d, stroke_u


def _path_bbox_file_units(d: str) -> tuple[float, float, float, float] | None:
    """Min/max x,y in path ``d`` (EasyEDA file units)."""
    nums = re.findall(r"[ML]\s+([0-9.-]+)\s+([0-9.-]+)", d)
    if not nums:
        return None
    xs = [float(a) for a, _ in nums]
    ys = [float(b) for _, b in nums]
    return min(xs), min(ys), max(xs), max(ys)


def _union_bbox(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    if not boxes:
        return None
    minx = min(b[0] for b in boxes)
    miny = min(b[1] for b in boxes)
    maxx = max(b[2] for b in boxes)
    maxy = max(b[3] for b in boxes)
    return minx, miny, maxx, maxy


def extract_branding_from_shapes(shapes: list) -> tuple[
    list[tuple[float, float, float, float, str]],
    list[tuple[float, float, float, str, str]],
    list[tuple[str, float]],
]:
    """Collect branding IMAGE(s), longest TEXT~L~ on Top Silk, and SVGNODE paths (layer 3).

    Heuristic: branding text has the **longest** ``d`` among matching ``TEXT~L~`` shapes
    (GPIO labels are shorter). All layer-3 ``IMAGE~`` and ``SVGNODE`` silk paths are kept.
    """
    images: list[tuple[float, float, float, float, str]] = []
    text_candidates: list[tuple[float, float, float, str, str]] = []
    svgnode_paths: list[tuple[str, float]] = []

    for item in shapes:
        if not isinstance(item, str):
            continue
        im = _parse_image_shape(item)
        if im is not None:
            x, y, w, h, b64 = im
            images.append((x, y, w, h, b64))
        tx = _parse_branding_text_shape(item)
        if tx is not None:
            text_candidates.append(tx)
        sn = _parse_svgnode_silk_path(item)
        if sn is not None:
            svgnode_paths.append(sn)

    if not text_candidates:
        chosen: list[tuple[float, float, float, str, str]] = []
    else:
        longest = max(text_candidates, key=lambda t: len(t[4]))
        chosen = [longest]

    return images, chosen, svgnode_paths


def emit_branding_svg(
    images: list[tuple[float, float, float, float, str]],
    texts: list[tuple[float, float, float, str, str]],
    svgnode_paths: list[tuple[str, float]] | None = None,
    *,
    pad_mil: float = 24.0,
) -> str:
    """SVG document in mil, +Y down."""
    if svgnode_paths is None:
        svgnode_paths = []
    boxes: list[tuple[float, float, float, float]] = []
    for x, y, w, h, _b64 in images:
        boxes.append((x * 10.0, y * 10.0, (x + w) * 10.0, (y + h) * 10.0))
    for _cx, _cy, stroke, _lab, d in texts:
        bb = _path_bbox_file_units(d)
        if bb is not None:
            minx, miny, maxx, maxy = bb
            boxes.append(
                (minx * 10.0, miny * 10.0, maxx * 10.0, maxy * 10.0),
            )
    for d, _sw in svgnode_paths:
        bb = _path_bbox_file_units(d)
        if bb is not None:
            minx, miny, maxx, maxy = bb
            boxes.append(
                (minx * 10.0, miny * 10.0, maxx * 10.0, maxy * 10.0),
            )
    u = _union_bbox(boxes)
    if u is None:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            "<title>No branding found</title></svg>"
        )
    minx, miny, maxx, maxy = u
    minx -= pad_mil
    miny -= pad_mil
    maxx += pad_mil
    maxy += pad_mil
    w = maxx - minx
    h = maxy - miny

    svg_open = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w:.1f}" height="{h:.1f}" '
        f'viewBox="{minx:.2f} {miny:.2f} {w:.2f} {h:.2f}">'
    )
    bg = (
        f'<rect x="{minx:.2f}" y="{miny:.2f}" width="{w:.2f}" '
        f'height="{h:.2f}" fill="#1a1a18"/>'
    )
    parts: list[str] = [
        svg_open,
        "<title>Branding extract (mil, +Y down)</title>",
        bg,
    ]
    for x, y, iw, ih, b64 in images:
        xm, ym, wm, hm = x * 10.0, y * 10.0, iw * 10.0, ih * 10.0
        uri = "data:image/png;base64," + b64
        parts.append(
            f'<image href="{uri}" x="{xm:.2f}" y="{ym:.2f}" '
            f'width="{wm:.2f}" height="{hm:.2f}" preserveAspectRatio="none"/>'
        )
    for _cx, _cy, stroke, lab, d in texts:
        sw = max(stroke * 10.0, 0.1)
        # Path coordinates are already absolute file units → mil.
        d_mil = _path_d_file_to_mil(d)
        p_el = (
            f'<path fill="none" stroke="#ffcc00" stroke-width="{sw:.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'd="{_xml_escape_attr(d_mil)}"/>'
        )
        parts.append(p_el)
        parts.append(
            f'<!-- label: {_xml_escape_attr(lab)} -->',
        )
    for d, stroke_u in svgnode_paths:
        sw = max(stroke_u * 10.0, 0.1)
        d_mil = _path_d_file_to_mil(d)
        parts.append(
            f'<path fill="none" stroke="#88ddff" stroke-width="{sw:.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'd="{_xml_escape_attr(d_mil)}"/>'
        )
        parts.append("<!-- SVGNODE (EasyEDA-export logo path) -->")
    parts.append("</svg>")
    return "\n".join(parts)


def _path_d_file_to_mil(d: str) -> str:
    """Scale coordinates in ``d`` from file units to mil (×10)."""
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
            x = float(parts[i + 1]) * 10.0
            y = float(parts[i + 2]) * 10.0
            out.append(f"{x:.2f}")
            out.append(f"{y:.2f}")
            i += 3
            continue
        raise ValueError(f"bad path token {tok!r}")
    return " ".join(out)


def _xml_escape_attr(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Render branding IMAGE+TEXT from EasyEDA Standard JSON to a tight SVG."
        ),
    )
    p.add_argument(
        "json_path",
        type=Path,
        help=(
            "Path to *.standard.json "
            "(e.g. out/easyeda/<board>.devkitc1.standard.json)"
        ),
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output SVG (default: out/preview/<stem>-branding-only.svg)",
    )
    p.add_argument(
        "--pad-mil",
        type=float,
        default=24.0,
        help="Padding around union bbox (mil). Default: 24.",
    )
    args = p.parse_args()
    path = args.json_path.resolve()
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    shapes = data.get("shape")
    if not isinstance(shapes, list):
        print("JSON missing shape[]", file=sys.stderr)
        raise SystemExit(1)
    images, texts, svgnode_paths = extract_branding_from_shapes(shapes)
    if not images and not texts and not svgnode_paths:
        print(
            "No branding: IMAGE~ (layer 3), TEXT~L~…~3~~5~…, or SVGNODE (layer 3).",
            file=sys.stderr,
        )
    out = args.output
    if out is None:
        out = _REPO / "out" / "preview" / f"{path.stem}-branding-only.svg"
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    svg = emit_branding_svg(
        images, texts, svgnode_paths, pad_mil=args.pad_mil
    )
    out.write_text(svg, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
