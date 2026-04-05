"""Sizing for SVG preview waypoint markers (discussion only; not copper).

Aligns with ``row_reverser_geometry`` preview trace width and default gap.
"""

from __future__ import annotations

# Match row-reverser preview / typical default signal trace width (mil).
TRACE_WIDTH_MIL = 6.0
# Same base as ``_DEFAULT_TRACE_GAP`` in row_reverser_geometry.
TRACE_GAP_MIL = 8.0

# Dot diameter = trace width (marker reads as one trace wide).
MARKER_RADIUS_MIL = TRACE_WIDTH_MIL / 2.0
# Thin outline so the dot stays visible on light FR4 in SVG.
MARKER_STROKE_MIL = 0.75

# Min center-to-center spacing when packing markers along a segment (mil).
MIN_TRACE_CENTER_PITCH_MIL = TRACE_WIDTH_MIL + TRACE_GAP_MIL

# Temp labels — small; remove once routing is final.
LABEL_FONT_SIZE_MIL = 7.0
LABEL_DY_MIL = 9.0
