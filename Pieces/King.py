from Pieces.PieceInterface import PieceInterface

class King(PieceInterface):
    def __init__(self, color):
        self.color = color

    def move(self, board, start_pos, end_pos):
        # Implement the logic to move the king on the board
        pass

    def get_possible_moves(self, board, position):
        # Implement the logic to get possible moves for the king
        pass

    def get_color(self):
        return self.color

    def get_type(self):
        return "King"

    def is_valid_move(self, board, start_pos, end_pos):
        # Implement the logic to check if the move is valid for a king
        pass