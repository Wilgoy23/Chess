import random
from Agents.AgentInterface import AgentInterface
import rules


class RandomAgent(AgentInterface):

    def __init__(self, color):
        self.color = color

    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple:
        moves = rules.get_legal_moves(grid, color, castling_rights, en_passant_target)
        return random.choice(moves) if moves else None
