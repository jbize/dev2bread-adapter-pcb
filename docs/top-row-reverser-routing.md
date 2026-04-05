# Top-row pin reverser (two-layer routing algorithm)

**Scope:** N-pin / N-hole dev-to-breadboard adapter (any **N** the generator supports), **two copper layers** (e.g. Top + Bottom), using **plated through-holes** as layer-to-layer transitions (“pass-throughs” / vias). The routing rules are the same for every column count **n = N/2**.

**Goal:** Electrically **reverse the order** of signals along **one** long row of the wide head so that, after this block, net order matches the breadboard / stem convention.

This document states the **routing pattern** and the **repeatable rules** used by `scripts/row_reverser_svg.py` (preview). Fab DRC is still your toolchain’s job.

### Canonical preview rules (`row_reverser_svg.py`)

These are the **same** rules you can mirror in copper (mil, +Y down):

| Rule | Definition |
|------|------------|
| **Units** | **mil**; column pitch **`PITCH`** (0.1″ = 100 mil); PTH hole radius **`HOLE_R`** from `adapter_gen.geometry`. |
| **Pad column X** | **`x(i) = (n − 1 − i) × PITCH`**; **edge via column** **`x_e = (n − 1) × PITCH + edge_offset`** (default **`edge_offset = 2×HOLE_R + 20`** mil). |
| **Layer B inner end for column `i`** | Let **`j = n − 1 − i`**. If **`j ≥ 1`**, inner via at gap **`g(j−1)`** = midpoint between **`x(j−1)`** and **`x(j)`**. If **`i = n − 1`** (**Jn**): **no** inner-layer horizontal (pad already on the correct side); **only** Layer A to **edge** via. |
| **Layer B traces** | **`i ≤ n − 3`**: **horizontal** from **`V_i`** at **`y_v(i)`** **only** **until** **intersection** with **Layer A** **`P_{n−2} → V_{n−2}`** (**J6** cyan when **n = 7**), then **straight** to **`(gap x, y_v(i+1))`**; inner via **Y** = **`y_v(i+1)`**. If intersection is out of range, **one diagonal** to the gap. **`i = n − 2`**: **one straight diagonal** to **`y_v(n−1)`**. **Edge** vias unchanged. |
| **First lane Y** | **`y_first = y_pad + HOLE_R + trace_width/2 + neck_clearance`** so trace centers sit **below** PTH circles (no line through holes). Defaults: **`y_pad = 0`**, **`trace_width = 6`** mil, **`neck_clearance = 4`** mil (override **`--neck-clearance`**). |
| **Lane pitch** | **`dy = 2×via_r + trace_gap`** (defaults from script), or **`dy = max_y_span/(n−1)`** if **`--max-y-span`** is set. |
| **Labels** | **J1** = **`i = 0`** (right), **Jn** = **`i = n − 1`** (left). |

---

## Column index (same as `adapter_gen`, same as J1)

Use **one** index **`i = 0 … n − 1`** aligned with **`head_column_x_mil(i, p)`** and the **existing** pad numbering on the wide head:

| Symbol | Meaning |
|--------|---------|
| **N** | Total plated holes on the adapter head for this routing block (even). |
| **n** | Holes in **one** long row: **n = N/2** (adapter column count; scales with **N**). |
| **i** | **Column index** in **`adapter_gen`**: **`i = 0`** is the **right** column (**largest X**); **`i = n − 1`** is the **left** column (**smallest X**). |
| **J1 … Jn** (preview labels) | **Human-readable** column labels: **J1** is the **right** pad (**`i = 0`**), **Jn** is the **left** pad (**`i = n − 1`**), matching **`adapter_gen`** and **J1 net 1** on column **0**. The preview script `scripts/row_reverser_svg.py` draws these on pads (not the Espressif **J1/J3** connector names). |
| **J1 net on column i** | **`i + 1`** (wide row A). |
| **J3 net on column i** | **`i + n + 1`** (wide row B). |

The row that needs **reversal** (often **J3** / nets **n+1 … 2n** in a full head) is still **one pad per column `i`** — you route from **that** row’s pad at **`(head_column_x_mil(i), y_row)`**, not a second indexing scheme.

**No extra mapping:** **`i`** is **not** rotated or translated relative to the layout code; **`i = 0`** is the **same** column as row-A net **`i+1`** (e.g. **1**) and row-B net **`i+n+1`** (e.g. **`n+1`**) for that column — for **any** adapter **N** (preview uses the **innermost row-A** pad line for **`y_pad`**).

### Pin / hole ↔ via ↔ trace (preview)

Each **column `i`** has **one PTH** in the row being reversed (hole center **`(x(i), y_pad)`**). **Layer A:** pad **`P_i` → edge via `V_i`** at **`(x_e, y_v(i))`** (cyan). **Layer B:** **`V_i` → gap via** at **`(x, y)`** where **`x`** is the midpoint between **`x(j−1)`** and **`x(j)`** with **`j = n − 1 − i`** (red), except **`i = n − 1`** (**Jn**): **no** inner horizontal — only **`P_{n−1} → V_{n−1}`**.

