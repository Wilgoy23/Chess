from Pieces.PieceInterface import PieceInterface

class Queen(PieceInterface):
    def __init__(self, color):
        self.color = color

    def get_possible_moves(self, board, position):
        moves = []
        row, col = position
        # Queen combines rook (straight) and bishop (diagonal) directions
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
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
        return "Queen"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a queen
        pass