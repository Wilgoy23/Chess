import copy
import time
from Agents.AgentInterface import AgentInterface


# Material value of each piece type
PIECE_VALUES = {
    "Pawn": 1,
    "Knight": 3,
    "Bishop": 3,
    "Rook": 5,
    "Queen": 9,
    "King": 0,  # never captured, not counted
}


class MinimaxAgent(AgentInterface):

    def __init__(self, color, depth=3, time_limit=5.0):
        self.color = color
        self.depth = depth
        self.time_limit = time_limit  # seconds
        self._opponent = "black" if color == "white" else "white"
        self._deadline = None

    def get_move(self, grid, _color):
        self._deadline = time.time() + self.time_limit
        _, move = self._minimax(grid, self.depth, float("-inf"), float("inf"), True)
        return move

    # -------------------------------------------------------------------------
    # Minimax with alpha-beta pruning
    # -------------------------------------------------------------------------

    def _timed_out(self):
        return time.time() >= self._deadline

    def _minimax(self, grid, depth, alpha, beta, maximizing):
        if depth == 0 or self._timed_out():
            return self._evaluate(grid), None

        all_moves = self._get_all_moves(grid, self.color if maximizing else self._opponent)
        if not all_moves:
            return self._evaluate(grid), None

        best_move = None

        if maximizing:
            best_score = float("-inf")
            for from_pos, to_pos in all_moves:
                if self._timed_out():
                    break
                new_grid = self._apply_move(grid, from_pos, to_pos)
                score, _ = self._minimax(new_grid, depth - 1, alpha, beta, False)
                if score > best_score:
                    best_score = score
                    best_move = (from_pos, to_pos)
                alpha = max(alpha, score)
                if beta <= alpha:
                    break
            return best_score, best_move
        else:
            best_score = float("inf")
            for from_pos, to_pos in all_moves:
                if self._timed_out():
                    break
                new_grid = self._apply_move(grid, from_pos, to_pos)
                score, _ = self._minimax(new_grid, depth - 1, alpha, beta, True)
                if score < best_score:
                    best_score = score
                    best_move = (from_pos, to_pos)
                beta = min(beta, score)
                if beta <= alpha:
                    break
            return best_score, best_move

    # -------------------------------------------------------------------------
    # Board evaluation — positive = good for this agent's color
    # -------------------------------------------------------------------------

    def _evaluate(self, grid):
        score = 0
        for row in grid:
            for piece in row:
                if piece is None:
                    continue
                value = PIECE_VALUES.get(piece.get_type(), 0)
                score += value if piece.get_color() == self.color else -value
        return score

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_all_moves(self, grid, color):
        moves = []
        for row in range(8):
            for col in range(8):
                piece = grid[row][col]
                if piece and piece.get_color() == color:
                    for to_pos in piece.get_possible_moves(grid, (row, col)) or []:
                        moves.append(((row, col), to_pos))
        return moves

    def _apply_move(self, grid, from_pos, to_pos):
        new_grid = copy.deepcopy(grid)
        fr, fc = from_pos
        tr, tc = to_pos
        new_grid[tr][tc] = new_grid[fr][fc]
        new_grid[fr][fc] = None
        return new_grid
