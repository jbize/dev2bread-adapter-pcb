"""Load board parameter files (TOML) for human + machine use.

See ``resources/boards/esp32-s3-devkitc-1.toml`` for the schema.
Requires Python 3.11+ (``tomllib``).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from adapter_gen.geometry import BoardParams


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
    silk_profile: str | None
    source_path: Path | None


def load_board_profile(path: Path) -> BoardProfile:
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    if int(data.get("schema", -1)) != 1:
        raise ValueError(f"{path}: expected schema = 1")

    geom = data.get("geometry") or {}
    return BoardProfile(
        id=str(data["id"]),
        title=str(data.get("title", data["id"])),
        description=str(data.get("description", "")),
        device_min_pins=int(data["device_min_pins"]),
        adapter_pins=int(data["adapter_pins"]),
        n_rows_top=int(geom.get("n_rows_top", data.get("n_rows_top", 4))),
        n_rows_bottom=int(geom.get("n_rows_bottom", data.get("n_rows_bottom", 4))),
        silk_profile=data.get("silk_profile"),
        source_path=path.resolve(),
    )


def resolve_board_params(
    profile: BoardProfile | None,
    *,
    pins: int | None,
    rows_top: int | None,
    rows_bottom: int | None,
) -> BoardParams:
    """Merge CLI overrides onto profile; or use explicit pins if no profile."""
    if profile is None:
        if pins is None:
            raise ValueError("Either pass a BoardProfile or pins=")
        n = pins
        rt = rows_top if rows_top is not None else 4
        rb = rows_bottom if rows_bottom is not None else 4
    else:
        n = profile.adapter_pins if pins is None else pins
        rt = profile.n_rows_top if rows_top is None else rows_top
        rb = profile.n_rows_bottom if rows_bottom is None else rows_bottom
    return BoardParams(n_pins=n, n_rows_top=rt, n_rows_bottom=rb)


def boards_dir(repo_root: Path) -> Path:
    return repo_root / "resources" / "boards"
