# Context for AI / future sessions

Use this file when continuing work on **dev2bread-adapter-pcb** in a new chat or tool. It summarizes goals, decisions, and jargon from earlier design discussions (including the thread that led to splitting this repo from a PlatformIO firmware project).

## What this repository is

- **Hardware:** A **44-pin** “dev-to-breadboard” **T-shaped** PCB: **wide head** (~1.1″ between rows) for a wide dev board (ESP32-S3-DevKitC-1 class), **narrow stem** (~0.5″ straddle) for a standard solderless breadboard.
- **Electrical:** **1:1** routing — logical pin **1→1 … 44→44** (one net per index from head to stem). Same mapping on both ends; no crossbar logic.
- **Geometry:** Head rows parallel to **+X**; stem **rotated 90°** in-plane so the 22-pin direction runs **along the stem** (matches common commercial “Dev2Bread” style). Outline is a **T** (`STEM_OUTLINE_MARGIN`, `HEAD_OUTLINE_EXTRA`, etc. in `scripts/generate_easyeda_adapter_pcb.py`).
- **Wide head depth:** **Four** 0.1″-spaced holes per column per side (breadboard-like), **same net**, short vertical links; route from **innermost** pad to stem. **Five** holes were intentionally omitted — the fifth would be essentially the straddle row; boards that narrow don’t need this adapter.
- **Outputs:** **EasyEDA Standard** compressed JSON (`head.docType` 3, `shape[]` tilde strings). **Not** raw Gerber — import in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**, then **export Gerber + drill** for fabs. Do **not** rely on **File Source → Apply** with expanded TRACK/PAD JSON in Pro (expects different format → “Invalid format”).

## Terminology (docs + code)

- **Stem** — narrow breadboard plug-in section (T-shape / mushroom-cap analogy). Code uses `stem_*`, `STEM_OUTLINE_MARGIN`.
- **Neck** — informal synonym (guitar/bottle); **not** the same as `NECK_GAP` (gap **between** wide pads and stem pad block along **+Y**).
- **Head** — wide ESP32 / dev-board side.

## Silkscreen modes (CLI)

Per-pin silk uses **vector paths** baked into JSON (EasyEDA `TEXT` is stroke paths, not plain strings).

| `--silk-labels` | Meaning | Data file |
|-----------------|---------|-----------|
| `devkitc1` | **ESP32-S3-DevKitC-1 v1.1** J1/J3 signal names (Espressif tables). **Kit-specific** (not other DevKit shapes or revisions); user must orient **J1 → side A**, **J3 → side B**. Two-line **board ID** silk **between the J3 row and the stem** (visible when the stem is in a breadboard). | `out/intermediate/silk/devkitc1_gpio_silk_paths.json` (generated; run bake script) |
| `numeric` | Generic **1–44** (matches logical net / pad numbers). **Not vendor-specific.** | `out/intermediate/silk/numeric_silk_paths.json` (generated; run bake script) |
| `none` | No per-pin text silk (pin-1 **circles** still unless `--no-silk-pin1`). | — |

Default output filenames avoid overwriting variants: `out/easyeda/easyeda-adapter-44pin-dev2bread.<variant>.standard.json` (see `docs/dev2bread-adapter-pcb.md`). **`--all-variants`** writes devkitc1 + numeric defaults.

**Why GPIO silk:** On a breadboard, **logical 1…44** doesn’t match how people think (ESP32 **GPIO** names). DevKitC silk aligns with the **module’s** header naming when the board is oriented correctly.

## Scripts

| Script | When to run |
|--------|----------------|
| `scripts/generate_easyeda_adapter_pcb.py` | **Always** for PCB JSON changes. The script does not import matplotlib; for **`devkitc1` / `numeric` silk**, run **`bake` first** so **`out/intermediate/silk/*.json`** exist. |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Before first **`devkitc1` / `numeric`** generation, and when **regenerating** silk paths (fonts, labels). Needs **venv + matplotlib**. Writes **`out/intermediate/silk/`** (both DevKitC and numeric files). |

## Reference assets in `resources/images/`

- **`esp32-s3-squeeze.jpeg`** — **misfitment** demo: DevKitC-1 too wide; tie points blocked without an adapter.
- **`esp32-S3-N16R8.jpeg`**, **`godswind-east.jpeg`** — module / optional branding artwork references.
- **`ESP32-S3-DevKitC-1.jpeg`** — DevKit module photo reference.

## Repository history

- Split from **`esp32s3-first-project`** so firmware and PCB hardware stay separate. Firmware README links here: **https://github.com/jbize/dev2bread-adapter-pcb**
- This repo is the right place for **adapter PCB**, EasyEDA, silk, and fabrication discussion — **not** the PlatformIO firmware repo.

## Pitfalls to avoid

