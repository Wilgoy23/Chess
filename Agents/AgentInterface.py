from abc import ABC, abstractmethod


class AgentInterface(ABC):

    @abstractmethod
    def get_move(self, grid, color) -> tuple:
        """
        Given the current board grid (8x8 list of piece objects or None)
        and the color to move, return ((from_row, from_col), (to_row, to_col)).
        """
        pass