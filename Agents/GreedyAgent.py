"""One-ply material-capture maximizer, with random tie-break.

Sits between RandomAgent and MinimaxAgent on the strength ladder: it always
takes the best available capture (including en passant, which leaves no
piece on the destination square) but has no search depth or positional
understanding beyond that.
"""

import random

from Agents.AgentInterface import AgentInterface
import rules

_PIECE_VALUES = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Rook": 5, "Queen": 9, "King": 0}


class GreedyAgent(AgentInterface):

    def __init__(self, color):
        super().__init__()
        self.color = color

    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple:
        moves = rules.get_legal_moves(grid, color, castling_rights, en_passant_target)
        if not moves:
            return None

        best_value = 0
        best_moves = []
        for from_pos, to_pos in moves:
            best_value, best_moves = self._consider(
                grid, from_pos, to_pos, en_passant_target, best_value, best_moves)

        return random.choice(best_moves) if best_value > 0 else random.choice(moves)

    def _consider(self, grid, from_pos, to_pos, en_passant_target, best_value, best_moves):
        victim = grid[to_pos[0]][to_pos[1]]
        if victim is not None:
            value = _PIECE_VALUES.get(victim.get_type(), 0)
        else:
            mover = grid[from_pos[0]][from_pos[1]]
            is_en_passant = (mover.get_type() == "Pawn"
                              and to_pos == en_passant_target
                              and to_pos[1] != from_pos[1])
            value = _PIECE_VALUES["Pawn"] if is_en_passant else 0

        if value > best_value:
            return value, [(from_pos, to_pos)]
        if value == best_value:
            best_moves.append((from_pos, to_pos))
        return best_value, best_moves
