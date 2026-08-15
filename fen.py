"""FEN (Forsyth-Edwards Notation) parsing.

Deliberately free of pygame so that tests, perft, and headless tooling can set
up an arbitrary position without opening a display. Produces exactly the
primitive representation `rules.py` operates on:

    grid              : 8x8 list of piece objects (or None), row 0 = rank 8
    turn              : "white" or "black"
    castling_rights   : {"white": {"kingside": bool, "queenside": bool}, ...}
    en_passant_target : (row, col) or None
"""

from typing import NamedTuple

from Pieces.Pawn import Pawn
from Pieces.Rook import Rook
from Pieces.Knight import Knight
from Pieces.Bishop import Bishop
from Pieces.Queen import Queen
from Pieces.King import King

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_PIECE_CLASSES = {
    "p": Pawn, "r": Rook, "n": Knight, "b": Bishop, "q": Queen, "k": King,
}

_COL_NAMES = "abcdefgh"


class Position(NamedTuple):
    """A complete position, ready to hand to the functions in `rules`."""
    grid: list
    turn: str
    castling_rights: dict
    en_passant_target: tuple | None
    halfmove_clock: int
    fullmove_number: int


def square_to_coords(square):
    """Convert algebraic notation ("e3") to grid coordinates (row, col)."""
    if len(square) != 2 or square[0] not in _COL_NAMES or square[1] not in "12345678":
        raise ValueError(f"invalid square: {square!r}")
    return 8 - int(square[1]), _COL_NAMES.index(square[0])


def coords_to_square(row, col):
    """Convert grid coordinates (row, col) to algebraic notation ("e3")."""
    return f"{_COL_NAMES[col]}{8 - row}"


def parse_fen(fen):
    """Parse a FEN string into a Position.

    The halfmove-clock and fullmove-number fields are optional; they default
    to 0 and 1 the way most abbreviated FENs intend.
    """
    fields = fen.split()
    if len(fields) < 4:
        raise ValueError(f"FEN needs at least 4 fields, got {len(fields)}: {fen!r}")

    placement, active, castling, en_passant = fields[:4]
    halfmove_clock = int(fields[4]) if len(fields) > 4 else 0
    fullmove_number = int(fields[5]) if len(fields) > 5 else 1

    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError(f"FEN placement needs 8 ranks, got {len(ranks)}: {placement!r}")

    grid = [[None] * 8 for _ in range(8)]
    for row, rank in enumerate(ranks):
        col = 0
        for ch in rank:
            if ch.isdigit():
                col += int(ch)
            else:
                piece_cls = _PIECE_CLASSES.get(ch.lower())
                if piece_cls is None:
                    raise ValueError(f"unknown piece {ch!r} in FEN: {fen!r}")
                if col > 7:
                    raise ValueError(f"rank {8 - row} overflows: {rank!r}")
                grid[row][col] = piece_cls("white" if ch.isupper() else "black")
                col += 1
        if col != 8:
            raise ValueError(f"rank {8 - row} covers {col} files, expected 8: {rank!r}")

    if active not in ("w", "b"):
        raise ValueError(f"invalid side to move: {active!r}")

    castling_rights = {
        "white": {"kingside": "K" in castling, "queenside": "Q" in castling},
        "black": {"kingside": "k" in castling, "queenside": "q" in castling},
    }

    en_passant_target = None if en_passant == "-" else square_to_coords(en_passant)

    return Position(grid, "white" if active == "w" else "black",
                    castling_rights, en_passant_target,
                    halfmove_clock, fullmove_number)
