# Routing invariants (preview + layout intent)

These rules are **design constraints** for this adapter: SVG preview sketches and any
generated copper should stay consistent with them.

## Waypoint ↔ stem pin (neck)

- Each **neck waypoint** is tied to **exactly one** left-stem **pin / hole** (same logical net).
- **Pin 1** has **no** neck waypoint; it is the anchor / start of the straddle row.
- Waypoint **k** (for k ≥ 2 in the neck sequence used in preview) corresponds to **stem pin k**
  on the **left** straddle column only—**one net, one hole**, no many-to-one mapping.

## Same layer: no unintended connectivity

- On a **single copper layer**, traces are **not** allowed to **cross** in a way that would
  imply current could flow between nets on that layer. Separate nets need spatial separation
  or layer changes (vias)—not arbitrary crossings on the same layer.
- **This adapter** is laid out so that **circuits do not cross on the same layer** in the
  sense above: same-layer artwork should not depict or realize crossing traces between
  distinct nets.

## Preview vs fabrication

- SVG preview paths are **discussion geometry** unless mirrored in EasyEDA export; they still
  should follow these invariants so previews do not suggest illegal same-layer shorts or
  ambiguous crossings.
- **Stem neck (left column, nets 2…):** EasyEDA Standard output now includes TopLayer
  ``TRACK`` segments from ``adapter_gen/stem_neck_routing_mil`` (same as the cyan neck preview).
  Head-to-neck and pin-1 stem legs are still not auto-generated there.
