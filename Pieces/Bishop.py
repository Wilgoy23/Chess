from Pieces.PieceInterface import PieceInterface

class Bishop(PieceInterface):
    def __init__(self, color):
        self.color = color

    def move(self, board, start_pos, end_pos):
        # Implement the logic to move the bishop on the board
        pass

    def get_possible_moves(self, board, position):
        moves = []
        row, col = position
        # Bishops slide diagonally in all 4 directions
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = row + dr, col + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target is None:
                    moves.append((nr, nc))
                elif target.get_color() != self.color:
                    moves.append((nr, nc))  # capture, then stop
                    break
                else:
                    break  # blocked by own piece
                nr += dr
                nc += dc
        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "Bishop"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a bishop
        pass