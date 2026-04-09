# dev2bread-adapter-pcb

T-shaped **44-pin** adapter PCB: wide head for a development board (e.g. ESP32 class, ~1.1″ row spacing) and narrow stem for a solderless breadboard (~0.5″ straddle). **1:1** routing (logical pin 1→1 … 44→44).

This repository holds the **EasyEDA Standard** generator, documentation, and **static** assets under **`resources/`**. **Generated** outputs go under **`out/`** (gitignored — run the scripts locally): **`out/preview/`** (SVG previews), **`out/easyeda/`** (importable PCB JSON), **`out/intermediate/silk/`** (baked silk path cache — not a board file).

## Quick start

```bash
./scripts/bake_devkitc_gpio_silk_paths.py --all   # numeric silk + GPIO silk for each board TOML with [silk_bake]
./scripts/generate_easyeda_adapter_pcb.py --board esp32-s3-devkitc-1 --silk-labels devkitc1
./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1
```

Bake uses **`.venv`** automatically if system Python lacks **matplotlib**. Per-board vendor labels are defined under **`[silk_bake]`** in **`resources/boards/<name>.toml`** (`output`, `j1_labels`, `j3_labels`, …). Use **`--board NAME`** to bake one profile, **`--numeric-only`** for logical 1…N only.

### ESP32 DevKit V1 (30-pin)

Board profile: **`resources/boards/esp32-devkit-v1.toml`** (vendor pin names under **`[silk_bake]`**, optional **`[branding]`**). Run these from the repo root, in order:

1. **Generate the silk label layers** — bakes GPIO text paths into **`out/intermediate/silk/`** (required before preview or PCB JSON with vendor labels):

   ```bash
   ./scripts/bake_devkitc_gpio_silk_paths.py --board esp32-devkit-v1
   ```

2. **Review the layout** — SVG with silk labels and branding from the TOML (output **`out/preview/esp32-devkit-v1.svg`**):

   ```bash
   ./scripts/preview_adapter_board.py --board esp32-devkit-v1 --silk auto
   ```

   Pass **`--no-branding`** if you want outline and silk only, without the **`[branding]`** image and text.

3. **Generate the EasyEDA board** — Standard JSON with copper, silk labels, and branding (default is to include branding; use **`--no-branding`** to omit):

   ```bash
   ./scripts/generate_easyeda_adapter_pcb.py --board esp32-devkit-v1 --silk-labels devkitc1
   ```

   Typical output: **`out/easyeda/esp32-devkit-v1.devkitc1.standard.json`**. Import that file in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**.

Ensure **`[branding].image`** in the TOML points at a real file under **`resources/images/`** if you expect the bitmap on the board and in previews.

Scripts are executable and use `#!/usr/bin/env python3`. Import `out/easyeda/<board>.*.standard.json` (e.g. `esp32-s3-devkitc-1.devkitc1.standard.json`) in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**, then export Gerbers for your fab. Omit **`--board`** to keep the legacy default filenames (`easyeda-adapter-44pin-dev2bread.*`).

Full detail: **[docs/dev2bread-adapter-pcb.md](docs/dev2bread-adapter-pcb.md)** (includes a short **SVG preview** subsection). For **AI / handoff / picking up later** (terminology, silk modes, TOML vs silk vs copper, which `.py` files are new vs legacy, pitfalls): **[docs/PROMPT_CONTEXT.md](docs/PROMPT_CONTEXT.md)** — start with **“Picking up later (resume checklist)”** there.

**`resources/images/`** holds reference photos (e.g. DevKit module, **breadboard misfitment**). Optional **silk artwork** for bitmap branding in EasyEDA can live there too.

### Contributing

Before a PR: **[CONTRIBUTING.md](CONTRIBUTING.md)** (PR checklist, routing invariant links, local **`ruff` / `mypy` / `pytest` / `verify_board_outputs`** commands).

### Lint (local + CI)

Python **3.11+**. With a venv (e.g. **`.venv`** at the repo root):

```bash
pip install -e ".[dev]"   # ruff + mypy + pre-commit
ruff check .
ruff format --check .
mypy   # adapter_gen/ + scripts/ (see [tool.mypy] in pyproject.toml)
pytest -q   # unit tests under tests/ (pure helpers)
pre-commit install   # once per clone; runs ruff + ruff format from .pre-commit-config.yaml
```

GitHub Actions runs **`ruff`**, **`mypy`**, **`pytest`**, and the output verification job on push and pull requests (pre-commit is optional locally). Standards: **[docs/python-clean-code.md](docs/python-clean-code.md)**. Phased rollout checklist: **[docs/python-clean-code-tracker.md](docs/python-clean-code-tracker.md)**.

**Regression checksums (bake + preview + EasyEDA for every board TOML):** after deleting **`out/`**, the script runs **`bake_devkitc_gpio_silk_paths.py --all`**, then **`preview_adapter_board.py`** and **`generate_easyeda_adapter_pcb.py`** per profile. It compares SHA256s to **`tests/baselines/out_manifest.sha256`**: raw bytes for **`.svg`**, and for **`.json`** a hash of **canonical JSON** (sorted keys) so baked silk under **`out/intermediate/silk/`** is verified even if key order differs. Refresh the baseline when outputs change on purpose:

```bash
./scripts/verify_board_outputs.py --update-baseline --no-branding   # stable; omits [branding] bitmap/text
./scripts/verify_board_outputs.py --no-branding                     # check against baseline
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify_board_outputs.py` | Delete **`out/`**, bake silk, regenerate previews + Standard JSON for all **`resources/boards/*.toml`**, compare SHA256 to **`tests/baselines/out_manifest.sha256`**. |
| `scripts/generate_easyeda_adapter_pcb.py` | Emit EasyEDA Standard PCB JSON (outline, pads, row-reverser Top/Bottom **TRACK**s, silk, branding). Use **`--no-row-reverser`** to omit reverser copper. |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Regenerate **`numeric_silk_paths.json`** and GPIO silk JSON from **`[silk_bake]`** in board TOMLs (needs **matplotlib**). |
| `scripts/preview_adapter_board.py` | Board outline, holes, optional silk overlay, optional branding (SVG). |

### SVG preview (`preview_adapter_board.py`)

Run from the repo root. Silk JSON must exist under **`out/intermediate/silk/`** (run **`./scripts/bake_devkitc_gpio_silk_paths.py --all`** once, or **`--board <name>`** for a single profile). Branding uses the board TOML **`[branding]`** block and needs **matplotlib** (the script may use **`.venv`** automatically, same idea as the bake script). Omit **`--no-branding`** to include branding.

| What you want | Command |
|-----------------|---------|
| **DevKitC-style GPIO silk** + branding (profile default) | `./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1 --silk auto` or `--silk devkitc1` |
| **Numeric 1…N** silk + branding (generic indices, not vendor GPIO names) | `./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1 --silk numeric` |
| **Silk profile from TOML only** | `./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1 --silk auto` — uses **`silk_profile`** in **`resources/boards/<name>.toml`** (`devkitc1` → devkitc GPIO paths; **`generic`** / **`numeric`** in TOML map to the numeric silk JSON). To force numeric labels while keeping a **`devkitc1`** profile in the file, pass **`--silk numeric`** explicitly. |

Default output path: **`out/preview/<board>.svg`** (override with **`-o`**). Use **`--no-branding`** to omit **`[branding]`** even when it is defined in the profile.

See also **`scripts/preview_adapter_board.py`** module docstring and **`--help`**.
