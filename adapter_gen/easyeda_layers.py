"""EasyEDA Standard PCB layer ids (compressed ``shape[]`` strings).

Official ``TRACK`` format: ``TRACK~strokeWidth~layerId~net~points~gId~locked``.
After splitting on ``~``, index 2 is **layer id** — must match the first field of each
``layers[]`` entry in ``build_standard_compressed``:

- ``1`` = TopLayer (editor red / #FF0000)
- ``2`` = BottomLayer (editor blue / #0000FF)

Routing (2-layer adapter, ``stem_neck_emit`` + ``row_reverser_emit``):

**TopLayer (1):** row-reverser Layer A (``geom.cyan`` — pad↔edge vias, row-A ties, stubs);
wide-head stub end → straddle (or pin 1); left stem neck (straddle → ``x_ln``) for nets 2…N/2.

**BottomLayer (2):** row-reverser Layer B (``geom.red`` — inner horizontals to gap vias);
J3 wide-head row-B columns; J3 stem-side → right straddle/pin; right stem neck
(straddle → ``x_rn``) for nets N/2+2…N — same layer as J3 head art so straddle
meets copper without extra vias at the waypoint.

PTH pads are multi-layer; TRACK segments follow the above.
"""

from __future__ import annotations

# Sync with ``layers`` in ``scripts/generate_easyeda_adapter_pcb.py`` ``build_*``.
EASYEDA_TOP_LAYER_ID = "1"
EASYEDA_BOTTOM_LAYER_ID = "2"

# Plated routing vias (mil). File units in JSON: 1 = 10 mil (``mil_to_u`` in generator).
# Drill Ø ≈ 8 mil → hole radius 4 mil. Outer = via pad (annulus); 16 mil is typical ring budget.
# Must match ``VIA~`` in ``row_reverser_emit`` and DRCRULE in ``generate_easyeda_adapter_pcb``.
ROUTING_VIA_OUTER_DIAM_MIL = 16.0
ROUTING_VIA_HOLE_RADIUS_MIL = 4.0