**Horizontal stop (all lanes with `i ≤ n − 3`):** **Layer A** **`P_{n−2} → V_{n−2}`** (**J6** cyan when **n = 7**). Every red **horizontal** runs from **`V_i`** to **that** line only, then slants to the gap. For **`i = n − 2`** (**J6** red), the **J6** cyan meets **`V_{n−2}`** at **`x_e`**, so the preview uses **one diagonal** (no horizontal leg).

**Inner via Y:** **`y_v(i+1)`** for **`i ≤ n − 3`**; **`y_v(n−1)`** for **`i = n − 2`**.

**Example `n = 7`:** **J1…J5** horizontals all stop at **J6** cyan, then route to the gap; **J6** one diagonal to **`y_v(6)`**.

---

## Infrastructure: two via populations

1. **Edge stack**  
   **n** pass-through vias **V₀ … Vₙ₋₁** placed **below** the row being reversed, **near the `i = 0` (right) end** where the diagonal legs converge. They form a **vertical chain** so each column’s diagonal lands on a **distinct** edge via.

2. **Inter-column gap vias**  
   **n − 1** pass-through vias **G₀ … Gₙ₋₂**, each on the **centerline** of the **gap** between **column `i`** and **column `i + 1`** (adjacent columns along **X** in layout space).

---

## Layer A (e.g. top copper)

For each **column `i`**, route from **that row’s** pad at column **`i`** to **edge via `Vᵢ`** with a **short diagonal** on **layer A** only.

**Build order** (implementation detail): often **i = 0, 1, …** along the edge stack, or **from the outside column inward** — keep **one net per via** and **no unintended shorts** between diagonals.

---

## Layer B (e.g. bottom copper)

From each **Vᵢ**, route **toward** the chosen **gap** via (see canonical table). **`i ≤ n − 3`**: **horizontal** **to** **`P_{n−2} → V_{n−2}`** (**J6** cyan), **then** **to** **gap**. **`i = n − 2`**: **one diagonal** only. Optional extra **bends** in a **physical** **layout** are a **separate** **density** **trade** (see **`resources/images/reverse-traces.png`**).

**Traces vs vias:** **Copper** segments are **traces**; **pass-throughs** are **plated holes** (**vias**). In the preview SVG, **red** = inner-layer **traces**; **green** = **vias**. **Red** **horizontals** end **one pin/hole gap toward the edge** (at **g(j−1)** for target column **j**). **Jn** (leftmost) has no red segment — only cyan to the edge via on that net.

**Preview scaling:** `scripts/row_reverser_svg.py` uses **mil** and `PITCH` / `HOLE_R` from `adapter_gen.geometry` (breadboard **0.1″**). The first inner-layer lane is placed **below** the pad holes (**pad center + hole radius + half trace width + neck clearance**) so **red** traces and **vias** do not run through PTH circles. Lane spacing: **dy ≈ 2×routing via radius + trace gap**; **`--max-y-span`** caps total stack height; **`--neck-clearance`** adjusts the gap under holes.

**Reversal mapping:** Choose **which** **Gₖ** each **Vᵢ** hits so the **combined** **column → V → G** wiring implements the **intended permutation** (typically **full reversal** along that row).

There are **n − 1** gap sites **G₀ … Gₙ₋₂** (**Gₖ** = between **column `k`** and **`k + 1`**). A common pattern (see `docs/reverse-traces.svg`, 7-lane example) processes from the **`i = 0`** column first; exact **i → k** targets follow from the **reverse** you want and must keep **all nets disjoint** and **DRC-clean**.

---

## Summary (one paragraph)

**Layer A:** **column `i` pad → Vᵢ** (diagonal to the **right-hand** edge via stack). **Layer B:** **Vᵢ → Gₖ** (preview: **`i ≤ n − 3`** horizontal **to** **J6** cyan **then** **slant**; **`i = n − 2`** one diagonal), with **k** chosen so **n** nets **reverse** order along the row. **Two layers** are required because diagonals and horizontals use different layers; **plated holes** swap layers at **V** and **G**. **Indexing `i`** matches **`head_column_x_mil`** and **J1** net **`i+1`** — no separate **P** axis.

---

## Related files

- `docs/reverse-traces.svg` — two-layer **7-lane** bus reversal reference (cyan outer diagonals, red inner horizontals, green vias).
- `scripts/row_reverser_svg.py` — preview SVG in **mil** (`--columns N`): 0.1″ pitch, PTH/via scale from `adapter_gen.geometry`; **`i ≤ n−3`** red **horizontal** **to** **`P_{n−2}→V_{n−2}`** (**J6** cyan), inner **`y = y_v(i+1)`**; **`i = n−2`** one diagonal; vertical stack `dy = 2×via_r + trace_gap` or `--max-y-span`; cyan diagonals. Default `out/preview/row-reverser-<N>.svg`.
- `docs/dev2bread-adapter-pcb.md` — adapter terminology and geometry constants.
- `adapter_gen/geometry.py` — **`head_column_x_mil`**, **`wide_head_y_rows_mil`**.
- `adapter_gen/svg_preview.py` — full-board SVG: same geometry via **`compute_row_reverser_geometry_mil`**, **`y_pad`** = innermost row-A row (bottom of the top socket stack).
