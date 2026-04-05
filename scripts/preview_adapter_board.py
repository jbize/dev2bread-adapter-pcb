#!/usr/bin/env python3
"""
Emit SVG preview: board outline + PTH holes (new adapter_gen pipeline).

No copper yet — validates geometry vs N and socket row counts.

**CLI-only** (repo root: ``./scripts/preview_adapter_board.py`` — shebang ``python3``)

  ./scripts/preview_adapter_board.py --pins 44
      # → out/preview/board-44pin.svg

**Board profile (TOML)** — default ``-o`` is ``out/preview/<board>.svg``::

  ./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1
  ./scripts/preview_adapter_board.py --profile resources/boards/example-14pin-7-per-row.toml

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

try:
    from adapter_gen.board_profile import (  # noqa: E402
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
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        metavar="FILE",
        help="Output SVG (default: out/preview/<name>.svg from --board or --profile "
        "stem, else out/preview/board-<N>pin.svg).",
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
    emit_board_svg(bp, out)
    print(out.resolve())


if __name__ == "__main__":
    main()
