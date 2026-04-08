#!/usr/bin/env python3
"""Rebuild ``out/`` from all board TOMLs and compare SHA256 checksums to a stored baseline.

Typical workflow::

  # After intentional output changes (new geometry, new boards, …):
  ./scripts/verify_board_outputs.py --update-baseline

  # CI / local regression check:
  ./scripts/verify_board_outputs.py

Baseline file: ``tests/baselines/out_manifest.sha256`` (repo-relative paths, UTF-8).
Checksums cover **baked silk** (``out/intermediate/silk/*.json``), **SVG previews**, and
**EasyEDA Standard JSON**. For ``*.json`` files, the hash is SHA256 of **canonical JSON**
(UTF-8, sorted object keys, compact separators) so the same semantic bake output matches
even if key order or whitespace differs.

**Determinism:** Outputs include matplotlib-generated silk/branding. Use ``--no-branding`` for
fewer moving parts (font/renderer differences across machines). Full baseline may need
refresh when Python, matplotlib, or pinned deps change.

Run from the repository root (same as other ``scripts/*.py``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BASELINE_REL = Path("tests/baselines/out_manifest.sha256")

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adapter_gen.board_profile import boards_dir, load_board_profile  # noqa: E402


def _silk_mode_and_labels(silk_profile: str | None) -> tuple[str, str]:
    """Preview ``--silk`` mode and generator ``--silk-labels`` for a profile."""
    if silk_profile == "devkitc1":
        return "devkitc1", "devkitc1"
    if silk_profile in ("numeric", "generic"):
        return "numeric", "numeric"
    return "none", "none"


def _iter_board_tomls(repo: Path) -> list[Path]:
    d = boards_dir(repo)
    return sorted(d.glob("*.toml"), key=lambda p: p.name.lower())


def _digest_for_baseline(path: Path) -> str:
    """SHA256 of file bytes, except ``*.json`` uses canonical JSON (sorted keys)."""
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        canon = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_out_files(out_dir: Path) -> list[Path]:
    """Baked silk JSON, previews, and EasyEDA Standard JSON under ``out/``."""
    if not out_dir.is_dir():
        return []
    files: list[Path] = []
    silk = out_dir / "intermediate" / "silk"
    if silk.is_dir():
        files.extend(sorted(silk.glob("*.json")))
    for pattern, root in (
        ("*.svg", out_dir / "preview"),
        ("*.standard.json", out_dir / "easyeda"),
    ):
        if not root.is_dir():
            continue
        files.extend(root.glob(pattern))
    return sorted(set(files), key=lambda p: p.as_posix().lower())


def _manifest_lines(repo: Path, files: Iterable[Path]) -> list[str]:
    lines: list[str] = []
    for path in sorted(files, key=lambda p: p.as_posix().lower()):
        rel = path.relative_to(repo).as_posix()
        digest = _digest_for_baseline(path)
        lines.append(f"{digest}  {rel}")
    return lines


def _parse_baseline(text: str) -> dict[str, str]:
    """Map repo-relative posix path -> hex digest."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, rel = parts
        rel = rel.replace("\\", "/")
        out[rel] = digest.lower()
    return out


def _run_script(repo: Path, script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(repo / "scripts" / script), *args]
    subprocess.run(cmd, cwd=repo, check=True)


def _regenerate_all(repo: Path, *, no_branding: bool) -> None:
    out = repo / "out"
    if out.exists():
        shutil.rmtree(out)

    _run_script(repo, "bake_devkitc_gpio_silk_paths.py", ["--all"])

    extra: list[str] = []
    if no_branding:
        extra.append("--no-branding")

    for toml in _iter_board_tomls(repo):
        prof = load_board_profile(toml)
        stem = toml.stem
        silk_mode, silk_labels = _silk_mode_and_labels(prof.silk_profile)

        _run_script(
            repo,
            "preview_adapter_board.py",
            ["--board", stem, "--silk", silk_mode, *extra],
        )
        _run_script(
            repo,
            "generate_easyeda_adapter_pcb.py",
            ["--board", stem, "--silk-labels", silk_labels, *extra],
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Delete out/, bake silk, run preview + EasyEDA generator for each board TOML, "
            "then compare SHA256 checksums to tests/baselines/out_manifest.sha256."
        )
    )
    ap.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write tests/baselines/out_manifest.sha256 from current outputs (run after intentional changes).",
    )
    ap.add_argument(
        "--no-branding",
        action="store_true",
        help="Pass --no-branding to preview and generator (more stable across environments).",
    )
    ap.add_argument(
        "--skip-delete-out",
        action="store_true",
        help="Do not remove out/ before running (for debugging; baseline compare may be wrong).",
    )
    args = ap.parse_args()
    repo = _REPO_ROOT
    out_dir = repo / "out"
    baseline_path = repo / _BASELINE_REL

    if not args.skip_delete_out:
        _regenerate_all(repo, no_branding=args.no_branding)
    else:
        # Still ensure bake + board runs — user asked to skip only delete
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        _run_script(repo, "bake_devkitc_gpio_silk_paths.py", ["--all"])
        extra: list[str] = []
        if args.no_branding:
            extra.append("--no-branding")
        for toml in _iter_board_tomls(repo):
            prof = load_board_profile(toml)
            stem = toml.stem
            silk_mode, silk_labels = _silk_mode_and_labels(prof.silk_profile)
            _run_script(
                repo,
                "preview_adapter_board.py",
                ["--board", stem, "--silk", silk_mode, *extra],
            )
            _run_script(
                repo,
                "generate_easyeda_adapter_pcb.py",
                ["--board", stem, "--silk-labels", silk_labels, *extra],
            )

    files = _collect_out_files(out_dir)
    if not files:
        print("No files under out/ — nothing to checksum.", file=sys.stderr)
        return 1

    lines = _manifest_lines(repo, files)

    if args.update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "# SHA256 of outputs under out/ (repo-relative paths, two spaces after digest).\n"
            "# JSON files: hash of canonical JSON (sorted keys); SVG: raw file bytes.\n"
            "# Regenerate: scripts/verify_board_outputs.py --update-baseline\n"
        )
        baseline_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {len(lines)} entries to {_BASELINE_REL.as_posix()}")
        return 0

    if not baseline_path.is_file():
        print(
            f"Missing baseline {_BASELINE_REL} — run:\n"
            f"  {sys.executable} scripts/verify_board_outputs.py --update-baseline",
            file=sys.stderr,
        )
        return 1

    expected = _parse_baseline(baseline_path.read_text(encoding="utf-8"))
    actual: dict[str, str] = {}
    for line in lines:
        digest, rel = line.split("  ", 1)
        actual[rel] = digest.lower()

    missing = sorted(set(expected) - set(actual))
    extra_paths = sorted(set(actual) - set(expected))
    mismatches: list[tuple[str, str, str]] = []

    for rel, exp_digest in sorted(expected.items()):
        if rel not in actual:
            continue
        if actual[rel] != exp_digest:
            mismatches.append((rel, exp_digest, actual[rel]))

    if missing or extra_paths or mismatches:
        print("Baseline mismatch.", file=sys.stderr)
        for rel in missing:
            print(f"  MISSING (in baseline, not on disk): {rel}", file=sys.stderr)
        for rel in extra_paths:
            print(f"  EXTRA (on disk, not in baseline): {rel}", file=sys.stderr)
        for rel, want, got in mismatches:
            print(f"  DIFF {rel}", file=sys.stderr)
            print(f"    expected {want}", file=sys.stderr)
            print(f"    actual   {got}", file=sys.stderr)
        return 1

    print(f"OK — {len(actual)} files match {_BASELINE_REL.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