- Import **Standard compressed** JSON in Pro — not the legacy expanded blob for “File Source Apply.”
- After import: **DRC**, add anything missing (extra silk, fab notes, logos) in the editor, then **Gerber** for the house.
- **DevKitC v1.0 vs v1.1 LED:** GPIO silk follows **v1.1** (RGB LED on **GPIO38**); v1.0 used **GPIO48** for the LED — silk is still about **header** names, not LED wiring.

## Picking up later (resume checklist)

Use this when you have not touched the repo for a while or a new session needs full context.

### Read order

1. **`README.md`** — commands and script names.
2. **This file** (`docs/PROMPT_CONTEXT.md`) — jargon, silk modes, pitfalls.
3. **`docs/dev2bread-adapter-pcb.md`** — geometry constants, CLI details, file outputs.
4. **`docs/design-prompt-breadboard-adapter.md`** — longer-term product / IR / staged-copper design intent (if you are extending the parametric pipeline).

### Python: new pipeline vs legacy EasyEDA generator

| Role | Files |
|------|--------|
| **In play** (parametric geometry + SVG preview) | `adapter_gen/geometry.py`, `adapter_gen/board_profile.py`, `adapter_gen/svg_preview.py`, `adapter_gen/__init__.py`, `scripts/preview_adapter_board.py` |
| **Legacy bridge** (full EasyEDA JSON: copper, routing, silk) | `scripts/generate_easyeda_adapter_pcb.py` — still duplicates most layout constants; only **imports** `adapter_gen` for the **rounded board outline polyline**. Replace when a proper emitter lives under `adapter_gen`. |
| **Silk path baking** (optional pre-step) | `scripts/bake_devkitc_gpio_silk_paths.py` — writes **`out/intermediate/silk/*.json`**; needs **matplotlib**. Not part of `adapter_gen`. |

### Board TOML vs silk labels vs copper nets (keep these separate)

- **`resources/boards/*.toml`** — schema `1`: `id`, `device_min_pins`, `adapter_pins`, `[geometry]` (`n_rows_top` / `n_rows_bottom`), optional **`silk_profile`** string (e.g. `"devkitc1"`). Used by **`preview_adapter_board`** to build **`BoardParams`**. **Does not** contain per-pin name strings like `3V3` or `RST`.
- **Logical / programmatic pins** — nets **`NET1`…`NET44`** (or equivalent indices) in the generator; **1:1** head-to-stem. This is the stable reference for code and copper.
- **Vendor silk text** (what humans read on the PCB) — **not** read from TOML today. **`devkitc1`** names come from **hardcoded lists** in **`bake_devkitc_gpio_silk_paths.py`**, baked into **`out/intermediate/silk/devkitc1_gpio_silk_paths.json`**. **`generate_easyeda_adapter_pcb.py`** chooses silk via **`--silk-labels`** and loads that JSON; it does **not** load board TOML.
- **Independence rule** — treat **logical pin index** (1…N) as canonical; **silk** is a **display layer** that maps index → vendor string per profile. A future schema could move silk tables into data files or TOML; **`silk_profile`** in the board file is a **hook** for that, not the implementation yet.

### `out/` layout (generated; gitignored)

| Path | Contents |
|------|----------|
| **`out/preview/`** | SVG board previews (`adapter_gen` pipeline). |
| **`out/easyeda/`** | **Importable** EasyEDA Standard PCB JSON (and optional legacy expanded `.pcb.json`). |
| **`out/intermediate/silk/`** | Baked silk vector paths only — **cache** for the generator, not a board file. |

### Regeneration (typical)

```bash
# From repo root. Bake re-launches with `.venv/bin/python` when matplotlib is missing on `python3`.
./scripts/bake_devkitc_gpio_silk_paths.py
./scripts/generate_easyeda_adapter_pcb.py --board esp32-s3-devkitc-1 --silk-labels devkitc1
./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1
```

Default output paths use the board name (`out/easyeda/esp32-s3-devkitc-1.devkitc1.standard.json`, `out/preview/esp32-s3-devkitc-1.svg`). Pass **`-o` / `--output`** to override. Without **`--board`**, EasyEDA keeps the legacy basename `easyeda-adapter-44pin-dev2bread.*`.

Preview **silks** (`--silk devkitc1`, `numeric`, `auto`) and **branding** (`--no-branding` to omit): command table in **[README.md](../README.md)** (**SVG preview** section).

**Why (re)create a venv?** Usually you do not need to — keep **`.venv/`** in the repo (gitignored) and reuse it. Recreate if you switch Python major versions, the env breaks, you clone on a new machine, or you want a clean install of dependencies (e.g. after pinning versions).

**`out/`** is gitignored — regenerate locally after clone.

## Primary technical doc

Full constants, geometry, and CLI: **`docs/dev2bread-adapter-pcb.md`**.
