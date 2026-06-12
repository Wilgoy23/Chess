"""
Central chess rules engine.

This module is the single source of truth for move generation, check
detection, move application, and game-end conditions. It operates on the
board's primitive representation:

    grid              : 8x8 list of piece objects (or None), row 0 = rank 8
    color             : "white" or "black"
    castling_rights   : {"white": {"kingside": bool, "queenside": bool},
                          "black": {"kingside": bool, "queenside": bool}}
    en_passant_target : (row, col) of the square a pawn may capture onto via
                         en passant, or None

Both the human-facing Board and every AI agent share this module so they
always agree on what is legal.
"""

PROMOTION_TYPES = ["Queen", "Rook", "Bishop", "Knight"]


# ---------------------------------------------------------------------------
# Attack / check detection
# ---------------------------------------------------------------------------

def square_attacked(grid, row, col, by_color):
    """Return True if (row, col) is attacked by any piece of by_color.

    Pawns only attack their two diagonal-forward squares; a pawn's straight
    push to an empty square is not an attack, even though it appears in
    get_possible_moves().
    """
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


def in_check(grid, color):
    """Return True if color's king is currently attacked."""
    opponent = "black" if color == "white" else "white"
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_type() == "King" and p.get_color() == color:
                return square_attacked(grid, r, c, opponent)
    return False  # king not found (shouldn't happen)


# ---------------------------------------------------------------------------
# Move generation
# ---------------------------------------------------------------------------

def get_castling_moves(grid, color, castling_rights):
    """Return king destination squares ((row, col)) for legal castling moves."""
    moves = []
    row = 7 if color == "white" else 0
    rights = castling_rights[color]
    opponent = "black" if color == "white" else "white"

    king = grid[row][4]
    if king is None or king.get_type() != "King" or king.get_color() != color:
        return moves
    # Can't castle while in check
    if in_check(grid, color):
        return moves

    # Kingside: e->f->g must be clear and f, g not attacked
    if (rights["kingside"]
            and grid[row][5] is None
            and grid[row][6] is None
            and not square_attacked(grid, row, 5, opponent)
            and not square_attacked(grid, row, 6, opponent)):
        moves.append((row, 6))

    # Queenside: b, c, d must be empty; d, c not attacked (king passes through d, c)
    if (rights["queenside"]
            and grid[row][1] is None
            and grid[row][2] is None
            and grid[row][3] is None
            and not square_attacked(grid, row, 3, opponent)
            and not square_attacked(grid, row, 2, opponent)):
        moves.append((row, 2))

    return moves


def get_legal_moves_from(grid, from_pos, castling_rights, en_passant_target=None):
    """Return legal destination squares for the piece at from_pos.

    One entry is returned per destination square even when a pawn move is a
    promotion (the promotion piece is chosen separately and doesn't affect
    legality).
    """
    fr, fc = from_pos
    piece = grid[fr][fc]
    if piece is None:
        return []
    color = piece.get_color()

    raw = list(piece.get_possible_moves(grid, from_pos, en_passant_target) or [])
    if piece.get_type() == "King":
        raw += get_castling_moves(grid, color, castling_rights)

    legal = []
    for to_pos in raw:
        tr, tc = to_pos
        test = [row_[:] for row_ in grid]
        test[tr][tc] = test[fr][fc]
        test[fr][fc] = None
        # Simulate castling rook relocation in the test grid
        if piece.get_type() == "King" and abs(tc - fc) == 2:
            if tc == 6:
                test[fr][5] = test[fr][7]
                test[fr][7] = None
            else:
                test[fr][3] = test[fr][0]
                test[fr][0] = None
        if not in_check(test, color):
            legal.append(to_pos)
    return legal


def get_legal_moves(grid, color, castling_rights, en_passant_target=None):
    """Return all (from_pos, to_pos) pairs for color that don't leave their
    own king in check. Includes castling and en passant destinations."""
    moves = []
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece is None or piece.get_color() != color:
                continue
            for to_pos in get_legal_moves_from(grid, (r, c), castling_rights, en_passant_target):
                moves.append(((r, c), to_pos))
    return moves


# ---------------------------------------------------------------------------
# Move application
# ---------------------------------------------------------------------------

