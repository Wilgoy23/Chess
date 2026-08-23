"""Perft validation of the rules engine.

Node counts are the published values from the Chess Programming Wiki's perft
results page. A mismatch means move generation is wrong somewhere; use
`python perft.py --fen "<fen>" --depth N --divide` to find which root move's
subtree disagrees.

Deep cases are marked `slow` and skipped unless you pass `--runslow` (or set
PERFT_SLOW=1). After the PRD 1.2 move-generation speedup, the full set takes
under two minutes; the default set takes a few seconds.
"""

import pytest

import rules
from fen import START_FEN, parse_fen, square_to_coords
from perft import perft

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

# name -> (fen, node counts for depth 1, 2, 3, ...)
POSITIONS = {
    "startpos": (START_FEN, [20, 400, 8902, 197281, 4865609]),
    "kiwipete": (KIWIPETE, [48, 2039, 97862, 4085603]),
    "position3": ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
                  [14, 191, 2812, 43238, 674624]),
    "position4": ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
                  [6, 264, 9467, 422333]),
    "position5": ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
                  [44, 1486, 62379, 2103487]),
    "position6": ("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
                  [46, 2079, 89890, 3894594]),
}

# Cases above this node count are gated behind --runslow. Lower the bar as the
# engine gets faster (PRD 1.2) until the whole set fits in the default run.
FAST_MAX_NODES = 500_000


def _cases():
    for name, (fen, counts) in POSITIONS.items():
        for depth, expected in enumerate(counts, start=1):
            marks = [pytest.mark.slow] if expected > FAST_MAX_NODES else []
            yield pytest.param(fen, depth, expected, marks=marks,
                               id=f"{name}-d{depth}")


@pytest.mark.parametrize("fen, depth, expected", list(_cases()))
def test_perft(fen, depth, expected):
    assert perft(parse_fen(fen), depth) == expected


def test_en_passant_capture_exposing_own_king_is_illegal():
    """Position 3's trap, kept as a named case because perft found it here.

    After 1. g4, Black's f4 pawn appears to be able to take en passant, but
    fxg3 e.p. vacates f4 *and* removes the pawn on g4, opening the fourth rank
    from the white rook on b4 to the black king on h4.
    """
    position = parse_fen("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1")
    after_g4, rights, en_passant, _ = rules.apply_move(
        position.grid, square_to_coords("g2"), square_to_coords("g4"),
        position.castling_rights, position.en_passant_target,
    )
    assert en_passant == square_to_coords("g3")

    targets = rules.get_legal_moves_from(
        after_g4, square_to_coords("f4"), rights, en_passant
    )
    assert square_to_coords("g3") not in targets
    assert targets == [square_to_coords("f3")]
