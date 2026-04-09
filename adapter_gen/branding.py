"""Optional board branding (Top Silk) in the wide-head gap between innermost header rows.

Layout (image left / text right) is computed once in ``_compute_branding_layout`` and fed to both
EasyEDA ``IMAGE``/``TEXT`` emission and SVG preview — keep those call sites thin.

**Image:** If ``image`` is set in TOML to a non-empty path, that file must exist (or the
generator/preview raises). If you omit ``image``, text-only branding uses no image.

**Font / size:** Default face is ``DejaVu Sans`` / normal / normal when no ``font_*`` keys are in
TOML. If ``font_family``, ``font_weight``, or ``font_style`` is set in TOML (or ``--branding-font-family``
on the CLI), matplotlib must resolve that font — no silent fallback. ``branding_text_path_d_fit``
scales outlines to fill the text box; TOML ``font_size`` affects outline detail, not final mil size.
"""

from __future__ import annotations

import base64
import io
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.path import Path as MPath
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D

from adapter_gen.board_profile import BoardBranding
from adapter_gen.geometry import (
    BoardParams,
    header_branding_region_mil,
)


def branding_font_properties(b: BoardBranding) -> FontProperties:
    """Matplotlib font for branding text outlines (EasyEDA + SVG)."""
    primary = (b.font_family or "").strip() or "DejaVu Sans"
    style = cast(Literal["normal", "italic", "oblique"], b.font_style)
    return FontProperties(
        family=primary,
        size=b.font_size_pt,
        weight=b.font_weight,
        style=style,
    )


def _require_resolved_branding_font(font: FontProperties) -> None:
    """Fail if matplotlib cannot load the face (used when TOML/CLI fixed the font)."""
    try:
        fontManager.findfont(font, fallback_to_default=False)
    except ValueError as e:
        fam = font.get_family()
        fam_s = fam[0] if isinstance(fam, (list, tuple)) and fam else str(fam)
        raise RuntimeError(
            "Branding font cannot be resolved (install the font or change "
            f"[branding].font_family / --branding-font-family; requested {fam_s!r}). {e}"
        ) from e


# Same stroke / font model as ``scripts/bake_devkitc_gpio_silk_paths.py``.
BRANDING_TEXT_TARGET_H_FILE = 5.0

# EasyEDA TEXT stroke for branding only (file units: 1 = 10 mil). Wider than GPIO
# silk (0.5) so path-outlined lettering reads clearly in the editor at typical zoom;
# it is still stroke geometry, not a filled font.
BRANDING_TEXT_STROKE_FILE_U = 1.0
# SVG preview: same width in mil as EasyEDA stroke field × 10.
BRANDING_PREVIEW_STROKE_MIL = BRANDING_TEXT_STROKE_FILE_U * 10.0
# TopSilkLayer color in ``build_standard_compressed`` layers table (#FFCC00).
BRANDING_PREVIEW_SILK_COLOR = "#ffcc00"

# Insets inside the pad-cleared branding strip (mil).
BRANDING_INNER_PAD_MIL = 8.0
# Space between image block and text block when both are present (mil).
BRANDING_IMAGE_TEXT_GAP_MIL = 18.0


@dataclass(frozen=True)
class BrandingLayoutResult:
    """One layout for EasyEDA ``IMAGE``/``TEXT`` and SVG preview — same numbers, two emitters."""

    png_bytes: bytes | None
    img_left_mil: float
    img_top_mil: float
    img_w_mil: float
    img_h_mil: float
    has_png: bool
    text_label: str | None
    text_path_d0_file: str
    text_cx_mil: float
    text_cy_mil: float
    has_text: bool


def _compute_branding_layout(
    p: BoardParams,
    branding: BoardBranding,
) -> BrandingLayoutResult | None:
    """Place optional image (left) + text (right) in the full J1/J3 inner gap strip.

    Shared by ``append_branding_easyeda_shapes`` and ``build_branding_svg_overlay`` only.
    """
    rl, rt, rw, rh = header_branding_region_mil(p)
    pad = BRANDING_INNER_PAD_MIL
    il = rl + pad
    it = rt + pad
    iw = rw - 2.0 * pad
    ih = rh - 2.0 * pad
    if iw < 1.0 or ih < 1.0:
        return None

    if branding.image_path is not None and not branding.image_path.is_file():
        if branding.image_explicit:
            raise RuntimeError(
                f"Branding image not found (image was set in TOML): {branding.image_path}"
            )
        print(
            f"Warning: branding image not found: {branding.image_path}. Skipping image.",
            file=sys.stderr,
        )

    has_img = branding.image_path is not None and branding.image_path.is_file()
    has_txt = bool(branding.text and branding.text.strip())
    gap = BRANDING_IMAGE_TEXT_GAP_MIL

    png_bytes: bytes | None = None
    img_w = img_h = 0.0
    img_left = il
    img_top = it
    png_ok = False

    if has_img:
        img_path = branding.image_path
        assert img_path is not None
        if has_txt:
            img_max_w = max(10.0, 0.5 * (iw - gap))
            img_max_h = ih
        else:
            img_max_w = iw
            img_max_h = ih
        loaded = _load_image_png_rgba(
            img_path,
            max_width_mil=img_max_w,
            max_height_mil=img_max_h,
            strict=branding.image_explicit,
        )
        if loaded is not None:
            png_bytes, img_w, img_h = loaded
            img_left = il
            img_top = it + 0.5 * (ih - img_h)
            png_ok = True

    text_label: str | None = None
    d0 = ""
    cx_mil = cy_mil = 0.0
    has_text_out = False

    if has_txt:
        bt = branding.text
        assert bt is not None
        text_label = bt.strip()
        fp = branding_font_properties(branding)
        if has_img and png_ok:
            tx_left = il + img_w + gap
            tw = max(1.0, iw - img_w - gap)
            cx_mil = tx_left + 0.5 * tw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(
                text_label, tw, ih, font=fp, strict_font=branding.font_explicit
            )
        else:
            cx_mil = il + 0.5 * iw
            cy_mil = it + 0.5 * ih
            d0 = branding_text_path_d_fit(
                text_label, iw, ih, font=fp, strict_font=branding.font_explicit
            )
        has_text_out = True

    if not png_ok and not has_text_out:
        return None

    return BrandingLayoutResult(
        png_bytes=png_bytes if png_ok else None,
        img_left_mil=img_left,
        img_top_mil=img_top,
        img_w_mil=img_w if png_ok else 0.0,
        img_h_mil=img_h if png_ok else 0.0,
        has_png=png_ok,
        text_label=text_label,
        text_path_d0_file=d0,
        text_cx_mil=cx_mil,
        text_cy_mil=cy_mil,
        has_text=has_text_out,
    )


