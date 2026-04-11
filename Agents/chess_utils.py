"""Shared chess logic utilities used by agents."""


def is_in_check(grid, color):
    """Return True if color's king is attacked by any opponent piece."""
    opponent = "black" if color == "white" else "white"
    # Locate the king
    king_pos = None
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_type() == "King" and p.get_color() == color:
                king_pos = (r, c)
                break
        if king_pos:
            break
    if king_pos is None:
        return True  # king missing — treat as checked (shouldn't happen)

    kr, kc = king_pos
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_color() == opponent:
                if king_pos in (p.get_possible_moves(grid, (r, c)) or []):
                    return True
    return False


def _is_square_attacked(grid, row, col, by_color):
    """Return True if (row, col) is reachable by any piece of by_color."""
    for r in range(8):
        for c in range(8):
            p = grid[r][c]
            if p and p.get_color() == by_color:
                if (row, col) in (p.get_possible_moves(grid, (r, c)) or []):
                    return True
    return False


def _get_castling_moves(grid, color):
    """
    Generate pseudo-legal castling moves based on board state.
    Assumes king/rook have not moved if they are on their home squares.
    """
    moves = []
    row = 7 if color == "white" else 0
    opponent = "black" if color == "white" else "white"

    king = grid[row][4]
    if king is None or king.get_type() != "King" or king.get_color() != color:
        return moves
    if is_in_check(grid, color):
        return moves

    # Kingside: f1/f8 and g1/g8 must be empty and not attacked
    rook_ks = grid[row][7]
    if (rook_ks and rook_ks.get_type() == "Rook" and rook_ks.get_color() == color
            and grid[row][5] is None and grid[row][6] is None
            and not _is_square_attacked(grid, row, 5, opponent)
            and not _is_square_attacked(grid, row, 6, opponent)):
        test = [r[:] for r in grid]
        test[row][6] = test[row][4]
        test[row][4] = None
        if not is_in_check(test, color):
            moves.append(((row, 4), (row, 6)))

    # Queenside: b,c,d must be empty; c and d must not be attacked
    rook_qs = grid[row][0]
    if (rook_qs and rook_qs.get_type() == "Rook" and rook_qs.get_color() == color
            and grid[row][1] is None and grid[row][2] is None and grid[row][3] is None
            and not _is_square_attacked(grid, row, 3, opponent)
            and not _is_square_attacked(grid, row, 2, opponent)):
        test = [r[:] for r in grid]
        test[row][2] = test[row][4]
        test[row][4] = None
        if not is_in_check(test, color):
            moves.append(((row, 4), (row, 2)))

    return moves


def get_legal_moves(grid, color):
    """
    Return all (from_pos, to_pos) pairs for color that don't leave their king in check.
    Includes castling moves.
    """
    moves = []
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece is None or piece.get_color() != color:
                continue
            for to_pos in piece.get_possible_moves(grid, (r, c)) or []:
                tr, tc = to_pos
                # Simulate the move on a shallow copy
                test = [row[:] for row in grid]
                test[tr][tc] = test[r][c]
                test[r][c] = None
                if not is_in_check(test, color):
                    moves.append(((r, c), to_pos))

    moves.extend(_get_castling_moves(grid, color))
    return moves
