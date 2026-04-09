import random
from Agents.AgentInterface import AgentInterface
from Agents.chess_utils import get_legal_moves


class RandomAgent(AgentInterface):

    def __init__(self, color):
        self.color = color

    def get_move(self, grid, color) -> tuple:
        moves = get_legal_moves(grid, color)
        return random.choice(moves) if moves else None