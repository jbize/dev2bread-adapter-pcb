# Design prompt: generic solderless-breadboard extension adapter

Use this document as the **product + geometry brief** for a **new** generator pipeline (parallel to the legacy 44-pin EasyEDA script). It captures intent, constraints, and **staged routing** so implementation can proceed in layers.

## Concept

- **What it is:** A **T-shaped** PCB that acts as a **solderless breadboard extension**: one side plugs into a **standard breadboard** (fixed **straddle** geometry); the other side accepts a **development module** whose two header rows are **wider** than a breadboard trench.
- **Electrical model:** **1:1** mapping — logical pin **i** on the head connects only to pin **i** on the stem (no permutation, no crossbar). Indices run **1 … N** with **N** even.
- **Scope (v1):** Support **any even pin count from 14 to 44** (inclusive). Interpret **N** as **two rows of N/2 pins** on both head and stem (e.g. N=44 → 2×22; N=14 → 2×7).

## Fixed vs parameterized geometry

| Quantity | Rule |
|----------|------|
| **Stem straddle (width across the trench)** | **Target** ~0.5″ breadboard spacing — must be **≥** **minimum** derived from trace rules and stem routing (**Pre-determining pin-row gaps**); if not, widen with **extra column(s)** or non-standard straddle. |
| **Stem length (along the plug-in direction)** | **Determined by N** — scales with the number of **columns** (N/2) along the stem; padding/margins are explicit constants. |
| **Head row spacing** | **Target** ~1.1″ wide spacing — must be **≥** **minimum** gap for **reversal** given `w` and spacing (**Pre-determining pin-row gaps**); dev boards that match this are drop-in. |
| **Head depth (header socket rows per side)** | **Up to 4** parallel rows on the **top** side and **up to 4** on the **bottom** (0.1″ pitch) for **header sockets** — **`n_rows_top`**, **`n_rows_bottom`** ∈ **1…4** (see subsection). **Removing** rows **widens** the **reversal gap** when routing is tight. |
| **Outline** | **Fully determined** by N, **`(n_rows_top, n_rows_bottom)`**, and mechanical constants (margins, corner radius, neck gap, etc.). |

### Adjustable head depth (header sockets: up to 4 rows per side)

The **wide head** provides **header socket** holes on each side of the center gap — like a breadboard, **up to four** 0.1″ **depth** rows on the **top** side and **up to four** on the **bottom**, for a given column (same net across the depth you populate).

- **Parameters:** **`n_rows_top`** and **`n_rows_bottom`** — each in **1…4** — how many **socket** rows exist on the **top** side of the head and on the **bottom** (per column), alongside **N**.
- **Landing vs reversal gap:** **More** socket rows give **more** positions to fit different module widths (solder a header in the row that matches your dev board). **Fewer** socket rows **free** space: the generator must be able to **drop** rows (from the maximum) to **widen** the **reversal gap** — the **working region between** the two main head rows where **reversal** copper runs. That gap is often the **limiting** dimension; **removing** depth rows is a primary way to **enlarge** it without changing **N** or the **1:1** net list.
- **Maximum:** **Four** rows top and **four** bottom is the **design ceiling** (matches common “four hole depths” patterns); actual builds may use **fewer** when **predetermined gaps** or routing validation require more room for reversal.

**Goal:** Given **N**, shared constants, and **`(n_rows_top, n_rows_bottom)`** (each ≤ 4), **board geometry is fixed** — no ad hoc per-net editing for outline and pad positions.

### Mitigations when routing fails

When **reversal** routing, **neck/throat** paths, or **stem** paths fail validation (shorts, DRC, crossings, or unrouteable geometry), there are **two primary levers** — try **(1)** first where it respects fab rules, then **(2)** if the board must grow or simplify.

**1) Narrow the copper rules (within fab limits)**  
Reduce **trace width**, **via pad** size if modeled, and/or **minimum spacing** (trace–trace, trace–pad) — always subject to the **house DRC** and **minimum feature** rules. This costs **current capacity** and **noise margin** slightly but avoids a larger PCB.

**2) Add width or free a wider working channel**  
Grow or reshape the **usable routing area**:

