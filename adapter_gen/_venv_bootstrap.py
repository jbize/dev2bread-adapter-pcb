"""Re-exec the running script with repo ``.venv`` Python when matplotlib is missing.

Used by scripts that need matplotlib (silk paths, branding). Matches the behavior
documented in ``scripts/bake_devkitc_gpio_silk_paths.py``: ``#!/usr/bin/env python3``
follows PATH; if system Python has no matplotlib but ``.venv`` does, we switch to it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REEXEC_ENV = "_DEV2BREAD_MATPLOTLIB_REEXEC"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _venv_python(repo: Path) -> Path | None:
    if sys.platform == "win32":
        cand = repo / ".venv" / "Scripts" / "python.exe"
    else:
        cand = repo / ".venv" / "bin" / "python"
    return cand if cand.is_file() else None


def _print_matplotlib_help() -> None:
    script = Path(sys.argv[0]).name
    print(
        f"{script} requires the third-party package 'matplotlib' "
        "(vector text → paths for EasyEDA silk / branding).\n\n"
        "Install it in a project virtualenv (from the repo root):\n"
        "  python3 -m venv .venv && .venv/bin/pip install matplotlib\n\n"
        "Then run this script again. If .venv exists, it is used automatically when\n"
        "  system Python does not have matplotlib.\n",
        file=sys.stderr,
    )


def ensure_matplotlib() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        pass
    else:
        return

    if os.environ.get(_REEXEC_ENV):
        _print_matplotlib_help()
        raise SystemExit(1)

    vpy = _venv_python(_REPO_ROOT)
    if vpy is not None:
        env = {**os.environ, _REEXEC_ENV: "1"}
        script = Path(sys.argv[0]).resolve()
        os.execve(str(vpy), [str(vpy), str(script)] + sys.argv[1:], env)

    _print_matplotlib_help()
    raise SystemExit(1)
