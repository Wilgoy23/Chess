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

_ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
_KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# ---------------------------------------------------------------------------
# Attack / check detection
# ---------------------------------------------------------------------------

def square_attacked(grid, row, col, by_color):
    """Return True if (row, col) is attacked by any piece of by_color.

    Looks outward from (row, col) along each attack pattern instead of
    scanning the board and regenerating every enemy piece's moves. Pawns
    only attack their two diagonal-forward squares; a pawn's straight push
    to an empty square is not an attack. A square already held by a
    by_color piece can't be attacked by by_color (nothing to capture).
    """
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

    for dr, dc in _KNIGHT_OFFSETS:
        nr, nc = row + dr, col + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            p = grid[nr][nc]
            if p and p.get_type() == "Knight" and p.get_color() == by_color:
                return True

    for dr, dc in _KING_OFFSETS:
        nr, nc = row + dr, col + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            p = grid[nr][nc]
            if p and p.get_type() == "King" and p.get_color() == by_color:
                return True

    for dr, dc in _ROOK_DIRS:
        nr, nc = row + dr, col + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            p = grid[nr][nc]
            if p is not None:
                if p.get_color() == by_color and p.get_type() in ("Rook", "Queen"):
                    return True
                break
            nr += dr
            nc += dc

    for dr, dc in _BISHOP_DIRS:
        nr, nc = row + dr, col + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            p = grid[nr][nc]
            if p is not None:
                if p.get_color() == by_color and p.get_type() in ("Bishop", "Queen"):
                    return True
                break
            nr += dr
            nc += dc

    return False


def find_king(grid, color):
    """Return (row, col) of color's king, or None if it isn't on the board."""
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_type() == "King" and p.get_color() == color:
                return (r, c)
    return None


def in_check(grid, color):
    """Return True if color's king is currently attacked."""
    king_pos = find_king(grid, color)
    if king_pos is None:
        return False  # king not found (shouldn't happen)
    opponent = "black" if color == "white" else "white"
    return square_attacked(grid, king_pos[0], king_pos[1], opponent)


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


def _shares_line(a, b):
    """True if squares a and b lie on a shared row, column, or diagonal.

    A move can only expose a discovered check on the king by vacating a
    square that sits between the king and an enemy slider on one of these
    lines — a piece not aligned with the king this way can never expose one,
    whatever its destination.
    """
    ar, ac = a
    br, bc = b
    return ar == br or ac == bc or abs(ar - br) == abs(ac - bc)


def get_legal_moves_from(grid, from_pos, castling_rights, en_passant_target=None,
                          king_pos=None, in_check_now=None):
    """Return legal destination squares for the piece at from_pos.

    One entry is returned per destination square even when a pawn move is a
    promotion (the promotion piece is chosen separately and doesn't affect
    legality).

    king_pos/in_check_now, if given, are color's king square and whether it's
    already under attack, both before this piece moves — an optimization for
    get_legal_moves, which already knows both and would otherwise make every
    candidate move re-derive them. Callers testing a single piece in
    isolation can omit them.

    Most candidate moves don't need the expensive make/unmake + attack-probe
    legality test at all: a move can only leave the king in check if the
    king is already in check, the piece is the king itself, the piece sits
    on a line to the king (so moving it *might* expose a discovered check —
    see _shares_line), or the move is an en passant capture (the one case
    that removes a piece off a square other than to_pos, so it can expose a
    check unaligned with the mover's own from/to squares — see position3's
    trap in tests/test_perft.py). Anything else is unconditionally legal.
    """
    fr, fc = from_pos
    piece = grid[fr][fc]
    if piece is None:
        return []
    color = piece.get_color()
    is_king = piece.get_type() == "King"
    is_pawn = piece.get_type() == "Pawn"

    raw = list(piece.get_possible_moves(grid, from_pos, en_passant_target) or [])
    if is_king:
        raw += get_castling_moves(grid, color, castling_rights)

    if not is_king and king_pos is None:
        king_pos = find_king(grid, color)
    opponent = "black" if color == "white" else "white"
    if not is_king and in_check_now is None:
        in_check_now = king_pos is not None and square_attacked(grid, king_pos[0], king_pos[1], opponent)
    aligned_with_king = not is_king and king_pos is not None and _shares_line(from_pos, king_pos)

    legal = []
    for to_pos in raw:
        is_en_passant = (
            is_pawn and to_pos == en_passant_target
            and to_pos[1] != fc and grid[to_pos[0]][to_pos[1]] is None
        )
        if not (is_king or in_check_now or aligned_with_king or is_en_passant):
            legal.append(to_pos)
            continue

        changes, _, _ = _apply_move_grid(grid, from_pos, to_pos, en_passant_target=en_passant_target)
        probe = to_pos if is_king else king_pos
        safe = probe is None or not square_attacked(grid, probe[0], probe[1], opponent)
        unmake_move(grid, changes)
        if safe:
            legal.append(to_pos)
    return legal


