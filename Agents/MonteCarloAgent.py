import copy
import math
import random
import time

from Agents.AgentInterface import AgentInterface
from Agents.chess_utils import get_legal_moves, is_in_check

PIECE_VALUES = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Rook": 5, "Queen": 9, "King": 0}


def _opponent(color):
    return "black" if color == "white" else "white"


def _apply_move(grid, from_pos, to_pos):
    new_grid = copy.deepcopy(grid)
    fr, fc = from_pos
    tr, tc = to_pos
    new_grid[tr][tc] = new_grid[fr][fc]
    new_grid[fr][fc] = None
    return new_grid


def _hash_grid(grid):
    return tuple(
        (piece.get_color()[0] + piece.get_type()[0]) if piece else '.'
        for row in grid
        for piece in row
    )


def _material_winner(grid):
    white, black = 0, 0
    for row in grid:
        for piece in row:
            if piece:
                val = PIECE_VALUES.get(piece.get_type(), 0)
                if piece.get_color() == "white":
                    white += val
                else:
                    black += val
    if white > black:
        return "white"
    if black > white:
        return "black"
    return None


class MCTSNode:
    __slots__ = ["grid", "color", "move", "parent", "children",
                 "wins", "visits", "_untried_moves"]

    def __init__(self, grid, color, move=None, parent=None):
        self.grid = grid
        self.color = color          # player whose turn it is to move FROM this state
        self.move = move            # (from_pos, to_pos) that led to this state
        self.parent = parent
        self.children = []
        self.wins = 0.0             # wins for the player who moved INTO this node
        self.visits = 0
        self._untried_moves = None  # lazily initialized

    def untried_moves(self):
        if self._untried_moves is None:
            self._untried_moves = get_legal_moves(self.grid, self.color)
        return self._untried_moves

    def is_fully_expanded(self):
        return len(self.untried_moves()) == 0

    def is_terminal(self):
        return self.is_fully_expanded() and len(self.children) == 0

    def best_child_uct(self, c):
        log_n = math.log(self.visits)
        return max(
            self.children,
            key=lambda ch: (ch.wins / ch.visits) + c * math.sqrt(log_n / ch.visits)
        )


class MonteCarloAgent(AgentInterface):

    def __init__(self, color, time_limit=5.0, max_simulations=800,
                 max_rollout_depth=50, exploration_constant=1.414):
        self.color = color
        self.time_limit = time_limit
        self.max_simulations = max_simulations
        self.max_rollout_depth = max_rollout_depth
        self.C = exploration_constant
        self._start_time = None

    def get_move(self, grid, color) -> tuple:
        self._start_time = time.time()
        root = MCTSNode(grid, color=color)

        if not root.untried_moves():
            return None

        for _ in range(self.max_simulations):
            if self._timed_out():
                break
            node = self._select(root)
            if not node.is_terminal():
                node = self._expand(node)
            winner = self._rollout(node)
            self._backpropagate(node, winner)

        if not root.children:
            moves = root.untried_moves()
            return random.choice(moves) if moves else None

        return max(root.children, key=lambda ch: ch.visits).move

    def _timed_out(self):
        return time.time() - self._start_time >= self.time_limit

    def _select(self, node):
        while node.is_fully_expanded() and not node.is_terminal():
            node = node.best_child_uct(self.C)
        return node

    def _expand(self, node):
        moves = node.untried_moves()
        move = moves.pop(random.randrange(len(moves)))
        new_grid = _apply_move(node.grid, *move)
        next_color = _opponent(node.color)
        child = MCTSNode(new_grid, next_color, move=move, parent=node)
        node.children.append(child)
        return child

    def _rollout(self, node):
        grid = node.grid
        color = node.color
        position_counts = {}
        for _ in range(self.max_rollout_depth):
            moves = get_legal_moves(grid, color)
            if not moves:
                if is_in_check(grid, color):
                    return _opponent(color)  # checkmate
                return None                  # stalemate
            h = _hash_grid(grid)
            position_counts[h] = position_counts.get(h, 0) + 1
            if position_counts[h] >= 3:
                return None                  # 3-fold repetition → draw
            grid = _apply_move(grid, *random.choice(moves))
            color = _opponent(color)
        return _material_winner(grid)

    def _backpropagate(self, node, winner):
        current = node
        while current is not None:
            current.visits += 1
            if winner is None:
                current.wins += 0.5
            elif winner != current.color:
                current.wins += 1.0
            current = current.parent
