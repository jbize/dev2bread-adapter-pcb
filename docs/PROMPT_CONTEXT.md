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
| `devkitc1` | **ESP32-S3-DevKitC-1 v1.1** J1/J3 signal names (Espressif tables). **Kit-specific** (not other DevKit shapes or revisions); user must orient **J1 → side A**, **J3 → side B**. Two-line **board ID** silk **between the J3 row and the stem** (visible when the stem is in a breadboard). | `out/silk/devkitc1_gpio_silk_paths.json` (generated; run bake script) |
| `numeric` | Generic **1–44** (matches logical net / pad numbers). **Not vendor-specific.** | `out/silk/numeric_silk_paths.json` (generated; run bake script) |
| `none` | No per-pin text silk (pin-1 **circles** still unless `--no-silk-pin1`). | — |

Default output filenames avoid overwriting variants: `out/easyeda-adapter-44pin-dev2bread.<variant>.standard.json` (see `docs/dev2bread-adapter-pcb.md`). **`--all-variants`** writes devkitc1 + numeric defaults.

**Why GPIO silk:** On a breadboard, **logical 1…44** doesn’t match how people think (ESP32 **GPIO** names). DevKitC silk aligns with the **module’s** header naming when the board is oriented correctly.

## Scripts

| Script | When to run |
|--------|----------------|
| `scripts/generate_easyeda_adapter_pcb.py` | **Always** for PCB JSON changes. The script does not import matplotlib; for **`devkitc1` / `numeric` silk**, run **`bake` first** so **`out/silk/*.json`** exist. |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Before first **`devkitc1` / `numeric`** generation, and when **regenerating** silk paths (fonts, labels). Needs **venv + matplotlib**. Writes **`out/silk/`** (both DevKitC and numeric files). |

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

## Primary technical doc

Full constants, geometry, and CLI: **`docs/dev2bread-adapter-pcb.md`**.
