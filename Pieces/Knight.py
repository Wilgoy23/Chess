from Pieces.PieceInterface import PieceInterface

class Knight(PieceInterface):
    def __init__(self, color):
        self.color = color


    def get_possible_moves(self, board, position):
        moves = []
        row, col = position
        # All 8 L-shaped jumps
        for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target is None or target.get_color() != self.color:
                    moves.append((nr, nc))
        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "Knight"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a knight
        pass