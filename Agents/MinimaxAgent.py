import time
from Agents.AgentInterface import AgentInterface
import rules

PIECE_VALUES = {
    "Pawn": 1, "Knight": 3, "Bishop": 3,
    "Rook": 5, "Queen": 9, "King": 0,
}

# Non-pawn, non-king material total at game start (both sides): 2*(2*3+2*3+2*5+9) = 62
PHASE_TOTAL_START = 62

# ---------------------------------------------------------------------------
# Piece-Square Tables
# Row 0 = black's back rank, Row 7 = white's back rank.
# White reads the table as-is; black mirrors vertically (PST[7 - row][col]).
# ---------------------------------------------------------------------------
PST_PAWN = [
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],
    [ 0.50,  0.50,  0.50,  0.50,  0.50,  0.50,  0.50,  0.50],
    [ 0.10,  0.10,  0.20,  0.30,  0.30,  0.20,  0.10,  0.10],
    [ 0.05,  0.05,  0.10,  0.25,  0.25,  0.10,  0.05,  0.05],
    [ 0.00,  0.00,  0.00,  0.20,  0.20,  0.00,  0.00,  0.00],
    [ 0.05, -0.05, -0.10,  0.00,  0.00, -0.10, -0.05,  0.05],
    [ 0.05,  0.10,  0.10, -0.20, -0.20,  0.10,  0.10,  0.05],
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],
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
    [ 0.05,  0.10,  0.10,  0.10,  0.10,  0.10,  0.10,  0.05],
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

PST_KING_MID = [
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.30, -0.40, -0.40, -0.50, -0.50, -0.40, -0.40, -0.30],
    [-0.20, -0.30, -0.30, -0.40, -0.40, -0.30, -0.30, -0.20],
    [-0.10, -0.20, -0.20, -0.20, -0.20, -0.20, -0.20, -0.10],
    [ 0.10,  0.10, -0.10, -0.20, -0.20, -0.10,  0.10,  0.10],
    [ 0.20,  0.30,  0.10,  0.00,  0.00,  0.10,  0.30,  0.20],
]

