# Python clean-code rollout (tracker)

Companion to **[python-clean-code.md](python-clean-code.md)**. Use this as a **step-by-step** checklist; update boxes as you complete work (or move items to GitHub Issues if you prefer issue numbers over doc edits).

---

## Phase 1 — Tooling baseline

- [x] `pyproject.toml` with `[tool.ruff]` (lint + format settings)
- [x] `ruff check .` clean (E4/E7/E9/F/I; E402 ignored for `sys.path` scripts)
- [x] `ruff format` applied across Python sources
- [x] CI runs `ruff check` + `ruff format --check` on push/PR
- [x] Optional: `[dev]` extras — `pip install -e ".[dev]"` for local ruff (see root `pyproject.toml`)
- [ ] Optional: **pre-commit** hook (same commands as CI)

**Local commands (repo root):**

```bash
pip install -e ".[dev]"   # or: pip install ruff
ruff check .
ruff format --check .
```

---

## Phase 2 — Hygiene (no behavior change)

- [ ] Sweep **unused imports / dead locals** when ruff flags them (or enable stricter F rules if needed)
- [ ] Remove **commented-out** blocks and stray debug prints in library modules (`adapter_gen/`)
- [ ] Confirm no **orphaned** `.py` files (nothing imports or runs them)

---

## Phase 3 — Types (incremental)

- [ ] Add **`[tool.mypy]`** (or separate `mypy.ini`) with a **narrow** first target (e.g. `adapter_gen/geometry.py`)
- [ ] Fix errors **module by module**; avoid `--strict` on day one for the whole tree
- [ ] Document in this tracker which packages are **typed** vs **best-effort**

---

## Phase 4 — DRY / preview–export parity

- [ ] Read **[preview-generator-parity.md](preview-generator-parity.md)** and list concrete shared-helper opportunities
- [ ] Extract **duplicated mil constants** into `geometry` or shared routing modules (no “tidy” that merges distinct nets)
- [ ] Re-run preview + EasyEDA generation smoke tests after each meaningful extraction

---

## Phase 5 — Docs & review habit

- [ ] New **public** APIs: docstring + types per `python-clean-code.md`
- [ ] PRs touching copper/preview: **routing invariants** checklist (`adapter-routing-invariants.md`, `.cursor/rules/…`)

---

## Quick reference: PR checklist (from python-clean-code.md §5)

- [ ] No dead code or stray prints in library modules  
- [ ] New public API has types + docstring (units if relevant)  
- [ ] Duplication questioned: should this share a helper?  
- [ ] Geometry/copper changes: routing invariants still hold  
- [ ] Tests or manual script run noted in PR if behavior-visible  
