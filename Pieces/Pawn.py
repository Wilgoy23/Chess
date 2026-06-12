
from Pieces.PieceInterface import PieceInterface
from Pieces.Queen import Queen
from Pieces.Rook import Rook
from Pieces.Bishop import Bishop
from Pieces.Knight import Knight

_PROMOTION_CLASSES = {
    "Queen": Queen, "Rook": Rook, "Bishop": Bishop, "Knight": Knight,
}


class Pawn(PieceInterface):
    def __init__(self, color):
        self.color = color

    def get_possible_moves(self, board, position, en_passant_target=None):
        moves = []
        row, col = position
        direction = -1 if self.color == "white" else 1
        start_row = 6 if self.color == "white" else 1

        # One step forward
        nr = row + direction
        if 0 <= nr < 8 and board[nr][col] is None:
            moves.append((nr, col))
            # Two steps from starting row
            nr2 = row + 2 * direction
            if row == start_row and board[nr2][col] is None:
                moves.append((nr2, col))

        # Diagonal captures (including en passant)
        for dc in (-1, 1):
            nr, nc = row + direction, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target is not None and target.get_color() != self.color:
                    moves.append((nr, nc))
                elif target is None and en_passant_target == (nr, nc):
                    moves.append((nr, nc))

        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "Pawn"

    def move(self, grid: list, from_pos: tuple, to_pos: tuple,
             promotion: str = None, en_passant_target: tuple = None) -> list:
        fr, fc = from_pos
        tr, tc = to_pos
        mutations = []

        promo_row = 0 if self.color == "white" else 7
        if tr == promo_row:
            piece_cls = _PROMOTION_CLASSES.get(promotion, Queen)
            mutations.append((from_pos, to_pos, piece_cls(self.color)))
        else:
            mutations.append((from_pos, to_pos, self))

        # En passant: capture the pawn that just double-stepped, which sits
        # beside the origin square rather than on the destination square.
        if (to_pos == en_passant_target
                and tc != fc
                and grid[tr][tc] is None):
            captured_pos = (fr, tc)
            mutations.append((captured_pos, captured_pos, None))

        return mutations

    def is_valid_move(self, _board, _start_pos, _end_pos):
        pass
