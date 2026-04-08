#!/usr/bin/env python3
"""
Bake EasyEDA silk path JSON (matplotlib TextPath → ``d`` strings).

Requires **matplotlib**. Re-executes with ``repo/.venv/bin/python`` when needed
(see ``adapter_gen._venv_bootstrap``).

**Vendor GPIO silk** (per-pin J1/J3 names) is driven by ``[silk_bake]`` in each
``resources/boards/<board>.toml`` (``j1_labels``, ``j3_labels``, ``output``, …).

**Numeric silk** (logical 1…N) is ``numeric_silk_paths.json`` (default max pin 44).

Writes under ``out/intermediate/silk/`` (gitignored).

Examples (repo root)::

  ./scripts/bake_devkitc_gpio_silk_paths.py --all
  ./scripts/bake_devkitc_gpio_silk_paths.py --board esp32-s3-devkitc-1
  ./scripts/bake_devkitc_gpio_silk_paths.py --numeric-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adapter_gen._venv_bootstrap import ensure_matplotlib  # noqa: E402

ensure_matplotlib()

from adapter_gen.board_profile import boards_dir  # noqa: E402
from adapter_gen.silk_bake import (  # noqa: E402
    bake_gpio_from_board_toml,
    iter_board_tomls_with_silk_bake,
    write_numeric_silk_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Bake silk path JSON for adapter previews and EasyEDA generator "
            "(GPIO labels from board TOML [silk_bake]; numeric 1..N)."
        )
    )
    ap.add_argument(
        "--board",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Bake GPIO silk for resources/boards/<NAME>.toml (must define [silk_bake])."
        ),
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help=(
            "Bake numeric silk + GPIO silk for each board TOML with [silk_bake].output."
        ),
    )
    ap.add_argument(
        "--numeric-only",
        action="store_true",
        help="Only write numeric_silk_paths.json.",
    )
    ap.add_argument(
        "--max-pin",
        type=int,
        default=44,
        metavar="N",
        help="Largest string key in numeric silk (default 44).",
    )
    args = ap.parse_args()

    silk_dir = _REPO_ROOT / "out" / "intermediate" / "silk"
    silk_dir.mkdir(parents=True, exist_ok=True)
    out_num = silk_dir / "numeric_silk_paths.json"

    if args.numeric_only:
        write_numeric_silk_json(out_num, max_pin=args.max_pin)
        print(out_num.resolve())
        return

    if args.board:
        path = boards_dir(_REPO_ROOT) / f"{args.board}.toml"
        if not path.is_file():
            print(f"Board profile not found: {path}", file=sys.stderr)
            raise SystemExit(1)
        p = bake_gpio_from_board_toml(path, silk_dir)
        print(p.resolve(), "GPIO silk")
        write_numeric_silk_json(out_num, max_pin=args.max_pin)
        print(out_num.resolve(), "numeric")
        return

    if args.all:
        write_numeric_silk_json(out_num, max_pin=args.max_pin)
        print(out_num.resolve(), "numeric")
        for path in iter_board_tomls_with_silk_bake(boards_dir(_REPO_ROOT)):
            p = bake_gpio_from_board_toml(path, silk_dir)
            print(p.resolve(), f"from {path.name}")
        return

    # Default: same as --all (numeric + every [silk_bake] board).
    write_numeric_silk_json(out_num, max_pin=args.max_pin)
    print(out_num.resolve(), "numeric")
    for path in iter_board_tomls_with_silk_bake(boards_dir(_REPO_ROOT)):
        p = bake_gpio_from_board_toml(path, silk_dir)
        print(p.resolve(), f"from {path.name}")


if __name__ == "__main__":
    main()
