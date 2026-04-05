"""Load board parameter files (TOML) for human + machine use.

See ``resources/boards/esp32-s3-devkitc-1.toml`` for the schema.
Requires Python 3.11+ (``tomllib``).
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from adapter_gen.geometry import BoardParams


@dataclass(frozen=True)
class BoardBranding:
    """Optional Top Silk branding in the gap between innermost header rows (see ``branding.py``)."""

    text: str | None
    image_path: Path | None
    # Matplotlib ``FontProperties`` (glyph outline before fit-to-region scaling).
    font_family: str = "Segoe Script"
    font_size_pt: float = 96.0
    font_weight: str = "bold"
    font_style: str = "italic"


@dataclass(frozen=True)
class BoardProfile:
    """Metadata + pin counts from a board profile file."""

    id: str
    title: str
    description: str
    device_min_pins: int
    adapter_pins: int
    n_rows_top: int
    n_rows_bottom: int
    omit_row_b_gap_adjacent: bool
    silk_profile: str | None
    branding: BoardBranding | None
    source_path: Path | None


def _repo_root_from_board_profile(path: Path) -> Path:
    """``resources/boards/<name>.toml`` → repository root."""
    return path.resolve().parent.parent.parent


def _branding_font_fields(br: dict) -> tuple[str, float, str, str]:
    """Parse ``font_*`` from ``[branding]`` (defaults: script-like bold italic)."""
    raw_fam = br.get("font_family")
    if raw_fam is not None and str(raw_fam).strip():
        family = str(raw_fam).strip()
    else:
        family = "Segoe Script"
    raw_sz = br.get("font_size", 96.0)
    try:
        font_size_pt = float(raw_sz)
    except (TypeError, ValueError):
        font_size_pt = 96.0
    raw_w = br.get("font_weight", "bold")
    weight = str(raw_w).strip().lower() if raw_w is not None else "bold"
    raw_s = br.get("font_style", "italic")
    style = str(raw_s).strip().lower() if raw_s is not None else "italic"
    return family, font_size_pt, weight, style


def load_board_profile(path: Path) -> BoardProfile:
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    if int(data.get("schema", -1)) != 1:
        raise ValueError(f"{path}: expected schema = 1")

    geom = data.get("geometry") or {}
    branding: BoardBranding | None = None
    br = data.get("branding")
    if not isinstance(br, dict) and (
        data.get("text") is not None or data.get("image") is not None
    ):
        print(
            f"Warning: {path}: `text` / `image` must live under a `[branding]` table "
            "(uncomment the `[branding]` line). Using them as branding for this load.",
            file=sys.stderr,
        )
        br = {"text": data.get("text"), "image": data.get("image")}
    if isinstance(br, dict):
        txt = br.get("text")
        text = str(txt).strip() if txt is not None else None
        if text == "":
            text = None
        img_raw = br.get("image")
        img_path: Path | None = None
        if img_raw is not None and str(img_raw).strip() != "":
            raw = str(img_raw).strip()
            pimg = Path(raw)
            repo = _repo_root_from_board_profile(path)
            img_path = pimg.resolve() if pimg.is_absolute() else (repo / pimg).resolve()
        if text is not None or img_path is not None:
            ff, fsz, fw, fst = _branding_font_fields(br)
            branding = BoardBranding(
                text=text,
                image_path=img_path,
                font_family=ff,
                font_size_pt=fsz,
                font_weight=fw,
                font_style=fst,
            )

    return BoardProfile(
        id=str(data["id"]),
        title=str(data.get("title", data["id"])),
        description=str(data.get("description", "")),
        device_min_pins=int(data["device_min_pins"]),
        adapter_pins=int(data["adapter_pins"]),
        n_rows_top=int(geom.get("n_rows_top", data.get("n_rows_top", 4))),
        n_rows_bottom=int(geom.get("n_rows_bottom", data.get("n_rows_bottom", 4))),
        omit_row_b_gap_adjacent=bool(geom.get("omit_row_b_gap_adjacent", False)),
        silk_profile=data.get("silk_profile"),
        branding=branding,
        source_path=path.resolve(),
    )


def resolve_board_params(
    profile: BoardProfile | None,
    *,
    pins: int | None,
    rows_top: int | None,
    rows_bottom: int | None,
    omit_row_b_gap_adjacent: bool | None = None,
) -> BoardParams:
    """Merge CLI overrides onto profile; or use explicit pins if no profile."""
    if profile is None:
        if pins is None:
            raise ValueError("Either pass a BoardProfile or pins=")
        n = pins
        rt = rows_top if rows_top is not None else 4
        rb = rows_bottom if rows_bottom is not None else 4
        o = False if omit_row_b_gap_adjacent is None else omit_row_b_gap_adjacent
    else:
        n = profile.adapter_pins if pins is None else pins
        rt = profile.n_rows_top if rows_top is None else rows_top
        rb = profile.n_rows_bottom if rows_bottom is None else rows_bottom
        o = (
            profile.omit_row_b_gap_adjacent
            if omit_row_b_gap_adjacent is None
            else omit_row_b_gap_adjacent
        )
    return BoardParams(
        n_pins=n,
        n_rows_top=rt,
        n_rows_bottom=rb,
        omit_row_b_gap_adjacent=o,
    )


def boards_dir(repo_root: Path) -> Path:
    return repo_root / "resources" / "boards"
