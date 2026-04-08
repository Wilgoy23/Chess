from Pieces.PieceInterface import PieceInterface

class King(PieceInterface):
    def __init__(self, color):
        self.color = color

    def move(self, board, start_pos, end_pos):
        # Implement the logic to move the king on the board
        pass

    def get_possible_moves(self, board, position):
        moves = []
        row, col = position
        # King moves one square in any direction
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target is None or target.get_color() != self.color:
                        moves.append((nr, nc))
        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "King"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a king
        pass