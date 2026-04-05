"""Optional board branding (Top Silk) in the wide-head gap between innermost header rows."""

from __future__ import annotations

import base64
import io
import logging
import sys
from pathlib import Path
from typing import Callable

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D

from adapter_gen.board_profile import BoardBranding
from adapter_gen.geometry import (
    BoardParams,
    header_branding_region_mil,
)


def branding_font_properties(b: BoardBranding) -> FontProperties:
    """Matplotlib font for branding text outlines (EasyEDA + SVG).

    ``family`` is tried first, then ``DejaVu Sans`` if the face is missing (e.g. Linux
    without ``Segoe Script``).
    """
    primary = (b.font_family or "").strip() or "Segoe Script"
    family: list[str] | str = [primary, "DejaVu Sans"]
    return FontProperties(
        family=family,
        size=b.font_size_pt,
        weight=b.font_weight,
        style=b.font_style,
    )


# Same stroke / font model as ``scripts/bake_devkitc_gpio_silk_paths.py``.
BRANDING_TEXT_TARGET_H_FILE = 5.0

# Insets inside the pad-cleared branding strip (mil).
BRANDING_INNER_PAD_MIL = 8.0
# Space between image block and text block when both are present (mil).
BRANDING_IMAGE_TEXT_GAP_MIL = 18.0


def _path_to_d(path: MPath) -> str:
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


def branding_text_path_d_fit(
    label: str,
    max_w_mil: float,
    max_h_mil: float,
    *,
    font: FontProperties,
) -> str:
    """Centered path ``d`` (EasyEDA file units) scaled to **fill** ``max_w_mil`` × ``max_h_mil``.

    Uses the maximum uniform scale that fits inside the box (can scale up or down).
    ``FontProperties.size`` (TOML ``font_size``) only affects outline fidelity, not final size.
    """
    # Matplotlib logs "Font family X not found" when substituting; branding TOML may name
    # Windows-only faces (e.g. Segoe Script) on Linux.
    _log_fm = logging.getLogger("matplotlib.font_manager")
    _prev = _log_fm.level
    _log_fm.setLevel(logging.ERROR)
    try:
        tp = TextPath((0, 0), label, prop=font)
    finally:
        _log_fm.setLevel(_prev)
    path = MPath(tp.vertices, tp.codes)
    bb = path.get_extents()
    h = max(bb.height, 1e-6)
    scale0 = BRANDING_TEXT_TARGET_H_FILE / h
    cx = (bb.x0 + bb.x1) / 2.0
    cy = (bb.y0 + bb.y1) / 2.0
    trans = Affine2D().translate(-cx, -cy).scale(scale0, -scale0)
    p2 = path.transformed(trans)
    bb2 = p2.get_extents()
    wf = max(bb2.width, 1e-9)
    hf = max(bb2.height, 1e-9)
    max_w_f = max_w_mil / 10.0
    max_h_f = max_h_mil / 10.0
    # Do not cap at 1.0 — we must scale **up** when the normalized path is smaller than the box.
    s_fit = min(max_w_f / wf, max_h_f / hf)
    p3 = p2.transformed(Affine2D().scale(s_fit, s_fit))
    return _path_to_d(p3)


def _load_image_png_rgba(
    path: Path,
    *,
    max_width_mil: float,
    max_height_mil: float,
) -> tuple[bytes, float, float] | None:
    """Return PNG bytes and (width_mil, height_mil), uniform scale, no distortion."""
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        print(
            "Warning: branding image needs Pillow (`pip install Pillow`). Skipping image.",
            file=sys.stderr,
        )
        return None

    try:
        im = Image.open(path).convert("RGBA")
    except OSError as e:
        print(f"Warning: could not read branding image {path}: {e}. Skipping.", file=sys.stderr)
        return None

    w_px, h_px = im.size
    if w_px <= 0 or h_px <= 0:
        return None

    max_px = 512
    if w_px > max_px:
        scale = max_px / float(w_px)
        new_w = max_px
        new_h = max(1, int(h_px * scale))
        im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        new_w, new_h = w_px, h_px

    aspect = float(new_w) / float(new_h)
    h_mil = float(max_height_mil)
    w_mil = h_mil * aspect
    if w_mil > max_width_mil:
        w_mil = float(max_width_mil)
        h_mil = w_mil / aspect

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue(), w_mil, h_mil


def offset_silk_path_d(d: str, dx: float, dy: float) -> str:
    """Translate path in EasyEDA file units (same as generate_easyeda)."""
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
            x = float(parts[i + 1]) + dx
            y = float(parts[i + 2]) + dy
            out.append(f"{x:.2f}")
            out.append(f"{y:.2f}")
            i += 3
            continue
        raise ValueError(f"unexpected path token {tok!r} in branding path")
    return " ".join(out)


