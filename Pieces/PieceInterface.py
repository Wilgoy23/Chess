from abc import ABC, abstractmethod

class PieceInterface(ABC):
    @abstractmethod
    def move(self, board, start_pos, end_pos):
        pass

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