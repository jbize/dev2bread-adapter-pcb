#!/usr/bin/env python3
"""
Emit SVG preview: board outline + PTH holes (optional silk labels from baked JSON).

No copper yet — validates geometry vs N and socket row counts.

Silk vectors come from ``out/intermediate/silk/*.json`` (run
``scripts/bake_devkitc_gpio_silk_paths.py`` first). Use ``--silk auto`` to follow
the board profile's ``silk_profile`` when present.

**CLI-only** (repo root: ``./scripts/preview_adapter_board.py`` — shebang ``python3``)

  ./scripts/preview_adapter_board.py --pins <N>
      # → out/preview/board-<N>pin.svg; row-A inner reverser sketch on by default (any N)

  ./scripts/preview_adapter_board.py --pins 14 --no-row-reverser
  ./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1 --silk devkitc1

Silk + optional ``[branding]`` match what ``scripts/generate_easyeda_adapter_pcb.py`` emits
(same geometry; branding needs matplotlib, auto re-exec with ``.venv`` like the bake script).

**Board profile (TOML)** — default ``-o`` is ``out/preview/<board>.svg``::

  ./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1
  ./scripts/preview_adapter_board.py --profile resources/boards/example-14pin-7-per-row.toml
  ./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1 --no-branding

  ./scripts/preview_adapter_board.py --pins 44 --silk numeric --bottom-only
      # preview: bottom-copper trace strokes only (no top-layer sketch obscuring)

Silk modes and branding (devkitc1 vs numeric vs auto, ``--no-branding``): see repository
**README.md** (section **SVG preview**).

Run from repo root (or set PYTHONPATH).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root on path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapter_gen._venv_bootstrap import ensure_matplotlib  # noqa: E402

ensure_matplotlib()

try:
    from adapter_gen.board_profile import (  # noqa: E402
        BoardProfile,
        boards_dir,
        load_board_profile,
        resolve_board_params,
    )
    from adapter_gen.svg_preview import emit_board_svg  # noqa: E402
except ImportError as e:
    print(
        "Cannot import adapter_gen — run from the repository root.\n"
        f"  Expected: {_ROOT / 'adapter_gen'}\n"
        f"  ImportError: {e}\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from e


def _auto_silk_mode(profile: BoardProfile | None) -> str:
    """Map board TOML ``silk_profile`` to preview mode (none | devkitc1 | numeric)."""
    if profile is None or not profile.silk_profile:
        return "none"
    sp = profile.silk_profile
    if sp == "devkitc1":
        return "devkitc1"
    if sp in ("numeric", "generic"):
        return "numeric"
    print(
        f"Note: silk_profile={sp!r} is not mapped for SVG preview; "
        "use --silk devkitc1|numeric|none.",
        file=sys.stderr,
    )
    return "none"


def main() -> None:
    desc = "Preview T-board outline + holes (SVG)."
    p = argparse.ArgumentParser(description=desc)
    p.add_argument(
        "--pins",
        type=int,
        default=None,
        metavar="N",
        help="Total pin count (even, 14..44). Overrides profile. "
        "Required if no --profile/--board.",
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument(
        "--profile",
        type=Path,
        default=None,
        metavar="FILE",
        help="Board parameter TOML (see resources/boards/*.toml).",
    )
    src.add_argument(
        "--board",
        type=str,
        default=None,
        metavar="NAME",
        help="Short name: loads resources/boards/<NAME>.toml",
    )
    p.add_argument(
        "--rows-top",
        type=int,
        default=None,
        metavar="N",
        help="Override: socket depth rows from row A (1..4).",
    )
    p.add_argument(
        "--rows-bottom",
        type=int,
        default=None,
        metavar="N",
        help="Override: socket depth rows from row B (1..4).",
    )
    og = p.add_mutually_exclusive_group()
    og.add_argument(
        "--omit-row-b-gap-adjacent",
        dest="omit_row_b_gap_adjacent",
        action="store_true",
        default=None,
        help="Omit gap-adjacent row-B socket row (room for row-A reverser). Default: profile / off.",
    )
    og.add_argument(
        "--no-omit-row-b-gap-adjacent",
        dest="omit_row_b_gap_adjacent",
        action="store_false",
        default=None,
        help="Place pads on all row-B socket rows.",
    )
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        metavar="FILE",
        help="Output SVG (default: out/preview/<name>.svg from --board or --profile "
        "stem, else out/preview/board-<N>pin.svg).",
    )
    p.add_argument(
        "--silk",
        choices=("none", "devkitc1", "numeric", "auto"),
        default="auto",
        metavar="MODE",
        help="Overlay silk labels from baked JSON: none | devkitc1 | numeric | auto "
        "(use board profile silk_profile if set, else none).",
    )
    p.add_argument(
        "--silk-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory with devkitc1_gpio_silk_paths.json / numeric_silk_paths.json "
        "(default: out/intermediate/silk under repo root).",
    )
    p.add_argument(
        "--no-branding",
        action="store_true",
        help="Omit optional board branding from TOML ([branding] text / image), even if defined.",
    )
    rr = p.add_mutually_exclusive_group()
    rr.add_argument(
        "--row-reverser",
        dest="row_reverser",
        action="store_true",
        default=None,
        help="Draw row-A inner reverser routing sketch (scales with --pins / profile). Default: on.",
    )
    rr.add_argument(
        "--no-row-reverser",
        dest="row_reverser",
        action="store_false",
        default=None,
        help="Omit top-row reverser overlay.",
    )
    p.add_argument(
        "--no-top-row-cyan-waypoints",
        action="store_true",
        help="Omit cyan waypoint markers + temp labels on outer row A (preview only).",
    )
    p.add_argument(
        "--no-neck-cyan-waypoints",
        action="store_true",
        help="Omit cyan neck (stem straddle) waypoint markers (preview only).",
    )
    tb = p.add_mutually_exclusive_group()
    tb.add_argument(
        "--top-only",
        action="store_true",
        help="Preview only: Top copper only — cyan strokes (row-reverser, stubs, top-row, neck); "
        "hide Bottom (red).",
    )
    tb.add_argument(
        "--bottom-only",
        action="store_true",
        help="Preview only: Bottom copper — red row-reverser strokes; hide Top (cyan). "
        "Discrete red markers on the J3 straddle (same spots as cyan J3 neck) unless "
        "--no-neck-cyan-waypoints.",
    )
    args = p.parse_args()
    profile = None
    if args.profile is not None:
        profile = load_board_profile(args.profile)
    elif args.board is not None:
        path = boards_dir(_ROOT) / f"{args.board}.toml"
        profile = load_board_profile(path)

    if args.pins is None and profile is None:
        p.error("Specify --pins, or --profile PATH, or --board NAME")

    bp = resolve_board_params(
        profile,
        pins=args.pins,
        rows_top=args.rows_top,
        rows_bottom=args.rows_bottom,
        omit_row_b_gap_adjacent=args.omit_row_b_gap_adjacent,
    )
    if profile is not None and bp.n_pins < profile.device_min_pins:
        print(
            f"Note: adapter_pins={bp.n_pins} < device_min_pins="
            f"{profile.device_min_pins} (partial vs device).",
            file=sys.stderr,
        )
    out = args.out
    if out is None:
        prev = Path("out/preview")
        if args.board is not None:
            out = prev / f"{args.board}.svg"
        elif args.profile is not None:
            out = prev / f"{args.profile.stem}.svg"
        else:
            out = prev / f"board-{bp.n_pins}pin.svg"

    silk_mode = args.silk
    if silk_mode == "auto":
        silk_mode = _auto_silk_mode(profile)
    silk_dir = args.silk_dir
    if silk_dir is None:
        silk_dir = _ROOT / "out" / "intermediate" / "silk"
    else:
        silk_dir = silk_dir.resolve()

    branding = None
    if (
        profile is not None
        and profile.branding is not None
        and not args.no_branding
    ):
        branding = profile.branding

    if args.row_reverser is not None:
        row_reverser = args.row_reverser
    else:
        row_reverser = True

    silk_gpio_paths_json = (
        profile.silk_gpio_paths_json if profile is not None else None
    )

    if args.top_only:
        preview_traces = "top"
    elif args.bottom_only:
        preview_traces = "bottom"
    else:
        preview_traces = "both"

    emit_board_svg(
        bp,
        out,
        silk_mode=None if silk_mode == "none" else silk_mode,
        silk_dir=silk_dir,
        branding=branding,
        row_reverser=row_reverser,
        silk_gpio_paths_json=silk_gpio_paths_json,
        top_row_cyan_waypoints=not args.no_top_row_cyan_waypoints,
        neck_cyan_waypoints=not args.no_neck_cyan_waypoints,
        preview_traces=preview_traces,
    )
    print(out.resolve())


if __name__ == "__main__":
    main()
