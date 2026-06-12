import math
import random
import time

from Agents.AgentInterface import AgentInterface
import rules

PIECE_VALUES = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Rook": 5, "Queen": 9, "King": 0}


def _opponent(color):
    return "black" if color == "white" else "white"


def _hash_grid(grid):
    return tuple(
        (piece.get_color()[0] + piece.get_type()[0]) if piece else '.'
        for row in grid
        for piece in row
    )


def _material_score(grid):
    """Estimated P(white wins) from the material balance at rollout cutoff.
    Smooth gradient so every point of material shifts the score — a hard
    win/loss threshold made small captures invisible to the search."""
    diff = 0
    for row in grid:
        for piece in row:
            if piece:
                val = PIECE_VALUES.get(piece.get_type(), 0)
                diff += val if piece.get_color() == "white" else -val
    return 1.0 / (1.0 + 10.0 ** (-diff / 10.0))


def _pseudo_legal_moves(grid, color, en_passant_target=None):
    """Return all moves for `color` without filtering for leaving the king in check.
    Used only in rollouts where speed matters more than perfect legality."""
    moves = []
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece and piece.get_color() == color:
                for to_pos in (piece.get_possible_moves(grid, (r, c), en_passant_target) or []):
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
    __slots__ = ["grid", "color", "castling_rights", "en_passant_target",
                 "move", "parent", "children",
                 "wins", "visits", "_untried_moves"]

    def __init__(self, grid, color, castling_rights, en_passant_target=None,
                 move=None, parent=None):
        self.grid              = grid
        self.color             = color    # player whose turn it is to move FROM this state
        self.castling_rights   = castling_rights
        self.en_passant_target = en_passant_target
        self.move   = move     # (from_pos, to_pos) that led to this state
        self.parent = parent
        self.children       = []
        self.wins           = 0.0   # wins for the player who moved INTO this node
        self.visits         = 0
        self._untried_moves = None  # lazily initialised

    def untried_moves(self):
        if self._untried_moves is None:
            self._untried_moves = rules.get_legal_moves(
                self.grid, self.color, self.castling_rights, self.en_passant_target)
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

    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple:
        self._start_time = time.time()
        root = MCTSNode(grid, color=color, castling_rights=castling_rights,
                        en_passant_target=en_passant_target)

        if not root.untried_moves():
            return None

        for _ in range(self.max_simulations):
            if self._timed_out():
                break
            node = self._select(root)
            if not node.is_terminal():
                node = self._expand(node)
            if node.is_terminal():
                # No legal moves: checkmate (the player who moved in wins)
                # or stalemate (draw). Score exactly instead of rolling out —
                # pseudo-legal rollouts would play on from a mated position.
                if rules.in_check(node.grid, node.color):
                    score = 1.0 if _opponent(node.color) == "white" else 0.0
                else:
                    score = 0.5
            else:
                score = self._rollout(node)
            self._backpropagate(node, score)

        if not root.children:
            moves = root.untried_moves()
            return random.choice(moves) if moves else None

        return max(root.children,
                   key=lambda ch: (ch.visits, ch.wins / ch.visits)).move

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
        new_grid, new_cr, new_ep, _ = rules.apply_move(
            node.grid, *move, node.castling_rights, node.en_passant_target)
        child = MCTSNode(
            new_grid,
            color=_opponent(node.color),
            castling_rights=new_cr,
            en_passant_target=new_ep,
            move=move,
            parent=node,
        )
        node.children.append(child)
        return child

    def _rollout(self, node):
        """Capture-biased rollout using pseudo-legal moves.
        Returns an estimated P(white wins) in [0, 1].

        King capture acts as checkmate signal, avoiding the expensive
        is_in_check scan. Captures are preferred over uniformly random moves —
        strongly on the first ply (so a piece hung by the expanded move is
        punished immediately) and moderately afterwards. Pure-random play makes
        every position look ~50/50, which drowns the signal MCTS needs."""
        grid              = node.grid
        color             = node.color
        castling_rights   = node.castling_rights
        en_passant_target = node.en_passant_target
        position_counts   = {}

        for ply in range(self.max_rollout_depth):
            moves = _pseudo_legal_moves(grid, color, en_passant_target)
            if not moves:
                return 0.5      # no pieces left ≈ draw

            h = _hash_grid(grid)
            position_counts[h] = position_counts.get(h, 0) + 1
            if position_counts[h] >= 3:
                return 0.5      # 3-fold repetition → draw

            move = None
            capture_bias = 0.8 if ply == 0 else 0.5
            if random.random() < capture_bias:
                best_victim = 0
                for fm, tm in moves:
                    victim = grid[tm[0]][tm[1]]
                    if victim is not None:
                        val = PIECE_VALUES.get(victim.get_type(), 0)
                        if victim.get_type() == "King":
                            val = 100   # always take a hanging king
                        if val > best_victim:
                            best_victim = val
                            move = (fm, tm)
            if move is None:
                move = random.choice(moves)

            grid, castling_rights, en_passant_target, _ = rules.apply_move(
                grid, *move, castling_rights, en_passant_target)

            # If the king was just captured the moving side wins outright
            opp = _opponent(color)
            if not _king_alive(grid, opp):
                return 1.0 if color == "white" else 0.0

            color = opp

        return _material_score(grid)

    def _backpropagate(self, node, score_white):
        """Propagate a rollout score (P(white wins), in [0, 1]) up the tree.
        current.color is the player to move FROM a node; current.wins counts
        wins for the player who moved INTO it (the opponent of current.color)."""
        current = node
        while current is not None:
            current.visits += 1
            if current.color == "black":    # white moved into this node
                current.wins += score_white
            else:                           # black moved into this node
                current.wins += 1.0 - score_white
            current = current.parent
