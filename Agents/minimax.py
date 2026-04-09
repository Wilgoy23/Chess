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

# Non-pawn, non-king material for both sides at game start:
# 2 * (2*3 + 2*3 + 2*5 + 9) = 62
PHASE_TOTAL_START = 62

# -----------------------------------------------------------------------------
# Piece-Square Tables (PSTs)
# Row 0 = black's back rank, Row 7 = white's back rank.
# White uses the table as-is. Black flips the row: PST[7 - row][col].
# Values are in fractional pawn units (e.g. 0.30 = 30% of a pawn).
# -----------------------------------------------------------------------------

PST_PAWN = [
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],  # row 0 — back rank, pawns never here
    [ 0.50,  0.50,  0.50,  0.50,  0.50,  0.50,  0.50,  0.50],  # row 1 — near promotion
    [ 0.10,  0.10,  0.20,  0.30,  0.30,  0.20,  0.10,  0.10],  # row 2
    [ 0.05,  0.05,  0.10,  0.25,  0.25,  0.10,  0.05,  0.05],  # row 3
    [ 0.00,  0.00,  0.00,  0.20,  0.20,  0.00,  0.00,  0.00],  # row 4 — center push rewarded
    [ 0.05, -0.05, -0.10,  0.00,  0.00, -0.10, -0.05,  0.05],  # row 5
    [ 0.05,  0.10,  0.10, -0.20, -0.20,  0.10,  0.10,  0.05],  # row 6 — white start row
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],  # row 7 — back rank, pawns never here
]

PST_KNIGHT = [
    [-0.50, -0.40, -0.30, -0.30, -0.30, -0.30, -0.40, -0.50],
    [-0.40, -0.20,  0.00,  0.00,  0.00,  0.00, -0.20, -0.40],
    [-0.30,  0.00,  0.10,  0.15,  0.15,  0.10,  0.00, -0.30],
    [-0.30,  0.05,  0.15,  0.20,  0.20,  0.15,  0.05, -0.30],
    [-0.30,  0.00,  0.15,  0.20,  0.20,  0.15,  0.00, -0.30],
    [-0.30,  0.05,  0.10,  0.15,  0.15,  0.10,  0.05, -0.30],
    [-0.40, -0.20,  0.00,  0.05,  0.05,  0.00, -0.20, -0.40],
    [-0.50, -0.40, -0.30, -0.30, -0.30, -0.30, -0.40, -0.50],
]

PST_BISHOP = [
    [-0.20, -0.10, -0.10, -0.10, -0.10, -0.10, -0.10, -0.20],
    [-0.10,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.10],
    [-0.10,  0.00,  0.05,  0.10,  0.10,  0.05,  0.00, -0.10],
    [-0.10,  0.05,  0.05,  0.10,  0.10,  0.05,  0.05, -0.10],
    [-0.10,  0.00,  0.10,  0.10,  0.10,  0.10,  0.00, -0.10],
    [-0.10,  0.10,  0.10,  0.10,  0.10,  0.10,  0.10, -0.10],
    [-0.10,  0.05,  0.00,  0.00,  0.00,  0.00,  0.05, -0.10],
    [-0.20, -0.10, -0.10, -0.10, -0.10, -0.10, -0.10, -0.20],
]

PST_ROOK = [
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],
    [ 0.05,  0.10,  0.10,  0.10,  0.10,  0.10,  0.10,  0.05],  # 7th rank bonus
    [-0.05,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.05],
    [-0.05,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.05],
    [-0.05,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.05],
    [-0.05,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.05],
    [-0.05,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.05],
    [ 0.00,  0.00,  0.00,  0.05,  0.05,  0.00,  0.00,  0.00],
]

PST_QUEEN = [
    [-0.20, -0.10, -0.10, -0.05, -0.05, -0.10, -0.10, -0.20],
    [-0.10,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, -0.10],
    [-0.10,  0.00,  0.05,  0.05,  0.05,  0.05,  0.00, -0.10],
    [-0.05,  0.00,  0.05,  0.05,  0.05,  0.05,  0.00, -0.05],
    [ 0.00,  0.00,  0.05,  0.05,  0.05,  0.05,  0.00, -0.05],
    [-0.10,  0.05,  0.05,  0.05,  0.05,  0.05,  0.00, -0.10],
    [-0.10,  0.00,  0.05,  0.00,  0.00,  0.00,  0.00, -0.10],
    [-0.20, -0.10, -0.10, -0.05, -0.05, -0.10, -0.10, -0.20],
]

# King prefers castled/edge squares in midgame, center in endgame
PST_KING_MIDGAME = [
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.20, -0.30, -0.30, -0.40, -0.40, -0.30, -0.30, -0.20],
    [-0.10, -0.20, -0.20, -0.20, -0.20, -0.20, -0.20, -0.10],
    [ 0.20,  0.20,  0.00,  0.00,  0.00,  0.00,  0.20,  0.20],
    [ 0.20,  0.30,  0.10,  0.00,  0.00,  0.10,  0.30,  0.20],  # g1/b1 castled positions
]

