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


def get_legal_moves(grid, color):
    """
    Return all (from_pos, to_pos) pairs for color that don't leave their king in check.
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
    return moves
