from abc import ABC, abstractmethod


class PieceInterface(ABC):

    @abstractmethod
    def get_possible_moves(self, board, position):
        pass

    @abstractmethod
    def get_color(self):
        pass

    @abstractmethod
    def get_type(self):
        pass

    @abstractmethod
    def is_valid_move(self, board, start_pos, end_pos):
        pass

    def move(self, _grid: list, from_pos: tuple, to_pos: tuple) -> list:
        """
        Returns a list of (origin, destination, piece_object) mutations.
        Board applies each as: grid[dest] = piece_obj; grid[origin] = None.
        Override for special rules (Pawn promotion, King castling).
        """
        return [(from_pos, to_pos, self)]