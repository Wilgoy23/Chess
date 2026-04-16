import copy
import time
from Agents.AgentInterface import AgentInterface
from Agents.chess_utils import get_legal_moves, is_in_check
from Pieces.Queen import Queen


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

# Endgame mating bonuses (only applied when clearly winning in the endgame)
WEIGHT_ENDGAME_CORNER    = 1.00  # reward opponent king being far from center
WEIGHT_ENDGAME_PROXIMITY = 0.50  # reward our king being close to opponent king
REPETITION_PENALTY       = 0.30  # subtracted per time a position was already played


class MinimaxAgent(AgentInterface):

    def __init__(self, color, depth=5, time_limit=2.0):
        self.color = color
        self.depth = depth
        self.time_limit = time_limit  # seconds
        self._opponent = "black" if color == "white" else "white"
        self._deadline = None
        self._position_history = {}  # pos_hash -> times seen this game

    def get_move(self, grid, _color):
        self._deadline = time.time() + self.time_limit
        h = self._hash_grid(grid)
        self._position_history[h] = self._position_history.get(h, 0) + 1
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
            current_color = self.color if maximizing else self._opponent
            if is_in_check(grid, current_color):
                # Checkmate: use large finite values so faster mates are preferred
                return (-100_000 + depth if maximizing else 100_000 - depth), None
            else:
                return 0.0, None  # Stalemate

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

        # --- Endgame mating bonus: push opponent king to edge, bring ours close ---
        endgame_bonus = 0.0
        if phase_ratio < 0.5 and material > 0.5 and len(king_pos) == 2:
            my_k  = king_pos.get(self.color)
            opp_k = king_pos.get(self._opponent)
            if my_k and opp_k:
                opp_center_dist = abs(opp_k[0] - 3.5) + abs(opp_k[1] - 3.5)  # 1.0..7.0
                king_chebyshev  = max(abs(my_k[0] - opp_k[0]), abs(my_k[1] - opp_k[1]))
                endgame_bonus = (1.0 - phase_ratio) * (
                    WEIGHT_ENDGAME_CORNER    * opp_center_dist / 7.0
                    + WEIGHT_ENDGAME_PROXIMITY * (7 - king_chebyshev) / 7.0
                )

        # --- Repetition penalty: discourage returning to already-played positions ---
        repetition_penalty = 0.0
        h = self._hash_grid(grid)
        count = self._position_history.get(h, 0)
        if count > 0:
            repetition_penalty = REPETITION_PENALTY * count

        return (
            material       * WEIGHT_MATERIAL
            + pst_score    * WEIGHT_PST
            + mobility_score * WEIGHT_MOBILITY    * (0.5 + 0.5 * phase_ratio)
            + king_safety  * WEIGHT_KING_SAFETY   * phase_ratio
            + pawn_struct  * WEIGHT_PAWN_STRUCT
            + bishop_pair
            + endgame_bonus
            - repetition_penalty
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _hash_grid(grid):
        return tuple(
            (piece.get_color()[0] + piece.get_type()[0]) if piece else '.'
            for row in grid
            for piece in row
        )

    def _get_all_moves(self, grid, color):
        return get_legal_moves(grid, color)

    def _apply_move(self, grid, from_pos, to_pos):
        new_grid = copy.deepcopy(grid)
        fr, fc = from_pos
        tr, tc = to_pos
        piece = new_grid[fr][fc]
        new_grid[tr][tc] = piece
        new_grid[fr][fc] = None

        if piece is not None:
            # Castling: also relocate the rook
            if piece.get_type() == "King" and abs(tc - fc) == 2:
                if tc == 6:  # kingside
                    new_grid[tr][5] = new_grid[tr][7]
                    new_grid[tr][7] = None
                else:        # queenside
                    new_grid[tr][3] = new_grid[tr][0]
                    new_grid[tr][0] = None

            # Pawn promotion: always promote to queen
            if piece.get_type() == "Pawn":
                promo_row = 0 if piece.get_color() == "white" else 7
                if tr == promo_row:
                    new_grid[tr][tc] = Queen(piece.get_color())

        return new_grid
