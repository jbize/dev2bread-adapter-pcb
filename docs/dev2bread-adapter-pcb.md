# Dev-to-breadboard adapter PCB (goal and generated files)

This note records what the **44-pin adapter** is for, how the geometry matches the reference (`docs/example-44pin-beradboard adapter.jpg`), and where the EasyEDA output lives.

## Terminology (stem vs neck)

The narrow part that plugs into the breadboard is called the **stem** in this repo’s docs and code (`stem_layout_mil`, `STEM_OUTLINE_MARGIN`, …).

**Why “stem”:** The board is **T-shaped** — like a **mushroom** (cap + stem), a **wine glass** (bowl + stem), or a **T-junction** pipe: the **stem** is the vertical connector between the **wide head** (ESP32 side) and the **foot** that goes into the breadboard. It’s the usual word in mechanical/layout language for “the narrow middle bit.”

**“Neck” works too:** A **guitar** or **bottle** has a **neck** between a wider body and the opening — same geometry, different metaphor. Feel free to say **neck** in discussion; in documentation we standardize on **stem** so it matches the code and stays one word.

**`NECK_GAP` in the script** is the **gap** along the board between the bottom of the **wide** pad block and the **top** of the **stem** pads (the copper-only “throat” region), not a second name for the stem itself.

## Goal

- **Wide head:** A development board (e.g. ESP32-S3-DevKitC-1 class) plugs in here: two **22-pin** rows at **~1.1″** spacing, **rows parallel to the long edge of the head** (female headers on the PCB).
- **Narrow stem:** Plugs into a solderless breadboard: two **22-pin** rows at **~0.5″** (12.7 mm) **across** the breadboard trench. On the reference board, the stem hangs **down** from the **center** of the head in a **T** shape.
- **Electrically:** One **logical pin** = **one net** from that pin’s **wide** footprint to **exactly one** matching **stem** pad (pin 1 → 1, … 44 → 44). The stem still has **one** hole per net.

## Connectivity (does each hole go to exactly one stem pin?)

- **Stem:** Yes — **one** pad per net on the breadboard side (**44** pads total on the stem).
- **Wide head:** For **each** net there are **four** plated holes in a **breadboard-like** line (0.1″ pitch) stepping **toward the center gap**. The generator ties **all four** pads on the **same net** with short vertical copper, then routes from the **innermost** pad to the stem (so every hole is on the net, not just one — if your viewer shows only one pad connected, re-import or refresh DRC).

### Why four holes, not five?

On a real solderless breadboard, the **fifth** “row in” would be the **innermost** holes **right next to the center trench** — i.e. the row you’d use if the module were **narrow enough to sit across the gap** like a DIP. If your dev board **already** fit that way, you would **not** need this adapter. So the adapter only needs **four** selectable depths to cover common **wide** module spacings; a fifth “most inner” option is optional and was left out on purpose.

### Can more than one hole per column get a pin?

**Electrically:** Yes. All four holes in a column are the **same net**. Soldering a header pin in **two or more** holes in that column puts **parallel** connections on the same signal — usually harmless for ordinary digital I/O, just redundant.

**Mechanically:** You normally install **one** strip (or one row of pins) in the **single** row that **lines up** with your module’s header spacing. Filling **multiple** rows in the **same** column is uncommon because the **dev board** only has **one** row of pins per side there — but nothing in the **schematic** forbids extra pins in other holes on the same net if they fit and you want them for strength or experimentation.

## Breadboard column letters (a–j)

On a typical full breadboard, the **left** half of each row is **a–e** (**e** next to the center trench) and the **right** half is **f–j** (**f** next to the trench).

- **Narrow stem:** The two plug-in rows match **e** and **f** — they straddle the gap the same way a DIP or straddle header would.
- **Wide head:** The **four** holes per column step **inward** along **0.1″** toward the gap between the two long rows — the same pattern as **a→b→c→d** on the left half and **j→i→h→g** on the right half (four columns **outboard** of **e** / **f**). Only the stem is **inserted** into the breadboard; the head stays above the board — the letters describe **grid compatibility**, not that the whole head occupies those holes at once.

## Geometry (reference layout)

- **Head:** 22 columns along **+X** (**0.1″**). Column **0** is the **left** edge of the head (smaller **X**); **21** is the **right**. The two long sides are separated along **+Y** by **~1.1″** (`WIDE_ROW_GAP`). **J3** nets **23–44** on the **top** row (GND, TX, RX … at **top-left**), **J1** nets **1–22** on the **bottom** row (3V3, RST …). The **stem** was not mirrored: only head column **X** order was set to match the DevKitC-1 J1/J3 rows.
- **Wide “breadboard depth”:** `WIDE_HEAD_DEPTH_HOLES` (**4**) holes per column per side, same pitch as the breadboard grid in that direction.
- **Stem (90° vs head):** The **22-pin** direction runs along **+Y**; straddle spacing along **+X** (**~0.5″**, `NARROW_ROW_GAP`). Stem is centered under the head.
- **Routing:** Vertical links between the four wide pads on a net, then a Manhattan path from the **innermost** wide pad to the stem (with `ROUTE_JOG_MIL` so routes in the gap do not clip against the opposite side’s pads at the same column).
- **Outline:** **T-shaped** polygon (`STEM_OUTLINE_MARGIN`, `HEAD_OUTLINE_EXTRA`).

