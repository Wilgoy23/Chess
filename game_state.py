"""Pure chess game state: grid, turn, rights, and result tracking.

No pygame import — this is the state class shared by the interactive game
(game.py) and, transitively through rules.py/fen.py, the headless tournament
runner (tournament.py doesn't use this class directly; it walks rules.py/
fen.py itself for speed, but relies on the same guarantee: nothing on this
path ever imports pygame). Rendering and click handling live in
ui/board_view.py; this class only tracks and mutates rules-level state.
"""

from dataclasses import dataclass

import rules
from fen import START_FEN, coords_to_square, parse_fen

_PROMO_LETTER = {"Queen": "Q", "Rook": "R", "Bishop": "B", "Knight": "N"}


@dataclass
class MoveResult:
    """Everything about a just-applied move that a caller might want to log
    or display, beyond what's queryable from GameState afterward."""
    mover: str
    piece_type: str
    from_pos: tuple
    to_pos: tuple
    is_castle: bool
    is_en_passant: bool
    is_promotion: bool
    promotion: str | None
    in_check: bool
    game_over: bool
    winner: str | None
    draw_reason: str | None

    def _tag(self) -> str:
        if self.is_castle:
            return "  (O-O)" if self.to_pos[1] == 6 else "  (O-O-O)"
        if self.is_en_passant:
            return "  (e.p.)"
        if self.is_promotion:
            return f"  (={_PROMO_LETTER.get(self.promotion or 'Queen', 'Q')})"
        return ""

    def move_log(self) -> str:
        """Console move log matching the original board.py wording."""
        line = (f"[{self.mover.capitalize():5}] {self.piece_type} "
                f"{coords_to_square(*self.from_pos)} → "
                f"{coords_to_square(*self.to_pos)}{self._tag()}")
        if self.game_over:
            if self.winner:
                line += f"\nCheckmate! {self.winner.capitalize()} wins."
            else:
                line += f"\nDraw ({(self.draw_reason or '').replace('_', ' ')})."
        elif self.in_check:
            opponent = "black" if self.mover == "white" else "white"
            line += f"\n  → {opponent.capitalize()} is in check!"
        return line


class GameState:
    """Mutable chess position plus the bookkeeping (halfmove clock, position
    counts, game-over/winner/draw_reason) needed to detect game end."""

    def __init__(self):
        pos = parse_fen(START_FEN)
        self.grid               = pos.grid
        self.turn                = pos.turn
        self.castling_rights    = pos.castling_rights
        self.en_passant_target  = pos.en_passant_target
        self.halfmove_clock     = 0
        self.position_counts: dict = {}
        self.last_move           = None
        self.in_check             = False
        self.game_over            = False
        self.winner               = None
        self.draw_reason          = None
        self._record_position()

    def legal_moves_from(self, pos: tuple) -> list:
        return rules.get_legal_moves_from(
            self.grid, pos, self.castling_rights, self.en_passant_target)

    def is_promotion_move(self, from_pos: tuple, to_pos: tuple) -> bool:
        return rules.is_promotion_move(self.grid, from_pos, to_pos)

    def _record_position(self) -> None:
        key = rules.position_key(
            self.grid, self.turn, self.castling_rights, self.en_passant_target)
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    def make_move(self, from_pos: tuple, to_pos: tuple, promotion: str | None = None) -> MoveResult:
        """Apply a move, update turn/check/game-over state, and return a
        MoveResult describing what happened."""
        fr, fc = from_pos
        tr, tc = to_pos
        piece = self.grid[fr][fc]
        mover = piece.get_color()
        piece_type = piece.get_type()

        is_castle = piece_type == "King" and abs(tc - fc) == 2
        is_en_passant = (
            piece_type == "Pawn"
            and to_pos == self.en_passant_target
            and tc != fc
            and self.grid[tr][tc] is None
        )
        is_promotion = self.is_promotion_move(from_pos, to_pos)

        self.grid, self.castling_rights, self.en_passant_target, is_irreversible = rules.apply_move(
            self.grid, from_pos, to_pos, self.castling_rights, self.en_passant_target,
            promotion=promotion)
        self.halfmove_clock = 0 if is_irreversible else self.halfmove_clock + 1

        self.last_move = (from_pos, to_pos)
        self.turn = "black" if self.turn == "white" else "white"

        self._record_position()
        self.in_check = rules.in_check(self.grid, self.turn)
        result = rules.get_game_result(
            self.grid, self.turn, self.castling_rights, self.en_passant_target,
            self.halfmove_clock, self.position_counts)

        self.game_over = False
        self.winner = None
        self.draw_reason = None
        if result == "checkmate":
            self.game_over = True
            self.winner = mover
        elif result is not None:
            self.game_over = True
            self.draw_reason = result

        return MoveResult(
            mover=mover, piece_type=piece_type, from_pos=from_pos, to_pos=to_pos,
            is_castle=is_castle, is_en_passant=is_en_passant,
            is_promotion=is_promotion, promotion=promotion,
            in_check=self.in_check, game_over=self.game_over,
            winner=self.winner, draw_reason=self.draw_reason,
        )

    def snapshot(self) -> dict:
        """A deep-enough copy to restore() later (used for undo)."""
        return {
            "grid":               [row[:] for row in self.grid],
            "turn":               self.turn,
            "castling_rights":    {c: dict(v) for c, v in self.castling_rights.items()},
            "en_passant_target":  self.en_passant_target,
            "halfmove_clock":     self.halfmove_clock,
            "position_counts":    dict(self.position_counts),
            "last_move":          self.last_move,
            "in_check":           self.in_check,
            "game_over":          self.game_over,
            "winner":             self.winner,
            "draw_reason":        self.draw_reason,
        }

    def restore(self, snap: dict) -> None:
        self.grid               = [row[:] for row in snap["grid"]]
        self.turn                = snap["turn"]
        self.castling_rights    = {c: dict(v) for c, v in snap["castling_rights"].items()}
        self.en_passant_target  = snap["en_passant_target"]
        self.halfmove_clock     = snap["halfmove_clock"]
        self.position_counts    = dict(snap["position_counts"])
        self.last_move           = snap["last_move"]
        self.in_check             = snap["in_check"]
        self.game_over            = snap["game_over"]
        self.winner               = snap["winner"]
        self.draw_reason          = snap["draw_reason"]