def get_legal_moves(grid, color, castling_rights, en_passant_target=None):
    """Return all (from_pos, to_pos) pairs for color that don't leave their
    own king in check. Includes castling and en passant destinations."""
    king_pos = find_king(grid, color)
    in_check_now = False
    if king_pos is not None:
        opponent = "black" if color == "white" else "white"
        in_check_now = square_attacked(grid, king_pos[0], king_pos[1], opponent)

    moves = []
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece is None or piece.get_color() != color:
                continue
            for to_pos in get_legal_moves_from(
                    grid, (r, c), castling_rights, en_passant_target, king_pos, in_check_now):
                moves.append(((r, c), to_pos))
    return moves


# ---------------------------------------------------------------------------
# Move application
# ---------------------------------------------------------------------------

_ROOK_HOME_SQUARES = {(7, 0), (7, 7), (0, 0), (0, 7)}


def _next_castling_rights(castling_rights, piece, from_pos, to_pos, captured):
    """Castling rights after moving `piece` from_pos->to_pos, given whatever
    (if anything) was captured on to_pos before the move.

    The vast majority of moves touch neither a king, a rook, nor a rook's
    home square, so they can't change castling rights at all — skip the
    dict copy and hand back the same object. Safe because nothing in this
    codebase ever mutates a castling_rights dict in place; a changed dict
    is always a freshly built replacement (see below).
    """
    ptype, color = piece.get_type(), piece.get_color()
    touches_rights = (
        ptype == "King"
        or (ptype == "Rook" and from_pos in _ROOK_HOME_SQUARES)
        or (captured is not None and captured.get_type() == "Rook" and to_pos in _ROOK_HOME_SQUARES)
    )
    if not touches_rights:
        return castling_rights

    new_castling_rights = {c: dict(v) for c, v in castling_rights.items()}

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

    return new_castling_rights


def _next_en_passant_target(piece, from_pos, to_pos):
    """The en passant target opened up by this move, or None.

    A pawn double-step opens up an en passant target on the skipped square.
    """
    if piece.get_type() == "Pawn" and abs(to_pos[0] - from_pos[0]) == 2:
        return ((from_pos[0] + to_pos[0]) // 2, from_pos[1])
    return None


def apply_move(grid, from_pos, to_pos, castling_rights, en_passant_target=None, promotion=None):
    """Apply a move to a copy of grid.

    Returns (new_grid, new_castling_rights, new_en_passant_target, is_irreversible).
    is_irreversible is True for pawn moves and captures (drives the fifty-move clock).

    For repeated apply/undo in a search loop, prefer `make_move`/`unmake_move`,
    which mutate grid in place instead of copying it.
    """
    new_grid = [row[:] for row in grid]
    _, piece, captured = _apply_move_grid(new_grid, from_pos, to_pos, en_passant_target, promotion)

    new_castling_rights = _next_castling_rights(castling_rights, piece, from_pos, to_pos, captured)
    new_en_passant_target = _next_en_passant_target(piece, from_pos, to_pos)
    is_irreversible = piece.get_type() == "Pawn" or captured is not None

    return new_grid, new_castling_rights, new_en_passant_target, is_irreversible


def _apply_move_grid(grid, from_pos, to_pos, en_passant_target=None, promotion=None):
    """Mutate grid in place for a single move; return (changes, piece, captured).

    The grid-mutation half of make_move, split out so callers that only need
    to probe a resulting position (get_legal_moves_from's legality test) can
    skip computing castling rights / en passant target, which they'd
    otherwise immediately discard.
    """
    fr, fc = from_pos
    piece = grid[fr][fc]
    captured = grid[to_pos[0]][to_pos[1]]

    changes = []
    for origin, destination, piece_obj in piece.move(
            grid, from_pos, to_pos, promotion=promotion, en_passant_target=en_passant_target):
        dr, dc = destination
        changes.append((destination, grid[dr][dc]))
        grid[dr][dc] = piece_obj
        orow, ocol = origin
        changes.append((origin, grid[orow][ocol]))
        grid[orow][ocol] = None

    return changes, piece, captured


def make_move(grid, from_pos, to_pos, castling_rights, en_passant_target=None, promotion=None):
    """Apply a move to grid in place. Reverse with unmake_move(grid, changes).

    Returns (changes, new_castling_rights, new_en_passant_target, is_irreversible)
    — the same trailing three values as apply_move, plus an opaque undo record
    in place of a new grid. Intended for search loops (perft, minimax, MCTS
    rollouts) that apply and then backtrack many moves in a row without
    needing to keep the pre-move grid around.
    """
    changes, piece, captured = _apply_move_grid(grid, from_pos, to_pos, en_passant_target, promotion)

    new_castling_rights = _next_castling_rights(castling_rights, piece, from_pos, to_pos, captured)
    new_en_passant_target = _next_en_passant_target(piece, from_pos, to_pos)
    is_irreversible = piece.get_type() == "Pawn" or captured is not None

    return changes, new_castling_rights, new_en_passant_target, is_irreversible


def unmake_move(grid, changes):
    """Reverse a make_move call, given the `changes` it returned."""
    for (r, c), previous_occupant in reversed(changes):
        grid[r][c] = previous_occupant


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