## Constants (see `scripts/generate_easyeda_adapter_pcb.py`)

| Meaning | Default (mil) | Notes |
|--------|----------------|--------|
| Pin pitch | `100` | 0.1″ |
| Wide row spacing | `1100` | ~1.1″ between outer rows of the head |
| Wide depth holes | `4` | `WIDE_HEAD_DEPTH_HOLES` — breadboard-style rows toward the gap |
| Narrow straddle | `500` | 0.5″; use `300` for 0.3″ if you prefer |
| Neck gap | `500` | Below `Y_W_ROW_B` before the stem block |
| Stem outline margin | `130` | Board edge past the narrow columns |
| Route jog | `40` | `ROUTE_JOG_MIL` on the path to the stem |

## Generated outputs

The adapter is **44 pins** total: **2 × 22** on the head and the same **2 × 22** on the stem (**1:1** routing).

### Which script does what

| Script | Role |
|--------|------|
| **`scripts/generate_easyeda_adapter_pcb.py`** | Builds the **EasyEDA Standard** PCB JSON (copper, outline, silk). Run this whenever you change geometry or silk mode. |
| **`scripts/bake_devkitc_gpio_silk_paths.py`** | **Required before `devkitc1` / `numeric` silk:** writes **`out/silk/*.json`** (needs a **venv** + **matplotlib**). Re-run when fonts or label tables change. |

### EasyEDA files (default names)

Import in **EasyEDA Pro**: **File → Import → Import EasyEDA Standard Edition**.

| Output file | Contents |
|-------------|----------|
| **`out/easyeda-adapter-44pin-dev2bread.devkitc1.standard.json`** | **Kit-specific silk:** ESP32-S3-DevKitC-1 v1.1 J1/J3 names (same mapping as [Espressif’s tables](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)). Use when the dev board is that kit. |
| **`out/easyeda-adapter-44pin-dev2bread.numeric.standard.json`** | **Generic silk:** labels **1–44** only (matches logical net index / copper pad numbers — not tied to a vendor pinout). |
| **`out/easyeda-adapter-44pin-dev2bread.standard.json`** | **No per-pin silk text** (pin-1 circles still on unless `--no-silk-pin1`). |

Regenerate examples:

```bash
python3 scripts/generate_easyeda_adapter_pcb.py --silk-labels devkitc1   # → *.devkitc1.standard.json
python3 scripts/generate_easyeda_adapter_pcb.py --silk-labels numeric   # → *.numeric.standard.json
python3 scripts/generate_easyeda_adapter_pcb.py --silk-labels none       # → *.standard.json
python3 scripts/generate_easyeda_adapter_pcb.py --all-variants           # writes devkitc1 + numeric
```

Use **`-o PATH`** to override the output file. **`--all-variants`** writes both kit-specific and numeric defaults (ignores `-o`).

- **Silk (pin 1):** Two small **open circles** on Top Silk marking **pin 1** (wide head row A, stem). Omit with **`--no-silk-pin1`**.
- **Per-pin silk text:** **88** Top Silk `TEXT` objects for `numeric` (two rows × 22 on the head + two columns × 22 on the stem). **`devkitc1` adds two more** **above the stem** (below the J3 GPIO row, not over those labels): **ESP32-S3-DevKitC-1** and **v1.1 · J1/J3** — **90** `TEXT` total. For **DevKitC-1**, orient the board so **J1 faces side A** and **J3 faces side B**; silk follows the Espressif **J1/J3** pin order (v1.1 RGB LED note: **GPIO38**).
- Vector paths: `out/silk/devkitc1_gpio_silk_paths.json` and `out/silk/numeric_silk_paths.json` (from **`scripts/bake_devkitc_gpio_silk_paths.py`**; not committed).
- **Stronger board / more FR4:** `--margin-mil`, `--stem-outline-margin-mil`, `--head-outline-extra-mil`.
- Optional legacy expanded JSON: `--legacy-expanded`

### Why numbering was “hard” (and what we did)

EasyEDA Standard `TEXT` stores **stroke outlines** (like plotter paths), not a font string. The bake script turns each short label into paths once; the main generator translates them to each pad. No **matplotlib** is required **at board-gen time** — only to **re-bake** paths if you change font or text.

### Branding / artwork (e.g. a painting)

**Cost:** Still usually **one silk color** included at cheap fabs; a **bitmap** on silk is often the same price as text (check **minimum line width** / **minimum feature** — often ~0.15 mm). **Extra** charges tend to be for **multiple silk colors**, **nonstandard stackups**, or **failed DRC** if artwork is too fine.

**Artwork vs photo:** Silk is **one ink color** on the board — **no gradients**. A detailed painting must be **flattened** to high-contrast **1-bit** (or coarse halftone) art. Fine hair, soft clouds, and subtle shading **will not** reproduce like a print; expect a **bold, posterized** look unless you simplify. Easiest flow: convert to **monochrome PNG/SVG**, import in **EasyEDA** on **Top Silk**, scale and run **DRC**. **No technical downside** beyond clutter and fab rules — not a reason to avoid it if you like it.

### What the script does *not* include

Octagonal head corners, **imported bitmap/logo** (add in EasyEDA), exact fab notes, or 3D.
