import threading
from abc import ABC, abstractmethod


class AgentInterface(ABC):

    def __init__(self) -> None:
        self.stop_event = threading.Event()

    @abstractmethod
    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple:
        """
        Given the current board grid (8x8 list of piece objects or None), the
        color to move, the castling rights dict
        ({"white": {"kingside": bool, "queenside": bool}, "black": {...}}),
        and the current en passant target square ((row, col) or None),
        return ((from_row, from_col), (to_row, to_col)).

        Implementations that run an iterative search should poll
        self.stop_event and return their best move so far once it is set.
        """
        pass

    def stop(self) -> None:
        """Ask an in-progress get_move() call to return as soon as it can.

        Cooperative: subclasses must poll self.stop_event themselves (or, like
        StockfishAgent, override this to signal an external process). Callers
        reusing an agent instance across multiple searches must clear
        stop_event before starting the next one.
        """
        self.stop_event.set()
