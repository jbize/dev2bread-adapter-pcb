# dev2bread-adapter-pcb

T-shaped **44-pin** adapter PCB: wide head for a development board (e.g. ESP32 class, ~1.1″ row spacing) and narrow stem for a solderless breadboard (~0.5″ straddle). **1:1** routing (logical pin 1→1 … 44→44).

This repository holds the **EasyEDA Standard** generator, baked silk vector data, and documentation. It is split from firmware projects so the hardware layout can evolve on its own.

## Quick start

```bash
python3 scripts/generate_easyeda_adapter_pcb.py --all-variants
```

Import `docs/easyeda-adapter-44pin-dev2bread.*.standard.json` in **EasyEDA Pro** via **File → Import → Import EasyEDA Standard Edition**, then export Gerbers for your fab.

Full detail: **[docs/dev2bread-adapter-pcb.md](docs/dev2bread-adapter-pcb.md)**.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_easyeda_adapter_pcb.py` | Emit EasyEDA Standard PCB JSON (copper, outline, silk). |
| `scripts/bake_devkitc_gpio_silk_paths.py` | Regenerate silk path JSON (needs Python venv + **matplotlib**). |