def append_branding_easyeda_shapes(
    shapes: list[str],
    nid: Callable[[], str],
    *,
    branding: BoardBranding,
    p: BoardParams,
    mil_to_u,
) -> None:
    """Append Top Silk IMAGE and/or TEXT inside the inner-row gap region (left image / right text)."""
    rl, rt, rw, rh = header_branding_region_mil(p)
    pad = BRANDING_INNER_PAD_MIL
    il = rl + pad
    it = rt + pad
    iw = rw - 2.0 * pad
    ih = rh - 2.0 * pad
    if iw < 1.0 or ih < 1.0:
        return

    if branding.image_path is not None and not branding.image_path.is_file():
        print(
            f"Warning: branding image not found: {branding.image_path}. Skipping image.",
            file=sys.stderr,
        )

    has_img = branding.image_path is not None and branding.image_path.is_file()
    has_txt = bool(branding.text and branding.text.strip())
    gap = BRANDING_IMAGE_TEXT_GAP_MIL

    img_left = img_top = img_w = img_h = 0.0
    png_bytes: bytes | None = None

    if has_img:
        if has_txt:
            img_max_w = max(10.0, 0.5 * (iw - gap))
            img_max_h = ih
        else:
            img_max_w = iw
            img_max_h = ih
        loaded = _load_image_png_rgba(
            branding.image_path,
            max_width_mil=img_max_w,
            max_height_mil=img_max_h,
        )
        if loaded is not None:
            png_bytes, img_w, img_h = loaded
            img_left = il
            img_top = it + 0.5 * (ih - img_h)

    if png_bytes is not None:
        x_u = mil_to_u(img_left)
        y_u = mil_to_u(img_top)
        w_u = mil_to_u(img_w)
        h_u = mil_to_u(img_h)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        shapes.append(f"IMAGE~{x_u}~{y_u}~{w_u}~{h_u}~3~{b64}~{nid()}")

    if has_txt:
        lab = branding.text.strip()
        fp = branding_font_properties(branding)
        if has_img and png_bytes is not None:
            tx_left = il + img_w + gap
            tw = max(1.0, iw - img_w - gap)
            cx_mil = tx_left + 0.5 * tw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(lab, tw, ih, font=fp)
        else:
            cx_mil = il + 0.5 * iw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(lab, iw, ih, font=fp)
        cx_u = mil_to_u(cx_mil)
        cy_u = mil_to_u(cy_mil)
        dabs = offset_silk_path_d(d0, cx_u, cy_u)
        shapes.append(
            f"TEXT~L~{cx_u}~{cy_u}~0.5~0~none~3~~5~{lab}~{dabs}~~{nid()}"
        )


def build_branding_svg_overlay(
    p: BoardParams,
    branding: BoardBranding,
) -> tuple[list[str], list[tuple[float, float, float, float, str]]] | None:
    """SVG preview: same placement as ``append_branding_easyeda_shapes``."""
    from adapter_gen.silk_preview import translate_silk_path_d_to_mil

    rl, rt, rw, rh = header_branding_region_mil(p)
    pad = BRANDING_INNER_PAD_MIL
    il = rl + pad
    it = rt + pad
    iw = rw - 2.0 * pad
    ih = rh - 2.0 * pad
    if iw < 1.0 or ih < 1.0:
        return None

    if branding.image_path is not None and not branding.image_path.is_file():
        print(
            f"Warning: branding image not found: {branding.image_path}. Skipping image.",
            file=sys.stderr,
        )

    has_img = branding.image_path is not None and branding.image_path.is_file()
    has_txt = bool(branding.text and branding.text.strip())
    gap = BRANDING_IMAGE_TEXT_GAP_MIL

    text_paths: list[str] = []
    images: list[tuple[float, float, float, float, str]] = []

    img_w = img_h = 0.0
    png_ok = False

    if has_img:
        if has_txt:
            img_max_w = max(10.0, 0.5 * (iw - gap))
            img_max_h = ih
        else:
            img_max_w = iw
            img_max_h = ih
        loaded = _load_image_png_rgba(
            branding.image_path,
            max_width_mil=img_max_w,
            max_height_mil=img_max_h,
        )
        if loaded is not None:
            png_bytes, img_w, img_h = loaded
            img_left = il
            img_top = it + 0.5 * (ih - img_h)
            uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode(
                "ascii"
            )
            images.append((img_left, img_top, img_w, img_h, uri))
            png_ok = True

    if has_txt:
        lab = branding.text.strip()
        fp = branding_font_properties(branding)
        if has_img and png_ok:
            tx_left = il + img_w + gap
            tw = max(1.0, iw - img_w - gap)
            cx_mil = tx_left + 0.5 * tw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(lab, tw, ih, font=fp)
        else:
            cx_mil = il + 0.5 * iw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(lab, iw, ih, font=fp)
        d_mil = translate_silk_path_d_to_mil(d0, cx_mil, cy_mil)
        text_paths.append(d_mil)

    if not text_paths and not images:
        return None
    return (text_paths, images)