| Region | Mitigation (conceptual) |
|--------|-------------------------|
| **Stem** | **Widen the board** by **one (or more) 0.1″ column(s)** to the **left or right** of the breadboard **trench** — i.e. add horizontal extent beside the straddle so vertical runs down the stem have **another column** of clearance. Still **N** pins; outline and stem pad grid shift with the extra margin. |
| **Head** | **Reduce** **`n_rows_top`** and/or **`n_rows_bottom`** below the **maximum (4)** — fewer **header socket** rows — to **widen the reversal gap** (room for reversal copper between the two main head rows). Trades **landing** options for **clearance**. |

**`n_rows_top` / `n_rows_bottom`:** At most **4** each; **removing** rows **widens** the **reversal** working region; **adding** rows (up to 4) **adds** socket positions but **shrinks** that gap — tune from **maximum** down when validation fails. The generator should treat **trace rules** and **row counts** as **explicit parameters** so a failed run can suggest **which** mitigation to try next.

### Pre-determining pin-row gaps from design rules

**Inputs:** Acceptable **minimum trace width** `w`, **minimum spacing** (trace–trace, trace–pad, pad–pad as applicable) — from **fab DRC** and electrical comfort — plus the **fixed routing recipes** (reversal topology in the **head**, stem **lane** usage between straddle rows).

**Principle:** Before placing pads or emitting copper, **derive minimum required gaps** so routing is **feasible by construction**, not by luck:

| Region | What to pre-compute |
|--------|---------------------|
| **Head — reversal** | From `w`, spacing, and the **reversal pattern** (how many parallel arcs/lanes fit between the two wide head rows, inner vs outer paths), compute a **minimum** **working gap** between the two **main** head rows (and any **neck** gap that the reversal consumes). The **physical** wide-row spacing (e.g. ~1.1″) must be **≥** this minimum — or the recipe must **widen** the head, **reduce** **`n_rows_top` / `n_rows_bottom`** (≤ 4) to **widen** the reversal region, or **narrow** `w` per **Mitigations**. |
| **Stem** | From `w`, spacing, **pad drill/annulus** if modeled, and the **number of independent traces** that must pass **between** the two stem rows (or in **side** channels), compute **minimum** **straddle** clearance and any **extra column width** needed beside the trench. Compare to **standard** ~0.5″ breadboard straddle: if the **minimum** exceeds it, **pre-decide** **stem extra column(s)** (or a non-standard wider stem) **before** layout — i.e. the generator should **fail fast at configuration** or **auto-widen** the stem outline, not only at DRC after the fact. |

**Outcome:** **Pin-row gaps** (head wide spacing contribution, neck, stem straddle, optional stem margin columns) are **predetermined** from **`(w, spacing)`** and **topology**, then **locked** for pad placement. Iteration becomes **change rules or topology**, regenerate geometry — consistent with **preview sign-off → JSON**.

**Reproducibility:** The IR should also record **`w`**, spacing inputs, and the **computed minimum gaps** (head, stem, any stem extra width) **used for that build**, so outputs can be **regenerated and diffed** without guessing which rules produced a given layout.

## Viewing and iteration

- **Preview at scale:** Produce a **scale-accurate** representation (e.g. **SVG** or equivalent) that can be **opened and reviewed independently** of EasyEDA — same coordinates/units as the copper model, so edits to geometry or routing are visible before export.
- **Separation:** Treat **layout / routing** and **EasyEDA JSON emission** as **different stages** so preview and fab export share the same underlying geometry.
- **Where files live:** **Generated** SVG previews (interim + combined) and **EasyEDA JSON** belong under **`out/`** — e.g. `out/preview/*.svg` or similar — alongside other **build outputs**, **not** under **`docs/`**. **`docs/`** keeps **human-authored** reference material (concept sketches, pinout notes, static diagrams like `docs/reverse-traces.svg`). Generated artifacts are **gitignored** with the rest of `out/` so the repo stays source-only.

### Interim outputs (layered previews)

The full board is **hard to read** in one picture. The pipeline should support **separate** preview artifacts — same coordinate system, **subset** of geometry — so each stage can be checked in isolation.

