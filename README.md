# dev2bread-adapter-pcb

T-shaped **44-pin** adapter PCB: wide head for a development board (e.g. ESP32 class, ~1.1″ row spacing) and narrow stem for a solderless breadboard (~0.5″ straddle). **1:1** routing (logical pin 1→1 … 44→44).

This repository holds the **EasyEDA Standard** generator, documentation, and **static** assets under **`resources/`**. **Generated** silk paths and EasyEDA JSON are written to **`out/`** (gitignored — run the scripts locally).

## Quick start

```bash
python3 scripts/bake_devkitc_gpio_silk_paths.py   # once: needs venv + matplotlib
python3 scripts/generate_easyeda_adapter_pcb.py --all-variants
```

Import `out/easyeda-adapter-44pin-dev2bread.*.standard.json` in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**, then export Gerbers for your fab.

Full detail: **[docs/dev2bread-adapter-pcb.md](docs/dev2bread-adapter-pcb.md)**. For **AI / handoff context** (terminology, silk modes, pitfalls, repo split): **[docs/PROMPT_CONTEXT.md](docs/PROMPT_CONTEXT.md)**.

**`resources/images/`** holds reference photos (e.g. DevKit module, **breadboard misfitment**). Optional **silk artwork** for bitmap branding in EasyEDA can live there too.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_easyeda_adapter_pcb.py` | Emit EasyEDA Standard PCB JSON (copper, outline, silk). |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Regenerate silk path JSON (needs Python venv + **matplotlib**). |
