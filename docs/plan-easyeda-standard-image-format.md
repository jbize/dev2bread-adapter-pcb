# Plan: EasyEDA Standard–style branding images in generated JSON

## Goal

Emit branding artwork in the same **representation EasyEDA Standard often uses after import/save**—notably **`SVGNODE~`** with vector **`path`** data on **Top Silk (layer 3)**—so that:

1. **Re-exported** JSON from EasyEDA is closer to **generator** output (fewer surprises).
2. **Import** behavior (logo visibility, Pro vs Standard) is easier to reason about than **`IMAGE~` + base64 PNG** alone.
3. **Preview** can stay **honest** (lossy, chunky paths if that is what the editor produces).

This is **not** about inventing a new industry format; **EasyEDA’s JSON is ground truth** for what we ingest.

## Current state (baseline)

| Piece | Behavior |
|-------|----------|
| **Source asset** | JPEG/PNG from `[branding].image`; Pillow loads, **RGBA**, optional **max width 512 px** resize, then **PNG bytes** embedded in **`IMAGE~x~y~w~h~3~base64~id`**. |
| **EasyEDA re-export** (observed) | Often **no `IMAGE~`**; logo stored as **`SVGNODE~{"gId", "nodeName":"path", "layerid":"3", "attrs":{"d":"M…", "stroke", …}}`**. |
| **Preview SVG** | Raster `image` + path text; **`preview_silk_color`** for branding text stroke only. |
| **Extractor** | `scripts/branding_box_from_easyeda_json.py` parses **`IMAGE~`**, **`TEXT~L~`**, **`SVGNODE`** (layer 3) for debug SVG. |

## Target outcomes

1. **Generator option** (or default): produce **vector silk** for the logo matching **`SVGNODE`** envelope and coordinate system (file units: **1 = 10 mil**, same as existing silk).
2. **Deterministic** pipeline: same input image + same TOML → same `shape[]` string (within float formatting tolerances).
3. **Dependencies**: any new library (e.g. Potrace bindings, OpenCV) is **optional** or **explicitly** added with documented install; no silent fallbacks that hide failures.
4. **Fallback**: keep **`IMAGE~`** path available (flag or automatic when tracing fails) so boards are not blocked.

## Technical approach

### 1. Raster → path (`d` string)

- **Preprocess**: grayscale, optional **threshold**, trim margins, resize to match **layout box in px** consistent with current **mil** box (same branding region math as `_compute_branding_layout`).
- **Trace** (choose one primary path; second as optional):
  - **Potrace** (via **`pypotrace`** or subprocess to CLI): strong for **high-contrast** logos.
  - **OpenCV** `findContours` + `approxPolyDP`: more control, more code; good for tuning.
- **Output**: single or multiple **closed paths** in **EasyEDA file units** (same numeric space as existing **`offset_silk_path_d`** for text).

### 2. Path → `SVGNODE` record

- Inspect **reference** `SVGNODE~{...}` from a real EasyEDA export (minimal JSON: `gId`, `nodeName`, `nodeType`, `layerid`, `attrs` with `d`, `stroke`, `id`).
- Implement **`append_branding_svgnode_shape(shapes, nid, d_file_units, ...)`** mirroring **`append_branding_easyeda_shapes`** placement (translate path so logo sits in **image** slot: same **left/top** as current `IMAGE~`).
- Assign **`gge*`** ids via existing **`nid()`** pattern.

### 3. Integration points

| Location | Change |
|----------|--------|
| `adapter_gen/branding.py` | Add **trace + SVGNODE** branch; optional **`use_vector_logo`** / **`logo_mode = "image" \| "svgnode" \| "auto"`** from TOML. |
| `adapter_gen/board_profile.py` | New optional **`[branding]`** keys, e.g. `logo_mode`, `trace_threshold`, `potrace_turdsize` (only if needed). |
| `scripts/generate_easyeda_adapter_pcb.py` | Pass new options into **`append_branding_*`**. |
| `adapter_gen/svg_preview.py` | Render traced paths for logo (stroke/fill rules matching editor or “ugly but honest” mode). |
| `scripts/branding_box_from_easyeda_json.py` | Already handles **`SVGNODE`**; extend tests / golden samples if format varies. |

### 4. Validation

- **Round-trip sanity**: generate JSON → import EasyEDA → export → compare **`SVGNODE`** count and **bbox** (not necessarily byte-identical).
- **Regression**: boards **without** branding unchanged; **`IMAGE~`**-only mode still works.
- **Size / DRC**: very large `d` strings → document **limits** (max path length, simplify step).

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Tracing **photo-like** art yields **huge** paths | Strong preprocessing (threshold, posterize); **warn** or **fail** if path &gt; N segments when `strict`. |
| **Potrace** not installed | Document **`apt install potrace`** + **`pip install pypotrace`**; or **OpenCV-only** path. |
| **Float** differences vs EasyEDA | Snap to **fixed decimals** in `d` if needed; align with **`offset_silk_path_d`** style. |
| **Pro** still differs | Treat as **separate** importer issue; document **Standard** as primary target. |

## Work breakdown (suggested order)

1. **Spike**: one script **`trace_logo_to_path.py`** (CLI): input PNG/JPEG → stdout **`d`** in file units + stats (segment count).
2. **Unit tests** on a **small synthetic** bitmap (e.g. white circle on black) → expected path bbox.
3. **`SVGNODE` emitter** in **`branding.py`** + TOML flag **`logo_mode`**.
4. Wire **preview** to traced paths.
5. **Docs**: TOML keys, dependencies, when to use **`IMAGE~`** vs **`SVGNODE`**.
6. Optional: **`auto`** mode — try trace, fall back to **`IMAGE~`** with logged warning.

## Out of scope (for this plan)

- **EasyEDA Pro** native **`OBJ`/`STRING`** format.
- **Guaranteed** pixel match between editor and fab (that is **Gerber** + fab rules).
- Changing **GPIO silk** or **copper** generation.

## References (in-repo)

- `adapter_gen/branding.py` — layout, **`IMAGE~`**, **`TEXT~L~`**
- `scripts/branding_box_from_easyeda_json.py` — **`SVGNODE`** parsing
- `resources/PCB_esp32-s3-devkitc-1.devkitc1.standard_2026-04-06.json` — real **`SVGNODE`** sample