| Interim artifact | Contents (conceptual) |
|------------------|------------------------|
| **Holes / mechanical** | Board **outline**, **PTH positions** (head + stem), **drill** circles — no copper, or copper dimmed. |
| **Bottom head row + stem (bottom-layer) copper** | Traces on the **primary layer** for the **bottom** logical head row (and **stem** segments that live on that layer, if any). |
| **Top head row + reversal (other-layer) copper** | Traces for the **top** logical row, including **reversal** segments, **vias**, and stem segments on the **alternate** layer as defined. |
| **Combined SVG (single file)** | **All** of the above in **one** document as named groups — e.g. `outline`, `holes`, `copper_bottom`, `copper_top`, `vias`, `silk` — so you can **toggle visibility** in Inkscape/browser and still **export one file** for review. Same coordinates as the split files. |

*(Stem copper may appear in **one or both** layer-specific previews depending on how layers are split; the **combined** file is the usual “does the whole board look right?” check.)*

**Format:** **SVG is the default** for these: **vector**, **zoomable**, easy to **diff**, and supports **separate files** or **layers/groups** (`<g id="holes">`, `<g id="copper-bottom">`, `<g id="copper-top">`) in one file. Write them under **`out/`** (see **Where files live** above). Alternatives (PNG/PDF exports, HTML canvas) are optional; **IR JSON** remains the source of truth — SVG is **derived** for humans.

Optional extras (if useful): **vias-only** group, **neck / throat** viewBox zoom, **silk** overlay as its own group.

### Preview sign-off → EasyEDA JSON

Workflow is **one** geometric truth, **two** render targets:

1. Build and validate **IR** (pads, tracks, vias, outline, silk placements).
2. Emit **interim + combined SVG** from that IR — iterate until **previews look correct** (geometry, layers, labels).
3. **Only then** emit **EasyEDA Standard JSON** from the **same IR** — **no parallel hand-built JSON**, no second geometry path. If something is wrong in EasyEDA import, **fix the IR or the emitter**, regenerate **both** SVG and JSON.

So: **approved previews ⇒ JSON matches** — the export step is **deterministic** from the signed-off model, not a separate artistic step.

## Silk / labeling modes

Per-pin silk (and any baked vector text) is selected by a **label mode** independent of **N** and geometry:

| Mode | Labels |
|------|--------|
| **Generic** | **`1` … `N`** — one string per logical net index (same as copper net numbering). Vendor-agnostic. |
| **Board** | **Board-type–specific** — e.g. a named profile (`esp32-s3-devkitc-1-v1.1`, …) supplies the **signal name** (or short silk string) **per pin** from a **lookup table** keyed by **logical index** 1…N (and documents required **orientation**: which physical row is “top” vs “bottom”). |

Implementation can mirror the existing repo pattern: **generic** needs no external table beyond **N**; **board** loads a **pinout table** for that board type. **EasyEDA** still receives **stroke paths** for text (bake step), not raw fonts, if the editor requires it.

## Copper: layered routing strategy (stages)

Routing is **not** a single monolithic step. Build copper as **ordered stages**; each stage has a clear responsibility and can be validated before the next.

### Layers (conceptual)

- **Bottom head row** (concrete name TBD: e.g. “J1 / row B / nets 1…N/2” in existing docs): **entirely on one copper layer** — no layer change for signals that only need Manhattan routing on that side of the head, as defined by the algorithm.
- **Top head row** (e.g. “J3 / row A / nets N/2+1…N”): must implement a **reversal** between the two head rows (bus order vs stem order). That **requires two layers** — inner horizontal segments on one layer, **outer** segments / **diagonals / vias** as needed on the other, consistent with the **reversal** pattern (see existing SVG concepts: `docs/reverse-traces.svg`, `docs/adapter-14pin-concept-r4.svg`).
- **Between the two head rows:** the **reversal** topology uses **both** layers; **outside** that region, the top row **otherwise** uses **the other layer** relative to the bottom row’s primary layer, so Top/Bottom roles stay predictable.

### Suggested stage breakdown (algorithm hooks)

