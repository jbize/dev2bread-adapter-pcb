#!/usr/bin/env python3
"""
Render a PNG catalog of every font **family** Matplotlib can resolve on this machine.

Matplotlib does not ship a visual font gallery; use this to pick ``font_family`` for
``[branding]`` in board TOML (same stack as silk/branding).

**Usage** (repo root; ``.venv`` via ``ensure_matplotlib`` if needed)::

  ./scripts/preview_matplotlib_fonts.py
  ./scripts/preview_matplotlib_fonts.py --sample "The quick brown fox"
  ./scripts/preview_matplotlib_fonts.py -o /tmp/fonts.png
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapter_gen._venv_bootstrap import ensure_matplotlib  # noqa: E402

ensure_matplotlib()

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import fontManager  # noqa: E402


def _likely_text_family(name: str) -> bool:
    """Heuristic: skip obvious symbol/math-only faces for the ``--text-only`` gallery."""
    n = name.lower()
    if n.startswith("cm") and len(name) <= 6:
        return False
    for bad in (
        "mathjax",
        "stix",
        "symbol",
        "d050000l",
        "open symbol",
    ):
        if bad in n:
            return False
    return True


def main() -> None:
    p = argparse.ArgumentParser(
        description="Write a PNG showing each Matplotlib font family with sample text.",
    )
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=_ROOT / "out" / "preview" / "matplotlib-fonts-sample.png",
        metavar="FILE",
        help="Output PNG (default: out/preview/matplotlib-fonts-sample.png).",
    )
    p.add_argument(
        "--text-only",
        action="store_true",
        help="Only list families that look like normal text faces "
        "(skip many symbol/math fonts).",
    )
    p.add_argument(
        "--sample",
        default="Godswind Consulting",
        metavar="TEXT",
        help="String drawn in each face (default: Godswind Consulting).",
    )
    args = p.parse_args()

    families = sorted({f.name for f in fontManager.ttflist})
    if args.text_only:
        families = [f for f in families if _likely_text_family(f)]
    n = len(families)
    line_h = 0.32
    fig_h = max(6.0, n * line_h)
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n)
    ax.axis("off")
    ax.set_title(
        f"Matplotlib font families on this machine ({n} total)",
        fontsize=12,
        pad=16,
    )

    for i, fam in enumerate(families):
        y = n - 1 - i
        # ASCII separator: many math/symbol fonts lack em dash or Latin glyphs.
        label = f"{fam} | {args.sample}"
        try:
            ax.text(
                0.01,
                y + 0.5,
                label,
                family=fam,
                fontsize=11,
                va="center",
            )
        except (ValueError, RuntimeError) as e:
            ax.text(
                0.01,
                y + 0.5,
                f"{fam} | (error: {e})",
                family="DejaVu Sans",
                fontsize=9,
                va="center",
                color="red",
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        fig.savefig(args.out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(args.out.resolve())


if __name__ == "__main__":
    main()
