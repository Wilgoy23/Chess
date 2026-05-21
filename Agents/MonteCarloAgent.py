import math
import random
import time

from Agents.AgentInterface import AgentInterface
from Agents.chess_utils import get_legal_moves
from Pieces.Queen import Queen

PIECE_VALUES = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Rook": 5, "Queen": 9, "King": 0}


def _opponent(color):
    return "black" if color == "white" else "white"


def _apply_move(grid, from_pos, to_pos):
    """Shallow-copy the grid and apply one move, including castling and promotion."""
    new_grid = [row[:] for row in grid]   # safe: piece objects are immutable
    fr, fc = from_pos
    tr, tc = to_pos
    piece = new_grid[fr][fc]
    new_grid[tr][tc] = piece
    new_grid[fr][fc] = None

    if piece is not None:
        # Castling: relocate the rook that pairs with the king's 2-square jump
        if piece.get_type() == "King" and abs(tc - fc) == 2:
            if tc == 6:                       # kingside
                new_grid[tr][5] = new_grid[tr][7]
                new_grid[tr][7] = None
            else:                             # queenside
                new_grid[tr][3] = new_grid[tr][0]
                new_grid[tr][0] = None
        # Pawn promotion → always queen (standard MCTS simplification)
        if piece.get_type() == "Pawn":
            promo_row = 0 if piece.get_color() == "white" else 7
            if tr == promo_row:
                new_grid[tr][tc] = Queen(piece.get_color())

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


def _pseudo_legal_moves(grid, color):
    """Return all moves for `color` without filtering for leaving the king in check.
    Used only in rollouts where speed matters more than perfect legality."""
    moves = []
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece and piece.get_color() == color:
                for to_pos in (piece.get_possible_moves(grid, (r, c)) or []):
                    moves.append(((r, c), to_pos))
    return moves


def _king_alive(grid, color):
    for row in grid:
        for piece in row:
            if piece and piece.get_type() == "King" and piece.get_color() == color:
                return True
    return False


# ---------------------------------------------------------------------------

class MCTSNode:
    __slots__ = ["grid", "color", "move", "parent", "children",
                 "wins", "visits", "_untried_moves"]

    def __init__(self, grid, color, move=None, parent=None):
        self.grid   = grid
        self.color  = color    # player whose turn it is to move FROM this state
        self.move   = move     # (from_pos, to_pos) that led to this state
        self.parent = parent
        self.children       = []
        self.wins           = 0.0   # wins for the player who moved INTO this node
        self.visits         = 0
        self._untried_moves = None  # lazily initialised

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
            key=lambda ch: (ch.wins / ch.visits) + c * math.sqrt(log_n / ch.visits),
        )


class MonteCarloAgent(AgentInterface):

    def __init__(self, color, time_limit=2.0, max_simulations=1000,
                 max_rollout_depth=20, exploration_constant=1.414):
        self.color              = color
        self.time_limit         = time_limit
        self.max_simulations    = max_simulations
        self.max_rollout_depth  = max_rollout_depth   # reduced from 50; rollouts are fast now
        self.C                  = exploration_constant
        self._start_time        = None

    def get_move(self, grid, color) -> tuple:
        self._start_time = time.time()
        root = MCTSNode(grid, color=color)

        if not root.untried_moves():
            return None

        for _ in range(self.max_simulations):
            if self._timed_out():
                break
            node   = self._select(root)
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

    # -------------------------------------------------------------------------
    # MCTS phases
    # -------------------------------------------------------------------------

    def _select(self, node):
        while node.is_fully_expanded() and not node.is_terminal():
            node = node.best_child_uct(self.C)
        return node

    def _expand(self, node):
        moves = node.untried_moves()
        move  = moves.pop(random.randrange(len(moves)))
        child = MCTSNode(
            _apply_move(node.grid, *move),
            color=_opponent(node.color),
            move=move,
            parent=node,
        )
        node.children.append(child)
        return child

    def _rollout(self, node):
        """Fast rollout using pseudo-legal moves.
        King capture acts as checkmate signal, avoiding the expensive is_in_check scan."""
        grid  = node.grid
        color = node.color
        position_counts = {}

        for _ in range(self.max_rollout_depth):
            moves = _pseudo_legal_moves(grid, color)
            if not moves:
                return None     # no pieces left ≈ draw

            h = _hash_grid(grid)
            position_counts[h] = position_counts.get(h, 0) + 1
            if position_counts[h] >= 3:
                return None     # 3-fold repetition → draw

            grid  = _apply_move(grid, *random.choice(moves))

            # If the king was just captured the moving side wins outright
            opp = _opponent(color)
            if not _king_alive(grid, opp):
                return color

            color = opp

        return _material_winner(grid)

    def _backpropagate(self, node, winner):
        current = node
        while current is not None:
            current.visits += 1
            if winner is None:
                current.wins += 0.5
            elif winner != current.color:
                # current.color is the player to move FROM this node;
                # current.wins counts wins for the player who moved INTO it.
                current.wins += 1.0
            current = current.parent
