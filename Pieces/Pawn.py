
from Pieces.PieceInterface import PieceInterface

class Pawn(PieceInterface):
    def __init__(self, color):
        self.color = color

    def move(self, board, start_pos, end_pos):
        # Implement the logic to move the pawn on the board
        pass

    def get_possible_moves(self, board, position):
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

        # Diagonal captures
        for dc in (-1, 1):
            nr, nc = row + direction, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target is not None and target.get_color() != self.color:
                    moves.append((nr, nc))

        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "Pawn"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a pawn
        pass