1. **Pads** — Place all **PTH pads** (head + stem) in board coordinates; assign **net IDs** 1…N.
2. **Stem** — Short links on stem as needed; stem may be mostly single-layer or follow a fixed pattern.
3. **Head — bottom row** — Complete **single-layer** routes for the bottom row to the **neck / stem entry** (policy: Manhattan, no vias unless later revised).
4. **Head — top row — reversal** — Add **second-layer** segments and **vias** to implement **reversal** from top head order to the **same column / net ordering** expected at the stem interface. If clearance is insufficient, apply **Mitigations when routing fails** (narrow rules; adjust head depth rows; widen stem — see that section) and re-run rather than hand-editing traces.
5. **Neck / throat** — Connect head exit points to stem entry; **no accidental shorts**; respect keepouts.
6. **Validation** — Same-layer segment intersection checks, outline containment, optional DRC-style rules before export.

Exact **track widths**, **via placement**, and **layer assignment** (Top vs Bottom) are **implementation details** but must follow the **staged** structure above so 14-pin and 44-pin share the same pipeline with different **N**.

## Outputs (future implementation)

| Output | Purpose | Location (convention) |
|--------|---------|------------------------|
| **Geometry / IR** (JSON or similar) | Stable intermediate: pads, segments, vias, outline — **units explicit** (e.g. mil); plus **design-rule snapshot** (`w`, spacing, **predetermined gaps**). **Single source of truth** for SVG and EasyEDA. | e.g. `out/ir/*.json` |
| **Interim SVGs** | **Holes-only**, **bottom-row copper**, **top-row copper** — same scale as IR (see **Interim outputs**). | e.g. `out/preview/` |
| **Combined SVG** | One file, **grouped layers** — default **human** sign-off before fab export. | e.g. `out/preview/board-combined.svg` |
| **EasyEDA Standard JSON** | Emitted **from the same IR** **after** previews are accepted — **matches** geometry in SVG; **last** render target, not a fork. | e.g. `out/easyeda/` (importable board file) |

Exact filenames are implementation-defined; **all** are under **`out/`**, not **`docs/`**.

## Relationship to the current repo

- The existing **`scripts/generate_easyeda_adapter_pcb.py`** remains a **reference** for **44-pin**, **single-layer Manhattan** head routing where applicable; the **new** pipeline generalizes **N** and adds the **two-layer reversal** rules for the **top** head row.
- **Silk:** **Generic** (`1…N`) vs **board**-typed labels map to the **`numeric`** vs **`devkitc1`** style in the legacy bake scripts; silk is **orthogonal** to the copper stages.
- **`out/` vs `docs/`:** Matches current repo policy — **generated** artifacts live under **`out/`** (gitignored): **`out/preview/`** (SVG), **`out/easyeda/`** (importable PCB JSON), **`out/intermediate/silk/`** (baked silk path cache). **`docs/`** is for **source** documentation and **static** reference diagrams, not generator output.

## Open decisions (to refine before coding)

- **Default vs bounds `n_rows_top` / `n_rows_bottom`:** **Max 4** per side (header sockets); default e.g. **4** for maximum landing flexibility — **decrease** toward **1** as needed to **widen the reversal gap** when routing fails — see **Adjustable head depth** and **Mitigations**.
- **Stem extra column(s):** Default **zero**; increment when stem paths fail and fab allows a **wider** outline.
- **N odd / partial rows:** v1 assumes **N even** and **two equal rows**. Document exceptions if any.
- **Minimum feature / fab:** Reversal may need **finer** geometry at small N — confirm **trace/via** rules per fab.
- **Closed-form vs conservative bounds:** Whether **minimum gaps** are **tight** formulas per reversal/stem recipe or **safe upper bounds** from worst-case lane count — document the chosen approach so **pre-determination** stays auditable.
- **Naming:** Align **row A/B**, **J1/J3**, and **net index** conventions with `docs/PROMPT_CONTEXT.md` and update both if terminology shifts.
- **Board label profiles:** How new **board types** are registered (file per board, single registry JSON, etc.).

---

*Last intent: capture a **design prompt** for a generic breadboard extension adapter with **N ∈ [14, 44]**, **stem length from N**, **pin-row gaps pre-determined from min trace width/spacing** (head reversal + stem), **up to 4 header socket rows** per side (**removable** to **widen** the reversal gap), **staged copper**, **interim + combined SVG previews**, **preview-then-export** (EasyEDA JSON **matches** IR after sign-off), **generic vs board silk labeling**, and **independent scale preview**.*
