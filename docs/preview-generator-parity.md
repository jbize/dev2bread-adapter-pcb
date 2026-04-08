# Preview ↔ generator parity (project goal)

This is a **product and architecture goal**, separate from general Python style (see `docs/python-clean-code.md`). It exists because **the SVG preview and the EasyEDA export must show the same geometry** wherever they describe the same thing—outline, holes, silk, and copper sketches. Divergence here is worse than ugly code: it ships **wrong expectations** about pads, silk, and routing.

---

## Goal

**Maximize shared code** between:

- **Preview:** `scripts/preview_adapter_board.py` → `adapter_gen/svg_preview.py` (and friends).
- **Generator:** `scripts/generate_easyeda_adapter_pcb.py` → EasyEDA Standard JSON (`TRACK`, pads, silk `TEXT`, etc.).

so that **what you see in the preview matches what you get in the exported board** for all shared concerns.

---

## What should stay in sync

| Concern | Shared source (examples) | Notes |
|--------|----------------------------|--------|
| Board outline, drill positions, `BoardParams` | `adapter_gen/geometry.py` | Single coordinate system (mil, +Y down). |
| Row reverser copper sketch | `adapter_gen/row_reverser_emit.py` vs preview glue in `svg_preview` | Same polylines / net intent. |
| Stem neck routing | `adapter_gen/stem_neck_routing_mil.py`, `stem_neck_emit.py` | Preview SVG and EasyEDA tracks should cite the same geometry. |
| Silk label positions (numeric / connector refs) | `adapter_gen/silk_preview.py` (`numeric_connector_header_centers_mil`, etc.) | Generator imports the same helpers where possible. |
| Baked silk vectors | `out/intermediate/silk/*.json` | Same JSON consumed by preview and generator. |

---

## What may legitimately differ

- **Presentation only:** stroke colors (Top = red, Bottom = blue in preview), waypoint dots, temporary labels, SVG groups—these have **no EasyEDA equivalent** or are cosmetic.
- **Layer / file format:** EasyEDA uses file units and `TEXT~` records; preview uses SVG `path`—**content** should match, **encoding** will not.

---

## Practices for contributors

1. **Add or change geometry in one place**—prefer `adapter_gen/` modules imported by **both** preview and generator before duplicating formulas in `scripts/`.
2. **When you must duplicate** (e.g. unavoidable EasyEDA string format), keep the **numeric core** in a shared function and only wrap for SVG vs EasyEDA at the edges.
3. **Docstrings** on shared helpers should state that they are used by **preview and/or EasyEDA** so future edits preserve parity.
4. **Regression check:** after changing layout or routing, regenerate a representative preview SVG **and** a sample EasyEDA JSON (or run the project’s smoke commands) and compare visually / spot-check coordinates.

---

## Related docs

- `docs/adapter-routing-invariants.md` — electrical and geometric intent (must not be violated for “parity” shortcuts).
- `docs/python-clean-code.md` — DRY and single source of truth align with this goal.
