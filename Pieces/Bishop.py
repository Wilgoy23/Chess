from Pieces.PieceInterface import PieceInterface

class Bishop(PieceInterface):
    def __init__(self, color):
        self.color = color

    def move(self, board, start_pos, end_pos):
        # Implement the logic to move the bishop on the board
        pass

    def get_possible_moves(self, board, position):
        # Implement the logic to get possible moves for the bishop
        pass

    def get_color(self):
        return self.color

    def get_type(self):
        return "Bishop"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a bishop
        pass