PST_KING_END = [
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


# Single-letter piece codes for hashing ("N" disambiguates Knight from King)
_HASH_LETTER = {
    "Pawn": "P", "Knight": "N", "Bishop": "B",
    "Rook": "R", "Queen": "Q", "King": "K",
}


def _hash_own_pieces(grid, color) -> tuple:
    """Hash only `color`'s piece positions, ignoring the opponent.
    Repeated own-piece configurations across game turns indicate oscillation."""
    return tuple(
        _HASH_LETTER[piece.get_type()] if (piece and piece.get_color() == color) else '.'
        for row in grid
        for piece in row
    )


def _pst_value(ptype, color, row, col):
    """PST value for a piece of `color` standing on (row, col)."""
    table = PST_MAP.get(ptype) or PST_KING_MID
    pst_row = row if color == "white" else (7 - row)
    return table[pst_row][col]


def _order_moves(grid, moves):
    """Sort moves to improve alpha-beta cutoffs: winning captures first
    (MVV-LVA, offset above all quiet moves), then quiet moves by how much
    they improve the mover's piece-square value."""
    def score(mv):
        fr, fc = mv[0]
        tr, tc = mv[1]
        victim   = grid[tr][tc]
        attacker = grid[fr][fc]
        if victim is not None:
            return (100
                    + PIECE_VALUES.get(victim.get_type(), 0) * 10
                    - PIECE_VALUES.get(attacker.get_type(), 0))
        ptype  = attacker.get_type()
        pcolor = attacker.get_color()
        return _pst_value(ptype, pcolor, tr, tc) - _pst_value(ptype, pcolor, fr, fc)
    return sorted(moves, key=score, reverse=True)


class MinimaxAgent(AgentInterface):

    def __init__(self, color, depth=5, time_limit=2.0):
        self.color      = color
        self.max_depth  = depth
        self.time_limit = time_limit
        self._opponent  = "black" if color == "white" else "white"
        self._deadline  = 0.0
        # Own-piece configurations seen in actual game moves (not search nodes).
        # Keyed by _hash_own_pieces; value = times this arrangement was on the board.
        self._game_pos_count: dict[tuple, int] = {}

    # -------------------------------------------------------------------------
    # Public entry point
    # -------------------------------------------------------------------------

    def get_move(self, grid, _color, castling_rights, en_passant_target=None):
        self._deadline = time.time() + self.time_limit

        # Record the current own-piece arrangement as a real game position.
        h = _hash_own_pieces(grid, self.color)
        self._game_pos_count[h] = self._game_pos_count.get(h, 0) + 1

        best_move = None

        # Iterative deepening: keep only results from iterations that finished
        # before the deadline. A depth that times out mid-search produces scores
        # from inconsistent depths (subtrees collapse to static evals), so its
        # partial best move is garbage and must not overwrite the previous one.
        for depth in range(1, self.max_depth + 1):
            if self._timed_out():
                break
            _, move = self._minimax(grid, castling_rights, en_passant_target,
                                     depth, float("-inf"), float("inf"), True)
            if move is not None and (depth == 1 or not self._timed_out()):
                best_move = move

        return best_move

    # -------------------------------------------------------------------------
    # Alpha-beta minimax
    # -------------------------------------------------------------------------

    def _timed_out(self):
        return time.time() >= self._deadline

    def _minimax(self, grid, castling_rights, en_passant_target, depth, alpha, beta, maximizing):
        if depth == 0 or self._timed_out():
            return self._evaluate(grid, castling_rights), None

        color = self.color if maximizing else self._opponent
        moves = rules.get_legal_moves(grid, color, castling_rights, en_passant_target)

        if not moves:
            if rules.in_check(grid, color):
                # Bug fix: use +depth so shallower checkmates (fewer moves away)
                # score higher for the winning side, not lower.
                return ((-100_000 - depth) if maximizing else (100_000 + depth)), None
            return 0.0, None    # stalemate

        moves     = _order_moves(grid, moves)
        best_move = None

        if maximizing:
            best = float("-inf")
            for fm, tm in moves:
                if self._timed_out():
                    break
                new_grid, new_cr, new_ep, _ = rules.apply_move(
                    grid, fm, tm, castling_rights, en_passant_target)
                score, _ = self._minimax(new_grid, new_cr, new_ep,
                                          depth - 1, alpha, beta, False)
                if score > best:
                    best      = score
                    best_move = (fm, tm)
                alpha = max(alpha, score)
                if beta <= alpha:
                    break
            return best, best_move
        else:
            best = float("inf")
            for fm, tm in moves:
                if self._timed_out():
                    break
                new_grid, new_cr, new_ep, _ = rules.apply_move(
                    grid, fm, tm, castling_rights, en_passant_target)
                score, _ = self._minimax(new_grid, new_cr, new_ep,
                                          depth - 1, alpha, beta, True)
                if score < best:
                    best      = score
                    best_move = (fm, tm)
                beta = min(beta, score)
                if beta <= alpha:
                    break
            return best, best_move

    # -------------------------------------------------------------------------
    # Static evaluation — positive = good for self.color
    # -------------------------------------------------------------------------

    def _evaluate(self, grid, castling_rights):
        material       = 0.0
        pst_score      = 0.0
        my_moves       = 0
        opp_moves      = 0
        phase_material = 0
        king_pos       = {}
        bishop_count   = {"white": 0, "black": 0}
        pawn_cols      = {"white": [], "black": []}

        for row in range(8):
            for col in range(8):
                piece = grid[row][col]
                if piece is None:
                    continue
                ptype  = piece.get_type()
                pcolor = piece.get_color()
                sign   = 1 if pcolor == self.color else -1

                material  += sign * PIECE_VALUES.get(ptype, 0)

                if ptype not in ("Pawn", "King"):
                    phase_material += PIECE_VALUES.get(ptype, 0)

                if ptype == "King":
                    king_pos[pcolor] = (row, col)
                else:
                    pst_row    = row if pcolor == "white" else (7 - row)
                    pst_score += sign * PST_MAP[ptype][pst_row][col]

                if ptype == "Bishop":
                    bishop_count[pcolor] += 1
                if ptype == "Pawn":
                    pawn_cols[pcolor].append(col)

                # King mobility is not an asset in the midgame — counting it
                # rewards king wandering, so the king is excluded here.
                if ptype != "King":
                    raw = piece.get_possible_moves(grid, (row, col)) or []
                    if pcolor == self.color:
                        my_moves  += len(raw)
                    else:
                        opp_moves += len(raw)

        # Game phase: 1.0 = opening material, 0.0 = bare endgame
        phase_ratio = min(1.0, phase_material / PHASE_TOTAL_START)

        # King PST interpolated by phase
        for pcolor, (kr, kc) in king_pos.items():
            sign     = 1 if pcolor == self.color else -1
            pst_row  = kr if pcolor == "white" else (7 - kr)
            k_table  = PST_KING_MID if phase_ratio > 0.4 else PST_KING_END
            pst_score += sign * k_table[pst_row][kc]

        # Mobility
        total_moves    = my_moves + opp_moves
        mobility_score = (my_moves - opp_moves) / total_moves if total_moves > 0 else 0.0

        # King safety: count friendly pieces in the 3×3 neighbourhood
        king_safety = 0.0
        for pcolor, (kr, kc) in king_pos.items():
            sign   = 1 if pcolor == self.color else -1
            shield = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = kr + dr, kc + dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        nb = grid[nr][nc]
                        if nb is not None and nb.get_color() == pcolor:
                            shield += 1
            king_safety += sign * shield

        # Pawn structure: penalise doubled and isolated pawns
        pawn_struct = 0.0
        for pcolor in ("white", "black"):
            sign      = 1 if pcolor == self.color else -1
            col_count = {}
            for c in pawn_cols[pcolor]:
                col_count[c] = col_count.get(c, 0) + 1
            for c, cnt in col_count.items():
                if cnt > 1:
                    pawn_struct -= sign * 0.5 * (cnt - 1)
                if (c - 1) not in col_count and (c + 1) not in col_count:
                    pawn_struct -= sign * 0.5

        # Bishop pair bonus
        bishop_pair = 0.0
        if bishop_count[self.color]    == 2: bishop_pair += 0.50
        if bishop_count[self._opponent] == 2: bishop_pair -= 0.50

        # Castling: reward keeping castling rights, and reward having castled
        # (king on g/c-file of its back rank with the rook beside it on f/d).
        # Without these terms a king shuffle like Ke1-e2 costs nothing even
        # though it forfeits castling forever.
        castling_score = 0.0
        for pcolor in ("white", "black"):
            sign      = 1 if pcolor == self.color else -1
            rights    = castling_rights[pcolor]
            back_rank = 7 if pcolor == "white" else 0
            castling_score += sign * 0.15 * phase_ratio * (
                rights["kingside"] + rights["queenside"])

            kpos = king_pos.get(pcolor)
            if kpos and kpos[0] == back_rank and kpos[1] in (6, 2):
                rook_col = 5 if kpos[1] == 6 else 3
                rook = grid[back_rank][rook_col]
                if rook and rook.get_type() == "Rook" and rook.get_color() == pcolor:
                    castling_score += sign * 0.40 * phase_ratio

        # Endgame mating bonus: drive opponent king to a corner
        endgame_bonus = 0.0
        if phase_ratio < 0.5 and material > 0.5 and len(king_pos) == 2:
            mk  = king_pos.get(self.color)
            ok  = king_pos.get(self._opponent)
            if mk and ok:
                opp_center_dist = abs(ok[0] - 3.5) + abs(ok[1] - 3.5)
                king_dist       = max(abs(mk[0] - ok[0]), abs(mk[1] - ok[1]))
                endgame_bonus   = (1.0 - phase_ratio) * (
                    1.0 * opp_center_dist / 7.0
                    + 0.5 * (7 - king_dist) / 7.0
                )

        # Repetition penalty: each time the agent's own pieces have been in this
        # exact arrangement in a real game move, subtract 0.5 pawns.
        # Uses own-piece-only hash so the penalty fires even when the opponent's
        # pieces have moved between repetitions (the common oscillation pattern).
        own_count = self._game_pos_count.get(_hash_own_pieces(grid, self.color), 0)
        repetition_penalty = 0.5 * own_count

        return (
            material       * 1.00
            + pst_score    * 1.00
            + mobility_score * 0.10 * (0.5 + 0.5 * phase_ratio)
            + king_safety  * 0.15  * phase_ratio
            + pawn_struct  * 0.20
            + bishop_pair
            + castling_score
            + endgame_bonus
            - repetition_penalty
        )
