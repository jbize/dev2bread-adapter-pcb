# Python clean-code rollout (tracker)

Companion to **[python-clean-code.md](python-clean-code.md)**. Use this as a **step-by-step** checklist; update boxes as you complete work (or move items to GitHub Issues if you prefer issue numbers over doc edits).

---

## Phase 1 — Tooling baseline

- [x] `pyproject.toml` with `[tool.ruff]` (lint + format settings)
- [x] `ruff check .` clean (E4/E7/E9/F/I; E402 ignored for `sys.path` scripts)
- [x] `ruff format` applied across Python sources
- [x] CI runs `ruff check` + `ruff format --check` on push/PR
- [x] Optional: `[dev]` extras — `pip install -e ".[dev]"` for local ruff (see root `pyproject.toml`)
- [x] Optional: **pre-commit** — `.pre-commit-config.yaml` runs **ruff** + **ruff format** (`pip install pre-commit && pre-commit install`). **mypy** stays CI/local only (same as full `mypy` in workflow).

**Local commands (repo root):**

```bash
pip install -e ".[dev]"   # ruff + mypy + pytest
ruff check .
ruff format --check .
mypy
pytest -q
pre-commit run -a   # optional; requires: pip install pre-commit && pre-commit install
```

---

## Phase 2 — Hygiene (no behavior change)

- [x] Sweep **unused imports / dead locals** — `ruff check --select F` clean on `adapter_gen/` + `scripts/`
- [x] Remove **commented-out** blocks and stray debug prints — no large commented blocks found; `print` in `adapter_gen/` is intentional user messaging (warnings / import help)
- [x] Confirm no **orphaned** `.py` files — each module is imported from previews, emitters, or run as a script (see `README` / `PROMPT_CONTEXT.md`)

---

## Phase 3 — Types (incremental)

- [x] **`[tool.mypy]`** — `files = ["adapter_gen", "scripts"]`; **`mypy`** in CI (no args). Whole tree **mypy-clean** at default settings (not `--strict`).

---

## Phase 4 — DRY / preview–export parity

- [x] Read **[preview-generator-parity.md](preview-generator-parity.md)** — parity table (outline/geometry, row reverser, stem neck, silk, baked JSON) drives where to share code next; no duplicate work item list here
- [x] Extract **duplicated mil constants** where obvious (trace width/gap; board-ID helpers; **`ROUTING_VIA_*_MIL`** in `easyeda_layers.py`; **`BOARD_ID_CLEARANCE_ABOVE_STEM_PADS_MIL`** in `silk_preview.py`)
- [x] **`pytest`** on pure helpers (`tests/test_board_id_offsets.py`) + CI step
- [x] **`verify_board_outputs.py --no-branding`** after DRY changes (CI + local regression)

---

## Phase 5 — Docs & review habit

- [x] **Public APIs + PR habit** documented in **[CONTRIBUTING.md](../CONTRIBUTING.md)** (docstrings/types for new/changed public symbols; routing invariant links; same checklist as `python-clean-code.md` §5)
- [x] **Copper / preview / PRs** — use **CONTRIBUTING.md** + **[adapter-routing-invariants.md](adapter-routing-invariants.md)** at review time (see also **`.cursor/rules/no-assumed-short-circuits.mdc`**)

---

## Quick reference: PR checklist

**Use [CONTRIBUTING.md](../CONTRIBUTING.md#pr-checklist)** (mirrors **§5** in [python-clean-code.md](python-clean-code.md)).