def apply_move(grid, from_pos, to_pos, castling_rights, en_passant_target=None, promotion=None):
    """Apply a move to a copy of grid.

    Returns (new_grid, new_castling_rights, new_en_passant_target, is_irreversible).
    is_irreversible is True for pawn moves and captures (drives the fifty-move clock).
    """
    new_grid = [row[:] for row in grid]
    fr, fc = from_pos
    piece = new_grid[fr][fc]
    captured = new_grid[to_pos[0]][to_pos[1]]

    new_castling_rights = {c: dict(v) for c, v in castling_rights.items()}

    for origin, destination, piece_obj in piece.move(
            new_grid, from_pos, to_pos, promotion=promotion, en_passant_target=en_passant_target):
        new_grid[destination[0]][destination[1]] = piece_obj
        new_grid[origin[0]][origin[1]] = None

    ptype, color = piece.get_type(), piece.get_color()

    # Revoke castling rights if a corner rook is captured
    if captured is not None and captured.get_type() == "Rook":
        if   to_pos == (7, 0): new_castling_rights["white"]["queenside"] = False
        elif to_pos == (7, 7): new_castling_rights["white"]["kingside"]  = False
        elif to_pos == (0, 0): new_castling_rights["black"]["queenside"] = False
        elif to_pos == (0, 7): new_castling_rights["black"]["kingside"]  = False

    # Revoke castling rights if the king or a rook moves from its home square
    if ptype == "King":
        new_castling_rights[color]["kingside"]  = False
        new_castling_rights[color]["queenside"] = False
    elif ptype == "Rook":
        if   from_pos == (7, 0): new_castling_rights["white"]["queenside"] = False
        elif from_pos == (7, 7): new_castling_rights["white"]["kingside"]  = False
        elif from_pos == (0, 0): new_castling_rights["black"]["queenside"] = False
        elif from_pos == (0, 7): new_castling_rights["black"]["kingside"]  = False

    # A pawn double-step opens up an en passant target on the skipped square
    new_en_passant_target = None
    if ptype == "Pawn" and abs(to_pos[0] - from_pos[0]) == 2:
        new_en_passant_target = ((from_pos[0] + to_pos[0]) // 2, from_pos[1])

    is_irreversible = ptype == "Pawn" or captured is not None

    return new_grid, new_castling_rights, new_en_passant_target, is_irreversible


# ---------------------------------------------------------------------------
# Game-end conditions
# ---------------------------------------------------------------------------

def is_promotion_move(grid, from_pos, to_pos):
    """Return True if moving the piece at from_pos to to_pos is a pawn promotion."""
    piece = grid[from_pos[0]][from_pos[1]]
    if piece is None or piece.get_type() != "Pawn":
        return False
    return to_pos[0] in (0, 7)


def is_insufficient_material(grid):
    """Return True if neither side has enough material to ever deliver checkmate.

    Covers: K vs K; K+minor vs K; K+B vs K+B with same-coloured bishops.
    """
    non_king = []
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_type() != "King":
                non_king.append((p.get_color(), p.get_type(), r, c))

    if not non_king:
        return True  # K vs K

    if len(non_king) == 1 and non_king[0][1] in ("Bishop", "Knight"):
        return True  # K+minor vs K

    if (len(non_king) == 2
            and non_king[0][1] == "Bishop" and non_king[1][1] == "Bishop"
            and non_king[0][0] != non_king[1][0]):
        _, _, r1, c1 = non_king[0]
        _, _, r2, c2 = non_king[1]
        if (r1 + c1) % 2 == (r2 + c2) % 2:
            return True  # K+B vs K+B, same-coloured bishops

    return False


def position_key(grid, turn, castling_rights, en_passant_target=None):
    """Hashable signature of a position, for threefold-repetition tracking."""
    board_state = tuple(
        (p.get_color(), p.get_type()) if p else None
        for row in grid for p in row
    )
    rights = (
        castling_rights["white"]["kingside"], castling_rights["white"]["queenside"],
        castling_rights["black"]["kingside"], castling_rights["black"]["queenside"],
    )
    return (board_state, turn, rights, en_passant_target)


def get_game_result(grid, color, castling_rights, en_passant_target, halfmove_clock, position_counts):
    """Return None if the game continues for `color` to move, else one of:
    "checkmate", "stalemate", "fifty_move_rule", "threefold_repetition",
    "insufficient_material".
    """
    if not get_legal_moves(grid, color, castling_rights, en_passant_target):
        return "checkmate" if in_check(grid, color) else "stalemate"

    if halfmove_clock >= 100:
        return "fifty_move_rule"

    key = position_key(grid, color, castling_rights, en_passant_target)
    if position_counts.get(key, 0) >= 3:
        return "threefold_repetition"

    if is_insufficient_material(grid):
        return "insufficient_material"

    return None
