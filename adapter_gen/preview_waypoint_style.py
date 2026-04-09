"""Sizing for SVG preview waypoint markers (discussion only; not copper).

Aligns with ``row_reverser_geometry`` preview trace width and default gap.

**Layer colors** match EasyEDA Standard PCB editor: **TopLayer = red**, **BottomLayer = blue**
(preview strokes only; not gerber).
"""

from __future__ import annotations

# EasyEDA layer table: TopLayer #FF0000, BottomLayer #0000FF — softer variants for SVG.
TOP_COPPER_PREVIEW_STROKE = "#d32f2f"
BOTTOM_COPPER_PREVIEW_STROKE = "#1565c0"
TOP_COPPER_PREVIEW_DOT_FILL = "#ffcdd2"
TOP_COPPER_PREVIEW_LABEL_FILL = "#b71c1c"
BOTTOM_COPPER_PREVIEW_DOT_FILL = "#bbdefb"
BOTTOM_COPPER_PREVIEW_LABEL_FILL = "#0d47a1"

# Default signal trace width + gap (mil) — shared with ``row_reverser_geometry`` and
# ``scripts/row_reverser_svg.py`` so preview strokes match reverser sketch geometry.
TRACE_WIDTH_MIL = 6.0
TRACE_GAP_MIL = 8.0

# Dot diameter = trace width (marker reads as one trace wide).
MARKER_RADIUS_MIL = TRACE_WIDTH_MIL / 2.0
# Thin outline so the dot stays visible on light FR4 in SVG.
MARKER_STROKE_MIL = 0.75

# Min center-to-center spacing when packing markers along a segment (mil).
MIN_TRACE_CENTER_PITCH_MIL = TRACE_WIDTH_MIL + TRACE_GAP_MIL

# Temp index labels on waypoint overlays (preview-only; ``--routing-waypoints``).
LABEL_FONT_SIZE_MIL = 7.0
LABEL_DY_MIL = 9.0
