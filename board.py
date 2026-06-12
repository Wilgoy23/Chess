import pygame
import os

from Pieces.Pawn import Pawn
from Pieces.Rook import Rook
from Pieces.Knight import Knight
from Pieces.Bishop import Bishop
from Pieces.Queen import Queen
from Pieces.King import King
import rules


class Board:
    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    HIGHLIGHT_COLOR = (186, 202, 68)
    VALID_MOVE_COLOR = (100, 111, 64)
    LAST_MOVE_COLOR = (205, 210, 106)
    CHECK_COLOR = (220, 20, 20)
    PROMO_BG_COLOR = (240, 240, 240)
    PROMO_BORDER_COLOR = (80, 80, 80)

    _COL_NAMES = "abcdefgh"
    _ROW_NAMES = "87654321"  # row 0 = rank 8

    # Algebraic piece letters used in the console log for promotions
    _PROMO_LETTER = {"Queen": "Q", "Rook": "R", "Bishop": "B", "Knight": "N"}

    UNICODE = {
        "white": {
            "Pawn": "♙", "Rook": "♖", "Knight": "♘",
            "Bishop": "♗", "Queen": "♕", "King": "♔",
        },
        "black": {
            "Pawn": "♟", "Rook": "♜", "Knight": "♞",
            "Bishop": "♝", "Queen": "♛", "King": "♚",
        },
    }

    def __init__(self, square_size=100):
        self.square_size = square_size
        self.grid = self._create_board()
        self.turn = "white"
        self.selected = None    # (row, col) of selected square
        self.valid_moves = []   # list of (row, col) the selected piece can move to
        self.castling_rights = {
            "white": {"kingside": True, "queenside": True},
            "black": {"kingside": True, "queenside": True},
        }
        self.en_passant_target = None   # (row, col) capturable en passant, or None
        self.halfmove_clock = 0          # half-moves since the last pawn move/capture
        self.position_counts = {}        # position signature -> times seen
        self.last_move = None   # (from_pos, to_pos) of the most recent move
        self.in_check = False   # True when the side to move is in check
        self.game_over = False
        self.winner = None      # "white", "black", or None (draw)
        self.draw_reason = None # None, or "stalemate"/"fifty_move_rule"/"threefold_repetition"/"insufficient_material"
        self.promotion_pending = None  # (from_pos, to_pos) awaiting a human promotion choice
        self._promo_rects = {}
        self.images = {}
        self._font = None
        self._load_pieces()
        self._record_position()

    # -------------------------------------------------------------------------
    # Board setup
    # -------------------------------------------------------------------------

    def _create_board(self):
        grid = [[None] * 8 for _ in range(8)]
        back_rank = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, PieceClass in enumerate(back_rank):
            grid[0][col] = PieceClass("black")
            grid[7][col] = PieceClass("white")
        for col in range(8):
            grid[1][col] = Pawn("black")
            grid[6][col] = Pawn("white")
        return grid

    # -------------------------------------------------------------------------
    # Asset loading
    # -------------------------------------------------------------------------

    def _load_pieces(self):
        pieces_dir = os.path.join(os.path.dirname(__file__), "pieces")
        # Image filenames: wPawn.png, bRook.png, etc.
        piece_types = ["Pawn", "Rook", "Knight", "Bishop", "Queen", "King"]
        for color, prefix in [("white", "w"), ("black", "b")]:
            for piece_type in piece_types:
                key = f"{color}_{piece_type}"
                path = os.path.join(pieces_dir, f"{prefix}{piece_type}.png")
                if os.path.exists(path):
                    img = pygame.image.load(path).convert_alpha()
                    self.images[key] = pygame.transform.scale(
                        img, (self.square_size, self.square_size)
                    )

        # Fallback: unicode font rendering when images are missing
        if len(self.images) < 12:
            size = int(self.square_size * 0.75)
            for font_name in ["segoeuisymbol", "segoe ui symbol", "Arial Unicode MS"]:
                font = pygame.font.SysFont(font_name, size)
                test = font.render("♔", True, (0, 0, 0))
                if test.get_width() > 5:
                    self._font = font
                    break
            if not self._font:
                self._font = pygame.font.SysFont(None, size)

    # -------------------------------------------------------------------------
    # State queries
    # -------------------------------------------------------------------------

    def get_piece(self, row, col):
        if 0 <= row < 8 and 0 <= col < 8:
            return self.grid[row][col]
        return None

    def _in_bounds(self, row, col):
        return 0 <= row < 8 and 0 <= col < 8

    def _square_name(self, row, col):
        return f"{self._COL_NAMES[col]}{self._ROW_NAMES[row]}"

    def _record_position(self):
        """Record the current position for threefold-repetition tracking."""
        key = rules.position_key(self.grid, self.turn, self.castling_rights, self.en_passant_target)
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        return key

    # -------------------------------------------------------------------------
    # Input handling
    # -------------------------------------------------------------------------

    def handle_click(self, pixel_x, pixel_y):
        if self.game_over:
            return
        if self.promotion_pending:
            self._handle_promotion_click(pixel_x, pixel_y)
            return
        col = pixel_x // self.square_size
        row = pixel_y // self.square_size
        if self._in_bounds(row, col):
            self._select(row, col)

    def _select(self, row, col):
        piece = self.get_piece(row, col)

        if self.selected:
            if (row, col) in self.valid_moves:
                from_pos = self.selected
                to_pos = (row, col)
                if rules.is_promotion_move(self.grid, from_pos, to_pos):
                    self.promotion_pending = (from_pos, to_pos)
                else:
                    self._move(from_pos, to_pos)
                return
            if (row, col) == self.selected:
                self.selected = None
                self.valid_moves = []
                return

        if piece and piece.get_color() == self.turn:
            self.selected = (row, col)
            self.valid_moves = rules.get_legal_moves_from(
                self.grid, (row, col), self.castling_rights, self.en_passant_target
            )
        else:
            self.selected = None
            self.valid_moves = []

    def _handle_promotion_click(self, pixel_x, pixel_y):
        from_pos, to_pos = self.promotion_pending
        for piece_type, rect in self._promo_rects.items():
            if rect.collidepoint(pixel_x, pixel_y):
                self.promotion_pending = None
                self._move(from_pos, to_pos, promotion=piece_type)
                return
        # Clicked outside the picker: cancel the pending promotion
        self.promotion_pending = None
        self.selected = None
        self.valid_moves = []
        self._promo_rects = {}

    def _move(self, from_pos, to_pos, promotion=None):
        fr, fc = from_pos
        tr, tc = to_pos
        piece = self.grid[fr][fc]
        mover = piece.get_color()

        # Determine move tags from pre-move state, for the console log
        is_castle = piece.get_type() == "King" and abs(tc - fc) == 2
        is_en_passant = (
            piece.get_type() == "Pawn"
            and to_pos == self.en_passant_target
            and tc != fc
            and self.grid[tr][tc] is None
        )
        is_promotion = rules.is_promotion_move(self.grid, from_pos, to_pos)

        self.grid, self.castling_rights, self.en_passant_target, is_irreversible = rules.apply_move(
            self.grid, from_pos, to_pos, self.castling_rights, self.en_passant_target, promotion=promotion
        )
        self.halfmove_clock = 0 if is_irreversible else self.halfmove_clock + 1

        self.last_move         = (from_pos, to_pos)
        self.turn               = "black" if self.turn == "white" else "white"
        self.selected           = None
        self.valid_moves        = []
        self.promotion_pending  = None
        self._promo_rects       = {}

        # Console move log
        tag = ""
        if is_castle:
            tag = "  (O-O)" if tc == 6 else "  (O-O-O)"
        elif is_en_passant:
            tag = "  (e.p.)"
        elif is_promotion:
            tag = f"  (={self._PROMO_LETTER.get(promotion or 'Queen', 'Q')})"
        print(f"[{mover.capitalize():5}] {piece.get_type()} "
              f"{self._square_name(fr, fc)} → {self._square_name(*to_pos)}{tag}")

        # Check / checkmate / stalemate / draw detection
        self._record_position()
        self.in_check = rules.in_check(self.grid, self.turn)
        result = rules.get_game_result(
            self.grid, self.turn, self.castling_rights, self.en_passant_target,
            self.halfmove_clock, self.position_counts,
        )

        self.draw_reason = None
        if result == "checkmate":
            self.game_over = True
            self.winner = mover   # the side that just moved wins
            print(f"Checkmate! {mover.capitalize()} wins.")
        elif result is not None:
            self.game_over = True
            self.winner = None
            self.draw_reason = result
            print(f"Draw ({result.replace('_', ' ')}).")
        elif self.in_check:
            print(f"  → {self.turn.capitalize()} is in check!")

        status = "Game over" if self.game_over else self.turn.capitalize() + "'s turn"
        check_tag = " [CHECK]" if self.in_check and not self.game_over else ""
        pygame.display.set_caption(f"Chess — {status}{check_tag}")

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def draw(self, surface):
        self._draw_squares(surface)
        self._draw_last_move(surface)
        self._draw_check(surface)
        self._draw_highlights(surface)
        self._draw_valid_moves(surface)
        self._draw_pieces(surface)
        self._draw_promotion_picker(surface)

    def _draw_squares(self, surface):
        for row in range(8):
            for col in range(8):
                color = self.LIGHT if (row + col) % 2 == 0 else self.DARK
                rect = pygame.Rect(
                    col * self.square_size,
                    row * self.square_size,
                    self.square_size,
                    self.square_size,
                )
                pygame.draw.rect(surface, color, rect)

    def _draw_last_move(self, surface):
        if not self.last_move:
            return
        overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        overlay.fill((*self.LAST_MOVE_COLOR, 160))
        for row, col in self.last_move:
            surface.blit(overlay, (col * self.square_size, row * self.square_size))

    def _draw_check(self, surface):
        if not self.in_check:
            return
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.get_type() == "King" and p.get_color() == self.turn:
                    overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                    overlay.fill((*self.CHECK_COLOR, 160))
                    surface.blit(overlay, (c * self.square_size, r * self.square_size))

    def _draw_highlights(self, surface):
        if not self.selected:
            return
        row, col = self.selected
        overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        overlay.fill((*self.HIGHLIGHT_COLOR, 180))
        surface.blit(overlay, (col * self.square_size, row * self.square_size))

    def _draw_valid_moves(self, surface):
        for row, col in self.valid_moves:
            cx = col * self.square_size + self.square_size // 2
            cy = row * self.square_size + self.square_size // 2
            if self.get_piece(row, col):
                # Ring around a capturable enemy piece
                pygame.draw.circle(surface, self.VALID_MOVE_COLOR, (cx, cy), self.square_size // 2, 6)
            else:
                # Dot on an empty destination square
                pygame.draw.circle(surface, self.VALID_MOVE_COLOR, (cx, cy), self.square_size // 6)

    def _draw_pieces(self, surface):
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if not piece:
                    continue
                x = col * self.square_size
                y = row * self.square_size
                key = f"{piece.get_color()}_{piece.get_type()}"
                if key in self.images:
                    surface.blit(self.images[key], (x, y))
                elif self._font:
                    text_color = (255, 255, 255) if piece.get_color() == "white" else (0, 0, 0)
                    symbol = self.UNICODE[piece.get_color()][piece.get_type()]
                    text = self._font.render(symbol, True, text_color)
                    rect = text.get_rect(center=(x + self.square_size // 2, y + self.square_size // 2))
                    surface.blit(text, rect)

    def _draw_promotion_picker(self, surface):
        if not self.promotion_pending:
            self._promo_rects = {}
            return

        from_pos, to_pos = self.promotion_pending
        color = self.grid[from_pos[0]][from_pos[1]].get_color()
        _, tc = to_pos

        # Dim the board behind the picker
        dim = pygame.Surface((self.square_size * 8, self.square_size * 8), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        # Stack the four choices toward the promoting side: white promotes on
        # row 0 (picker grows downward), black on row 7 (grows upward).
        rows = range(0, 4) if color == "white" else range(7, 3, -1)

        self._promo_rects = {}
        for piece_type, row in zip(rules.PROMOTION_TYPES, rows):
            rect = pygame.Rect(tc * self.square_size, row * self.square_size,
                                self.square_size, self.square_size)
            pygame.draw.rect(surface, self.PROMO_BG_COLOR, rect)
            pygame.draw.rect(surface, self.PROMO_BORDER_COLOR, rect, 2)

            key = f"{color}_{piece_type}"
            if key in self.images:
                surface.blit(self.images[key], rect.topleft)
            elif self._font:
                symbol = self.UNICODE[color][piece_type]
                text = self._font.render(symbol, True, (0, 0, 0))
                surface.blit(text, text.get_rect(center=rect.center))

            self._promo_rects[piece_type] = rect
