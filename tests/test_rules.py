"""Unit tests for the PRD 1.2 move-generation performance rewrite.

Perft already exercises make_move/unmake_move and square_attacked deeply and
would eventually notice a bug in either, but a wrong node count doesn't say
which primitive is at fault. These tests pin each one down directly:

- make_move/unmake_move must round-trip the grid back to its exact starting
  state, and must agree with the older, still-present apply_move (which
  copies the grid instead of mutating it) on the resulting position.
- The ray-based square_attacked rewrite must agree with a deliberately naive
  reference (scan every square, ask each piece if it could move here) that
  mirrors the pre-rewrite implementation, across several tactically dense
  positions.
"""

import rules
from fen import parse_fen, square_to_coords

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
POSITION3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
POSITION4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
POSITION5 = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"
POSITION6 = "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"
EN_PASSANT_FEN = "rnbqkbnr/pp2pppp/8/3pP3/2p5/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 4"

# (label, fen, from_square, to_square, promotion)
MOVE_CASES = [
    ("quiet",        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e2", "e4", None),
    ("capture",      KIWIPETE, "e5", "d7", None),
    ("kingside_o_o", KIWIPETE, "e1", "g1", None),
    ("queenside_o_o_o", KIWIPETE, "e1", "c1", None),
    ("en_passant",   EN_PASSANT_FEN, "e5", "d6", None),
    ("promotion_q",  POSITION4, "a7", "a8", "Queen"),
    ("promotion_n",  POSITION4, "a7", "b8", "Knight"),
]


def _signature(grid):
    """(color, type)-per-square snapshot; stable across object identity so
    it can compare a promoted piece from one code path to another."""
    return tuple(
        (p.get_color(), p.get_type()) if p else None
        for row in grid for p in row
    )


def test_make_unmake_round_trips_to_identical_grid():
    for label, fen, from_sq, to_sq, promotion in MOVE_CASES:
        position = parse_fen(fen)
        grid = position.grid
        before = _signature(grid)

        changes, _, _, _ = rules.make_move(
            grid, square_to_coords(from_sq), square_to_coords(to_sq),
            position.castling_rights, position.en_passant_target, promotion=promotion,
        )
        assert _signature(grid) != before, f"{label}: grid didn't change"

        rules.unmake_move(grid, changes)
        assert _signature(grid) == before, f"{label}: unmake didn't restore the grid"


def test_make_move_agrees_with_apply_move():
    for label, fen, from_sq, to_sq, promotion in MOVE_CASES:
        position = parse_fen(fen)
        from_pos, to_pos = square_to_coords(from_sq), square_to_coords(to_sq)

        copy_grid, copy_cr, copy_ep, copy_irrev = rules.apply_move(
            position.grid, from_pos, to_pos,
            position.castling_rights, position.en_passant_target, promotion=promotion,
        )

        mutate_grid = [row[:] for row in position.grid]
        _, mutate_cr, mutate_ep, mutate_irrev = rules.make_move(
            mutate_grid, from_pos, to_pos,
            position.castling_rights, position.en_passant_target, promotion=promotion,
        )

        assert _signature(mutate_grid) == _signature(copy_grid), label
        assert mutate_cr == copy_cr, label
        assert mutate_ep == copy_ep, label
        assert mutate_irrev == copy_irrev, label


# ---------------------------------------------------------------------------
# square_attacked vs. a deliberately naive reference
# ---------------------------------------------------------------------------

def _square_attacked_naive(grid, row, col, by_color):
    """Pre-rewrite approach: scan every square, ask each piece if (row, col)
    is one of its pseudo-legal destinations. Deliberately not shared code
    with rules.square_attacked, so it can catch a regression there.

    Every real caller only ever probes a square that's either empty or held
    by the *other* color (an empty castling-path square, or the color's own
    king when testing check) — never a square held by a by_color piece
    itself, so "can by_color capture its own piece here" is never a
    meaningful question in practice. Guard it the same way
    rules.square_attacked does, rather than leaving it to the accident of
    whether a given attacker type's move generator happens to filter out
    own-occupied squares (sliders and knights do; the pawn-attack check here
    never did, since it never consulted the target square at all)."""
    occupant = grid[row][col]
    if occupant is not None and occupant.get_color() == by_color:
        return False

    pawn_direction = -1 if by_color == "white" else 1
    for dc in (-1, 1):
        pr, pc = row - pawn_direction, col + dc
        if 0 <= pr < 8 and 0 <= pc < 8:
            p = grid[pr][pc]
            if p and p.get_type() == "Pawn" and p.get_color() == by_color:
                return True

    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_color() == by_color and p.get_type() != "Pawn":
                if (row, col) in (p.get_possible_moves(grid, (r, c)) or []):
                    return True
    return False


def test_square_attacked_matches_naive_reference():
    for fen in (KIWIPETE, POSITION3, POSITION4, POSITION5, POSITION6):
        grid = parse_fen(fen).grid
        for row in range(8):
            for col in range(8):
                for color in ("white", "black"):
                    fast = rules.square_attacked(grid, row, col, color)
                    naive = _square_attacked_naive(grid, row, col, color)
                    assert fast == naive, f"{fen} @ ({row},{col}) by {color}"
