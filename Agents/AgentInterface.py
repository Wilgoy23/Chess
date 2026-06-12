from abc import ABC, abstractmethod


class AgentInterface(ABC):

    @abstractmethod
    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple:
        """
        Given the current board grid (8x8 list of piece objects or None), the
        color to move, the castling rights dict
        ({"white": {"kingside": bool, "queenside": bool}, "black": {...}}),
        and the current en passant target square ((row, col) or None),
        return ((from_row, from_col), (to_row, to_col)).
        """
        pass
