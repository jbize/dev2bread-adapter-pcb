"""Pure helpers for devkitc board-ID silk placement (see ``adapter_gen.silk_preview``)."""

from __future__ import annotations

from adapter_gen.silk_preview import BOARD_ID_LINE_GAP_MIL, board_id_line_y_offsets_mil


def test_board_id_line_y_offsets_empty() -> None:
    assert board_id_line_y_offsets_mil(0) == []


def test_board_id_line_y_offsets_single_centered() -> None:
    assert board_id_line_y_offsets_mil(1) == [0.0]


def test_board_id_line_y_offsets_pair_symmetric() -> None:
    g = BOARD_ID_LINE_GAP_MIL
    assert board_id_line_y_offsets_mil(2) == [-g / 2.0, g / 2.0]


def test_board_id_line_y_offsets_three() -> None:
    g = BOARD_ID_LINE_GAP_MIL
    assert board_id_line_y_offsets_mil(3) == [-g, 0.0, g]