PST_KING_ENDGAME = [
    [-0.50, -0.40, -0.30, -0.20, -0.20, -0.30, -0.40, -0.50],
    [-0.30, -0.20, -0.10,  0.00,  0.00, -0.10, -0.20, -0.30],
    [-0.30, -0.10,  0.20,  0.30,  0.30,  0.20, -0.10, -0.30],
    [-0.30, -0.10,  0.30,  0.40,  0.40,  0.30, -0.10, -0.30],
    [-0.30, -0.10,  0.30,  0.40,  0.40,  0.30, -0.10, -0.30],
    [-0.30, -0.10,  0.20,  0.30,  0.30,  0.20, -0.10, -0.30],
    [-0.30, -0.30,  0.00,  0.00,  0.00,  0.00, -0.30, -0.30],
    [-0.50, -0.30, -0.30, -0.30, -0.30, -0.30, -0.30, -0.50],
]

PST_MAP = {
    "Pawn": PST_PAWN, "Knight": PST_KNIGHT,
    "Bishop": PST_BISHOP, "Rook": PST_ROOK, "Queen": PST_QUEEN,
}

# Evaluation factor weights
WEIGHT_MATERIAL    = 1.00
WEIGHT_PST         = 1.00
WEIGHT_MOBILITY    = 0.10
WEIGHT_KING_SAFETY = 0.15
WEIGHT_PAWN_STRUCT = 0.20
BISHOP_PAIR_BONUS  = 0.50


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
        material       = 0.0
        pst_score      = 0.0
        my_moves       = 0
        opp_moves      = 0
        phase_material = 0        # heavy piece material remaining (both sides)
        king_pos       = {}       # color -> (row, col)
        bishop_count   = {"white": 0, "black": 0}
        pawn_cols      = {"white": [], "black": []}

        # --- Single pass: material, PST, mobility, locate kings/pawns/bishops ---
        for row in range(8):
            for col in range(8):
                piece = grid[row][col]
                if piece is None:
                    continue
                ptype  = piece.get_type()
                pcolor = piece.get_color()
                sign   = 1 if pcolor == self.color else -1

                # Material
                piece_val = PIECE_VALUES.get(ptype, 0)
                material += sign * piece_val

                # Phase tracking — heavy pieces only
                if ptype not in ("Pawn", "King"):
                    phase_material += piece_val

                # PST — King deferred until phase is known
                if ptype == "King":
                    king_pos[pcolor] = (row, col)
                else:
                    pst_row = row if pcolor == "white" else (7 - row)
                    pst_score += sign * PST_MAP[ptype][pst_row][col]

                # Track bishops and pawn columns for structural evaluation
                if ptype == "Bishop":
                    bishop_count[pcolor] += 1
                if ptype == "Pawn":
                    pawn_cols[pcolor].append(col)

                # Mobility — one call per piece
                moves = piece.get_possible_moves(grid, (row, col)) or []
                if pcolor == self.color:
                    my_moves += len(moves)
                else:
                    opp_moves += len(moves)

        # --- Game phase: 1.0 = full opening material, 0.0 = bare kings ---
        phase_ratio = min(1.0, phase_material / PHASE_TOTAL_START)

        # --- King PST: switch table based on phase ---
        for pcolor, (krow, kcol) in king_pos.items():
            sign    = 1 if pcolor == self.color else -1
            pst_row = krow if pcolor == "white" else (7 - krow)
            king_table = PST_KING_MIDGAME if phase_ratio > 0.4 else PST_KING_ENDGAME
            pst_score += sign * king_table[pst_row][kcol]

        # --- King safety: count friendly pieces within 1 square of each king ---
        king_safety = 0.0
        for pcolor, (krow, kcol) in king_pos.items():
            sign  = 1 if pcolor == self.color else -1
            shield = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = krow + dr, kcol + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        neighbor = grid[nr][nc]
                        if neighbor is not None and neighbor.get_color() == pcolor:
                            shield += 1
            king_safety += sign * shield

        # --- Mobility score (normalized) ---
        total_moves    = my_moves + opp_moves
        mobility_score = (my_moves - opp_moves) / total_moves if total_moves > 0 else 0.0

        # --- Pawn structure: penalize isolated and doubled pawns ---
        pawn_struct = 0.0
        for pcolor in ("white", "black"):
            sign = 1 if pcolor == self.color else -1
            cols = pawn_cols[pcolor]
            col_counts = {}
            for c in cols:
                col_counts[c] = col_counts.get(c, 0) + 1

            for c, count in col_counts.items():
                # Doubled pawns (more than one pawn on the same file)
                if count > 1:
                    pawn_struct -= sign * 0.5 * (count - 1)
                # Isolated pawns (no friendly pawns on adjacent files)
                if (c - 1) not in col_counts and (c + 1) not in col_counts:
                    pawn_struct -= sign * 0.5

        # --- Bishop pair bonus ---
        bishop_pair = 0.0
        if bishop_count[self.color] == 2:
            bishop_pair += BISHOP_PAIR_BONUS
        if bishop_count[self._opponent] == 2:
            bishop_pair -= BISHOP_PAIR_BONUS

        return (
            material       * WEIGHT_MATERIAL
            + pst_score    * WEIGHT_PST
            + mobility_score * WEIGHT_MOBILITY    * (0.5 + 0.5 * phase_ratio)
            + king_safety  * WEIGHT_KING_SAFETY   * phase_ratio
            + pawn_struct  * WEIGHT_PAWN_STRUCT
            + bishop_pair
        )

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
