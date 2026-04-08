# Branding: EasyEDA Pro (`.epcb`) vs Standard (`*.standard.json`)

Reference: a Pro save of the same adapter after manual branding (`resources/esp32-s3-devkitc-1.devkitc1.standard.epcb`, lines cited as of the commit that added this doc).

## Pro format (native objects)

### Image — `OBJ`

Example:

```text
["OBJ","e753",0,3,"Godswind-east.jpg",-1070,1420,500,500,0,0,"blob:…",0]
```

| Meaning | Value |
|--------|--------|
| Layer `3` | Top Silkscreen (matches `LAYER` table in the same file) |
| Filename | `Godswind-east.jpg` |
| Position | `-1070`, `1420` (document coordinates, **mil** in Pro) |
| Size | `500` × `500` **mil** |
| Pixel data | `blob:…` URL — **not** embedded base64 in the line; resolved by the editor / asset store |

### Text — `STRING`

Example:

```text
["STRING","e751",0,3,277,1157.5,"Godswind Consulting","Copperplate Gothic Light",130,10,0,0,5,0,0,0,0,0]
```

| Meaning | Value |
|--------|--------|
| Layer `3` | Top Silkscreen |
| Center | `277`, `1157.5` **mil** |
| String | `Godswind Consulting` |
| Font | `Copperplate Gothic Light` (OS/editor font) |
| Height / stroke | `130` **mil** height, `10` **mil** stroke (typical Pro fields) |

### Outline data — `FONT`

A separate `FONT` row tessellates the same string for rendering/DRC (polylines per glyph). This is **not** the same encoding as Standard `TEXT~L~…~M…`.

## Standard format (this repo’s generator)

Emitted by `append_branding_easyeda_shapes` in `adapter_gen/branding.py`:

| Piece | Standard encoding |
|-------|-------------------|
| Image | `IMAGE~x~y~w~h~3~<base64 PNG>~id` — coordinates in **file units** (`mil / 10`); **PNG bytes embedded** in JSON |
| Text | `TEXT~L~cx~cy~stroke~0~none~3~~5~<label>~<path d>~~id` — **vector path** from matplotlib `TextPath`, not a live font name |

There is **no** official Pro → Standard exporter; formats differ by design.

## Can the generator use the “same parameters” as Pro?

**Same file format as Pro (`OBJ` / `STRING`):** **No.** `scripts/generate_easyeda_adapter_pcb.py` only writes **EasyEDA Standard** compressed JSON (`build_standard_compressed`). It does not emit Pro JSONL or blob URLs.

**Same numbers (placement and size in mil), approximately:**

- **Image:** Layout is computed in **mil** in `_compute_branding_layout` (gap region, aspect ratio, max size). You can tune `[branding]` and geometry so the emitted **IMAGE~** ends up near a target width/height/corner **in mil**, but values will only match Pro **if** you align board origin, outline, and branding box to that design. Pro’s `(-1070, 1420)` is in **Pro’s** coordinate system; Standard uses the same **geometry** module as the SVG preview, not arbitrary Pro offsets.
- **Text:** The generator does **not** output a font family string for Standard silk. It outputs **path outlines**. To **visually** match `Copperplate Gothic Light`, set `[branding].font_family` (and related fields) to a face **matplotlib can resolve** on the build machine — ideally the same name as in Pro if the font is installed. **Height 130 mil** vs **stroke 10 mil** are not separate first-class TOML knobs today: text is **scaled to fill** the branding text box; stroke is `BRANDING_TEXT_STROKE_FILE_U` (file units → mil). Matching Pro exactly would require **code/TOML changes** (e.g. optional fixed height/stroke in mil).

**Summary:** You can push **geometry** toward Pro-like numbers and choose a **font family** for path generation; you **cannot** make Standard JSON structurally identical to Pro `OBJ`/`STRING` without a different exporter or a new format target.
