# Python: clean code standards (this repo)

Audience: humans and tooling. Goal: code that is **correct**, **readable**, **maintainable**, and **safe to change**—especially for geometry, silk, and export paths where silent mistakes become bad boards.

For a **phased checklist** (tooling, hygiene, types, DRY), see **[python-clean-code-tracker.md](python-clean-code-tracker.md)**.

---

## 1. Non‑negotiables

### DRY (Don’t Repeat Yourself)

- **One source of truth** for numbers that must match across preview, EasyEDA export, and docs (e.g. layout in `adapter_gen/geometry.py` and shared helpers, not copy‑pasted literals).
- **Extract** repeated logic when the third similar block appears, or when two call sites must stay in lockstep (same bug in two places is worse than one abstraction).
- **DRY is not deduplication at any cost**: if two things only look similar but represent different domains or invariants, **keep them separate** and name the difference (see `docs/adapter-routing-invariants.md`).

### Dead code and clutter

- Remove **unused imports**, **unreachable branches**, **commented‑out blocks** kept “just in case”, and **orphaned** modules not referenced by scripts, tests, or package entry points.
- Prefer **deleting** over `# unused`—git remembers history.
- If something is kept intentionally (e.g. alternate algorithm), add a **one‑line comment** saying *why* it exists or link an issue.

### Documentation (docstrings / “pydoc”)

- **Public** functions, classes, and important module constants: a **docstring** that answers *what*, *inputs/outputs*, and *invariants or units* when non‑obvious (e.g. “mil, +Y down”).
- **Private** helpers (`_foo`): docstring if behavior is subtle; otherwise a short comment at the call site is enough.
- Prefer **imperative summary line** + blank line + details (PEP 257 style), not essays.
- Module docstring: **one paragraph** on purpose and key conventions (coordinate system, layer names).

### Type hints

- **Annotate** public APIs and shared helpers: parameters and return types.
- Use `from __future__ import annotations` where forward refs help.
- Prefer **`typing`** / **`collections.abc`** (`Sequence`, `Mapping`, `Callable`) over concrete list/dict when you only iterate or read.
- Use **`TypedDict`**, **`Protocol`**, or **`@dataclass`** when a dict/tuple shape is stable and reused.
- Run **mypy** (or the project’s configured checker) before large merges when touching core geometry or export code.

---

## 2. Structure and style

- **Imports**: stdlib, third party, local; alphabetical within groups where practical.
- **Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants; module names short and descriptive.
- **Line length**: follow project flake8 (e.g. 79) unless the team agrees otherwise—break long signatures and comprehensions.
- **Exceptions**: catch **specific** types; avoid bare `except:`; don’t swallow errors without logging or re‑raising with context.
- **Early returns** reduce nesting; **guard clauses** at the top of functions for invalid inputs.

---

## 3. Domain‑specific (this project)

- **Electrical / geometry**: never “tidy” copper or preview paths in ways that could merge distinct nets without explicit intent—see `.cursor/rules/no-assumed-short-circuits.mdc` and `docs/adapter-routing-invariants.md`.
- **Units**: state **mil** vs EasyEDA file units (0.1 mil) in docstrings where conversion happens.
- **Preview vs EasyEDA generator**: a **project goal** is to share as much code as possible so the SVG preview matches export—see **`docs/preview-generator-parity.md`** (this is broader than “clean code”; it is about **one source of truth** for layout and routing).

---

## 4. Optional practices — choose what to adopt

Use this as a checklist; turn items on by team agreement and CI.

| Practice | Benefit | Cost |
|----------|---------|------|
| **Ruff** (lint + format) | Fast, consistent style, import sorting | Config + CI hook |
| **Black** or **Ruff format** | No bike‑shedding formatting | Occasional large diffs |
| **mypy --strict** (incremental) | Fewer runtime surprises in large refactors | Time fixing legacy gaps |
| **pre-commit** | Catches issues before push | Local install |
| **pytest + coverage threshold** on `adapter_gen/` | Regressions caught early | Test maintenance |
| **`__slots__`** on hot dataclasses | Memory / attr typos | Less dynamic flexibility |
| **frozen `@dataclass`** for immutable params (`BoardParams`) | Clearer contracts | Boilerplate |
| **`Protocol`** for “file‑like” or “emit callback” | Easier testing/mocking | Indirection |
| **Structured logging** (`logging` + context) vs `print` in library code | Debuggable production paths | Migration effort |
| **Versioned schema** for JSON/TOML (you already use `schema = 1` in TOML) | Safer evolution | Migration notes |

### Stricter doc / typing (optional)

| Item | Notes |
|------|--------|
| **Google or NumPy docstring style** | Machine‑readable sections (`Args`, `Returns`, `Raises`). |
| **`TypedDict` for JSON blobs** | After `json.loads`, validate shape in one place. |
| **Explicit `-> None`** | On all procedures; helps mypy and readers. |

### Performance (only if profiled)

| Item | When |
|------|------|
| **Avoid repeated layout work in tight loops** | Cache `stem_layout_mil(p)` per `BoardParams` in a hot path. |
| **`__slots__` / maps pre‑built** | Only after profiling shows need. |

---

## 5. PR / review checklist (short)

- [ ] No dead code or stray prints in library modules.
- [ ] New public API has types + docstring (units if relevant).
- [ ] Duplication questioned: should this share a helper?
- [ ] Geometry/copper changes: routing invariants still hold.
- [ ] Tests or manual script run noted in PR if behavior‑visible.

---

## 6. References

- PEP 8 — Style Guide for Python Code  
- PEP 257 — Docstring Conventions  
- PEP 484 / 585 — Type hints  