def _path_to_d(path: MPath) -> str:
    path = path.interpolated(10)
    verts = np.asarray(path.vertices, dtype=np.float64)
    codes = np.asarray(path.codes, dtype=np.int_)
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
    strict_font: bool = False,
) -> str:
    """Centered path ``d`` (EasyEDA file units) scaled to **fill** ``max_w_mil`` × ``max_h_mil``.

    Uses the maximum uniform scale that fits inside the box (can scale up or down).
    ``FontProperties.size`` (TOML ``font_size``) only affects outline fidelity, not final size.

    When ``strict_font`` is True (TOML or CLI set the face/weight/style), matplotlib must resolve
    the font; otherwise a missing face falls back like normal matplotlib behavior.
    """
    if strict_font:
        _require_resolved_branding_font(font)
    tp = TextPath((0, 0), label, prop=font)
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
    strict: bool = False,
) -> tuple[bytes, float, float] | None:
    """Return PNG bytes and (width_mil, height_mil), uniform scale, no distortion."""
    try:
        from PIL import Image
    except ImportError:
        if strict:
            raise RuntimeError(
                "Branding image requires Pillow (`pip install Pillow`) when [branding].image is set."
            ) from None
        print(
            "Warning: branding image needs Pillow (`pip install Pillow`). Skipping image.",
            file=sys.stderr,
        )
        return None

    try:
        im = Image.open(path).convert("RGBA")
    except OSError as e:
        if strict:
            raise RuntimeError(f"Could not read branding image {path}: {e}") from e
        print(
            f"Warning: could not read branding image {path}: {e}. Skipping.",
            file=sys.stderr,
        )
        return None

    w_px, h_px = im.size
    if w_px <= 0 or h_px <= 0:
        if strict:
            raise RuntimeError(f"Branding image has invalid size: {path}")
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
    lay = _compute_branding_layout(p, branding)
    if lay is None:
        return
    if lay.has_png and lay.png_bytes is not None:
        x_u = mil_to_u(lay.img_left_mil)
        y_u = mil_to_u(lay.img_top_mil)
        w_u = mil_to_u(lay.img_w_mil)
        h_u = mil_to_u(lay.img_h_mil)
        b64 = base64.b64encode(lay.png_bytes).decode("ascii")
        shapes.append(f"IMAGE~{x_u}~{y_u}~{w_u}~{h_u}~3~{b64}~{nid()}")
    if lay.has_text and lay.text_label:
        cx_u = mil_to_u(lay.text_cx_mil)
        cy_u = mil_to_u(lay.text_cy_mil)
        dabs = offset_silk_path_d(lay.text_path_d0_file, cx_u, cy_u)
        lab = lay.text_label
        shapes.append(
            f"TEXT~L~{cx_u}~{cy_u}~{BRANDING_TEXT_STROKE_FILE_U}~0~none~3~~5~"
            f"{lab}~{dabs}~~{nid()}"
        )


def build_branding_svg_overlay(
    p: BoardParams,
    branding: BoardBranding,
) -> tuple[list[str], list[tuple[float, float, float, float, str]]] | None:
    """SVG preview: same layout as ``append_branding_easyeda_shapes`` via ``_compute_branding_layout``."""
    from adapter_gen.silk_preview import translate_silk_path_d_to_mil

    lay = _compute_branding_layout(p, branding)
    if lay is None:
        return None
    images: list[tuple[float, float, float, float, str]] = []
    if lay.has_png and lay.png_bytes is not None:
        uri = "data:image/png;base64," + base64.b64encode(lay.png_bytes).decode("ascii")
        images.append(
            (
                lay.img_left_mil,
                lay.img_top_mil,
                lay.img_w_mil,
                lay.img_h_mil,
                uri,
            )
        )
    text_paths: list[str] = []
    if lay.has_text and lay.text_label:
        d_mil = translate_silk_path_d_to_mil(
            lay.text_path_d0_file,
            lay.text_cx_mil,
            lay.text_cy_mil,
        )
        text_paths.append(d_mil)
    if not text_paths and not images:
        return None
    return (text_paths, images)
