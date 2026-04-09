# Contributing

Python style, typing, and DRY goals are summarized in **[docs/python-clean-code.md](docs/python-clean-code.md)**. This file captures **what to do before you open or merge a PR** so we stay aligned with that doc and with electrical safety on this PCB project.

---

## Local checks (run from repo root)

**Ruff** uses **`pyproject.toml`** `[tool.ruff]`: pycodestyle **E/W**, **pyflakes**, **isort**, **pyupgrade**, **bugbear**, **simplify**, **comprehensions**, **pie**, **perflint**, **ruf** — with intentional ignores (e.g. `print` in CLIs, unicode in docs, `E501` line length). Run from repo root:

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest -q
```

After layout, silk, bake, or export changes, refresh or run the checksum regression (see **[README.md](README.md)**):

```bash
./scripts/verify_board_outputs.py --no-branding
# If outputs change intentionally:
./scripts/verify_board_outputs.py --update-baseline --no-branding
```

Optional: **`pre-commit install`** then **`pre-commit run -a`** (Ruff only; mypy/pytest stay manual or CI).

---

## PR checklist

Use this when you change **Python**, **geometry**, **copper/preview**, or **EasyEDA export** (same items as **§5** in `docs/python-clean-code.md`):

1. **No dead code** or stray debug prints in library modules (`adapter_gen/`).
2. **New or changed public API** (functions/classes intended for callers): **type hints** + **docstring** — what it does, inputs/outputs, **units** if not obvious (e.g. mil, +Y down, layer id). Private helpers (`_foo`) need a docstring only if behavior is subtle.
3. **Duplication:** ask whether a helper should be shared (see **[docs/preview-generator-parity.md](docs/preview-generator-parity.md)**); do not merge unrelated nets for “cleanliness.”
4. **Geometry / copper / preview SVG / EasyEDA JSON:** routing must respect **[docs/adapter-routing-invariants.md](docs/adapter-routing-invariants.md)**. Do not “tidy” artwork in ways that could short separate nets. When in doubt, stop and clarify.
5. **Behavior-visible changes:** note **tests** run (`pytest`), **`verify_board_outputs`**, and/or manual script steps in the PR description.

---

## References

| Topic | Doc |
|--------|-----|
| Style, DRY, typing | [docs/python-clean-code.md](docs/python-clean-code.md) |
| Preview vs generator parity | [docs/preview-generator-parity.md](docs/preview-generator-parity.md) |
| Module map (geometry → SVG vs EasyEDA) | [docs/architecture-emitters.md](docs/architecture-emitters.md) |
| Routing / electrical intent | [docs/adapter-routing-invariants.md](docs/adapter-routing-invariants.md) |
| Rollout tracker (what we already did) | [docs/python-clean-code-tracker.md](docs/python-clean-code-tracker.md) |

Cursor rule for assistants: **`.cursor/rules/no-assumed-short-circuits.mdc`**.
