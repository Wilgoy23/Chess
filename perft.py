"""Perft: enumerate every legal move path to a fixed depth and count leaves.

Perft is the standard correctness test for a chess rules engine. Comparing
node counts against published values for well-known positions catches almost
every move-generation bug (missed pins, bad castling-through-check, en passant
edge cases, promotion counting) that eyeballing games will not.

Promotions count as four distinct moves, so a pawn move to the last rank is
expanded into Queen/Rook/Bishop/Knight here even though `rules.get_legal_moves`
returns one entry per destination square.

Run directly for a quick check or to debug a mismatch:

    python perft.py --depth 4
    python perft.py --fen "<fen>" --depth 3 --divide
"""

import argparse
import time

import rules
from fen import START_FEN, coords_to_square, parse_fen

_PROMO_LETTER = {"Queen": "q", "Rook": "r", "Bishop": "b", "Knight": "n"}


def _promotions(grid, from_pos, to_pos):
    """The promotion choices for a move: all four, or the single non-promotion."""
    if rules.is_promotion_move(grid, from_pos, to_pos):
        return rules.PROMOTION_TYPES
    return (None,)


def move_name(from_pos, to_pos, promotion=None):
    """UCI-style name for a move, e.g. "e2e4" or "a7a8q"."""
    name = coords_to_square(*from_pos) + coords_to_square(*to_pos)
    return name + _PROMO_LETTER[promotion] if promotion else name


def perft(position, depth):
    """Count leaf nodes `depth` plies below `position` (a `fen.Position`)."""
    return _perft(position.grid, position.turn, position.castling_rights,
                  position.en_passant_target, depth)


def _perft(grid, color, castling_rights, en_passant_target, depth):
    if depth <= 0:
        return 1

    opponent = "black" if color == "white" else "white"
    total = 0
    for from_pos, to_pos in rules.get_legal_moves(grid, color, castling_rights, en_passant_target):
        for promotion in _promotions(grid, from_pos, to_pos):
            changes, new_rights, new_ep, _ = rules.make_move(
                grid, from_pos, to_pos, castling_rights, en_passant_target,
                promotion=promotion,
            )
            total += _perft(grid, opponent, new_rights, new_ep, depth - 1)
            rules.unmake_move(grid, changes)
    return total


def perft_divide(position, depth):
    """Per-root-move node counts, keyed by UCI move name.

    The tool of choice when a total disagrees with the published value: diff
    this against a known-good engine's `go perft` output to find the move whose
    subtree is wrong, then recurse into it.
    """
    grid, color = position.grid, position.turn
    castling_rights, en_passant_target = position.castling_rights, position.en_passant_target
    opponent = "black" if color == "white" else "white"

    counts = {}
    for from_pos, to_pos in rules.get_legal_moves(grid, color, castling_rights, en_passant_target):
        for promotion in _promotions(grid, from_pos, to_pos):
            changes, new_rights, new_ep, _ = rules.make_move(
                grid, from_pos, to_pos, castling_rights, en_passant_target,
                promotion=promotion,
            )
            counts[move_name(from_pos, to_pos, promotion)] = _perft(
                grid, opponent, new_rights, new_ep, depth - 1
            )
            rules.unmake_move(grid, changes)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fen", default=START_FEN, help="position to search (default: startpos)")
    parser.add_argument("--depth", type=int, default=3, help="plies to search (default: 3)")
    parser.add_argument("--divide", action="store_true", help="also print per-root-move counts")
    args = parser.parse_args()

    position = parse_fen(args.fen)
    start = time.perf_counter()
    if args.divide:
        counts = perft_divide(position, args.depth)
        for name in sorted(counts):
            print(f"{name}: {counts[name]}")
        nodes = sum(counts.values())
    else:
        nodes = perft(position, args.depth)
    elapsed = time.perf_counter() - start

    print(f"\nperft({args.depth}) = {nodes} in {elapsed:.2f}s "
          f"({nodes / elapsed:,.0f} nodes/s)")


if __name__ == "__main__":
    main()
