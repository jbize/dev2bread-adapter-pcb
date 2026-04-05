# dev2bread-adapter-pcb

T-shaped **44-pin** adapter PCB: wide head for a development board (e.g. ESP32 class, ~1.1″ row spacing) and narrow stem for a solderless breadboard (~0.5″ straddle). **1:1** routing (logical pin 1→1 … 44→44).

This repository holds the **EasyEDA Standard** generator, documentation, and **static** assets under **`resources/`**. **Generated** outputs go under **`out/`** (gitignored — run the scripts locally): **`out/preview/`** (SVG previews), **`out/easyeda/`** (importable PCB JSON), **`out/intermediate/silk/`** (baked silk path cache — not a board file).

## Quick start

```bash
./scripts/bake_devkitc_gpio_silk_paths.py         # once: uses .venv automatically if matplotlib is missing on system Python
./scripts/generate_easyeda_adapter_pcb.py --board esp32-s3-devkitc-1 --silk-labels devkitc1
./scripts/preview_adapter_board.py --board esp32-s3-devkitc-1
```

Scripts are executable and use `#!/usr/bin/env python3`. Import `out/easyeda/<board>.*.standard.json` (e.g. `esp32-s3-devkitc-1.devkitc1.standard.json`) in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**, then export Gerbers for your fab. Omit **`--board`** to keep the legacy default filenames (`easyeda-adapter-44pin-dev2bread.*`).

Full detail: **[docs/dev2bread-adapter-pcb.md](docs/dev2bread-adapter-pcb.md)**. For **AI / handoff / picking up later** (terminology, silk modes, TOML vs silk vs copper, which `.py` files are new vs legacy, pitfalls): **[docs/PROMPT_CONTEXT.md](docs/PROMPT_CONTEXT.md)** — start with **“Picking up later (resume checklist)”** there.

**`resources/images/`** holds reference photos (e.g. DevKit module, **breadboard misfitment**). Optional **silk artwork** for bitmap branding in EasyEDA can live there too.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_easyeda_adapter_pcb.py` | Emit EasyEDA Standard PCB JSON (copper, outline, silk). |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Regenerate silk path JSON (needs Python venv + **matplotlib**). |
