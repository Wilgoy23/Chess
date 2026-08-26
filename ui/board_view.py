"""Board rendering and click-to-move interaction.

Reads game state from a GameState instance passed into each call; owns only
UI-local interaction state (selection, promotion picker) and pygame
image/font assets. Doesn't mutate GameState itself — handle_click() returns
a completed (from_pos, to_pos, promotion) once the user has fully specified a
move, and the caller (main.py) is responsible for applying it via
GameController.play_move().
"""

import os

import pygame

import rules
from ui.layout import SQUARE_SIZE


class BoardView:
    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    HIGHLIGHT_COLOR = (186, 202, 68)
    VALID_MOVE_COLOR = (100, 111, 64)
    LAST_MOVE_COLOR = (205, 210, 106)
    CHECK_COLOR = (220, 20, 20)
    PROMO_BG_COLOR = (240, 240, 240)
    PROMO_BORDER_COLOR = (80, 80, 80)

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

    def __init__(self, square_size: int = SQUARE_SIZE):
        self.square_size = square_size
        self.selected = None            # (row, col) of the selected square
        self.valid_moves = []           # destinations for the selected piece
        self.promotion_pending = None   # (from_pos, to_pos) awaiting a choice
        self._promo_rects: dict = {}
        self.images: dict = {}
        self._font = None
        self._load_pieces()

    def reset_selection(self) -> None:
        """Clear click-in-progress UI state — call after undo/new game, since
        a stale selection or pending promotion may no longer make sense."""
        self.selected = None
        self.valid_moves = []
        self.promotion_pending = None
        self._promo_rects = {}

    # -------------------------------------------------------------------------
    # Asset loading
    # -------------------------------------------------------------------------

    def _load_pieces(self) -> None:
        pieces_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pieces")
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
    # Input handling
    # -------------------------------------------------------------------------

    def handle_click(self, pixel_x: int, pixel_y: int, state) -> tuple | None:
        """Returns (from_pos, to_pos, promotion) once click-click selection
        (plus a promotion-picker click, if needed) has fully specified a
        move; otherwise updates internal selection state and returns None."""
        if state.game_over:
            return None
        if self.promotion_pending:
            return self._handle_promotion_click(pixel_x, pixel_y)

        col = pixel_x // self.square_size
        row = pixel_y // self.square_size
        if not (0 <= row < 8 and 0 <= col < 8):
            return None
        return self._select(row, col, state)

    def _select(self, row: int, col: int, state) -> tuple | None:
        piece = state.grid[row][col]

        if self.selected:
            if (row, col) in self.valid_moves:
                from_pos = self.selected
                to_pos = (row, col)
                if state.is_promotion_move(from_pos, to_pos):
                    self.promotion_pending = (from_pos, to_pos)
                    self.selected = None
                    self.valid_moves = []
                    return None
                self.selected = None
                self.valid_moves = []
                return (from_pos, to_pos, None)
            if (row, col) == self.selected:
                self.selected = None
                self.valid_moves = []
                return None

        if piece and piece.get_color() == state.turn:
            self.selected = (row, col)
            self.valid_moves = state.legal_moves_from((row, col))
        else:
            self.selected = None
            self.valid_moves = []
        return None

    def _handle_promotion_click(self, pixel_x: int, pixel_y: int) -> tuple | None:
        from_pos, to_pos = self.promotion_pending
        for piece_type, rect in self._promo_rects.items():
            if rect.collidepoint(pixel_x, pixel_y):
                self.promotion_pending = None
                return (from_pos, to_pos, piece_type)
        # Clicked outside the picker: cancel the pending promotion
        self.promotion_pending = None
        self.selected = None
        self.valid_moves = []
        self._promo_rects = {}
        return None

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def draw(self, surface, state) -> None:
        self._draw_squares(surface)
        self._draw_last_move(surface, state)
        self._draw_check(surface, state)
        self._draw_highlights(surface)
        self._draw_valid_moves(surface, state)
        self._draw_pieces(surface, state)
        self._draw_promotion_picker(surface, state)

    def _draw_squares(self, surface) -> None:
        for row in range(8):
            for col in range(8):
                color = self.LIGHT if (row + col) % 2 == 0 else self.DARK
                rect = pygame.Rect(
                    col * self.square_size, row * self.square_size,
                    self.square_size, self.square_size,
                )
                pygame.draw.rect(surface, color, rect)

    def _draw_last_move(self, surface, state) -> None:
        if not state.last_move:
            return
        overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        overlay.fill((*self.LAST_MOVE_COLOR, 160))
        for row, col in state.last_move:
            surface.blit(overlay, (col * self.square_size, row * self.square_size))

    def _draw_check(self, surface, state) -> None:
        if not state.in_check:
            return
        for r in range(8):
            for c in range(8):
                p = state.grid[r][c]
                if p and p.get_type() == "King" and p.get_color() == state.turn:
                    overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                    overlay.fill((*self.CHECK_COLOR, 160))
                    surface.blit(overlay, (c * self.square_size, r * self.square_size))

    def _draw_highlights(self, surface) -> None:
        if not self.selected:
            return
        row, col = self.selected
        overlay = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        overlay.fill((*self.HIGHLIGHT_COLOR, 180))
        surface.blit(overlay, (col * self.square_size, row * self.square_size))

    def _draw_valid_moves(self, surface, state) -> None:
        for row, col in self.valid_moves:
            cx = col * self.square_size + self.square_size // 2
            cy = row * self.square_size + self.square_size // 2
            if state.grid[row][col]:
                pygame.draw.circle(surface, self.VALID_MOVE_COLOR, (cx, cy), self.square_size // 2, 6)
            else:
                pygame.draw.circle(surface, self.VALID_MOVE_COLOR, (cx, cy), self.square_size // 6)

    def _draw_pieces(self, surface, state) -> None:
        for row in range(8):
            for col in range(8):
                piece = state.grid[row][col]
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

    def _draw_promotion_picker(self, surface, state) -> None:
        if not self.promotion_pending:
            self._promo_rects = {}
            return

        from_pos, to_pos = self.promotion_pending
        color = state.grid[from_pos[0]][from_pos[1]].get_color()
        _, tc = to_pos

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
