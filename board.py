import pygame
import os

from Pieces.Pawn import Pawn
from Pieces.Rook import Rook
from Pieces.Knight import Knight
from Pieces.Bishop import Bishop
from Pieces.Queen import Queen
from Pieces.King import King


class Board:
    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    HIGHLIGHT_COLOR = (186, 202, 68)
    VALID_MOVE_COLOR = (100, 111, 64)

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
        self.images = {}
        self._font = None
        self._load_pieces()

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

    # -------------------------------------------------------------------------
    # Input handling
    # -------------------------------------------------------------------------

    def handle_click(self, pixel_x, pixel_y):
        col = pixel_x // self.square_size
        row = pixel_y // self.square_size
        if self._in_bounds(row, col):
            self._select(row, col)

    def _select(self, row, col):
        piece = self.get_piece(row, col)

        if self.selected:
            if (row, col) in self.valid_moves:
                self._move(self.selected, (row, col))
                return
            if (row, col) == self.selected:
                self.selected = None
                self.valid_moves = []
                return

        if piece and piece.get_color() == self.turn:
            self.selected = (row, col)
            self.valid_moves = piece.get_possible_moves(self.grid, (row, col))
            if self.valid_moves is None:
                self.valid_moves = []
            if piece.get_type() == "King":
                self.valid_moves += self._get_castling_moves(piece.get_color())
        else:
            self.selected = None
            self.valid_moves = []

    def _get_castling_moves(self, color):
        moves = []
        row = 7 if color == "white" else 0
        rights = self.castling_rights[color]
        # King must still be on its starting square
        king = self.grid[row][4]
        if king is None or king.get_type() != "King":
            return moves
        # Kingside: squares f and g must be empty
        if rights["kingside"] and self.grid[row][5] is None and self.grid[row][6] is None:
            moves.append((row, 6))
        # Queenside: squares b, c, d must be empty
        if rights["queenside"] and self.grid[row][1] is None and self.grid[row][2] is None and self.grid[row][3] is None:
            moves.append((row, 2))
        return moves

    def _move(self, from_pos, to_pos):
        fr, fc = from_pos
        tr, tc = to_pos
        piece = self.grid[fr][fc]
        captured = self.grid[tr][tc]

        # Revoke castling rights if a corner rook is captured
        if captured is not None and captured.get_type() == "Rook":
            if (tr, tc) == (7, 0): self.castling_rights["white"]["queenside"] = False
            elif (tr, tc) == (7, 7): self.castling_rights["white"]["kingside"] = False
            elif (tr, tc) == (0, 0): self.castling_rights["black"]["queenside"] = False
            elif (tr, tc) == (0, 7): self.castling_rights["black"]["kingside"] = False

        self.grid[tr][tc] = piece
        self.grid[fr][fc] = None

        # Pawn promotion: auto-promote to Queen
        if piece.get_type() == "Pawn":
            promo_row = 0 if piece.get_color() == "white" else 7
            if tr == promo_row:
                self.grid[tr][tc] = Queen(piece.get_color())

        # King move: revoke all castling rights; detect and execute castling
        if piece.get_type() == "King":
            color = piece.get_color()
            self.castling_rights[color]["kingside"] = False
            self.castling_rights[color]["queenside"] = False
            if abs(tc - fc) == 2:  # castling move detected
                if tc == 6:  # kingside — rook goes from h to f
                    self.grid[fr][5] = self.grid[fr][7]
                    self.grid[fr][7] = None
                else:         # queenside (tc == 2) — rook goes from a to d
                    self.grid[fr][3] = self.grid[fr][0]
                    self.grid[fr][0] = None

        # Rook move: revoke the relevant castling right
        if piece.get_type() == "Rook":
            if (fr, fc) == (7, 0): self.castling_rights["white"]["queenside"] = False
            elif (fr, fc) == (7, 7): self.castling_rights["white"]["kingside"] = False
            elif (fr, fc) == (0, 0): self.castling_rights["black"]["queenside"] = False
            elif (fr, fc) == (0, 7): self.castling_rights["black"]["kingside"] = False

        self.turn = "black" if self.turn == "white" else "white"
        self.selected = None
        self.valid_moves = []

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def draw(self, surface):
        self._draw_squares(surface)
        self._draw_highlights(surface)
        self._draw_valid_moves(surface)
        self._draw_pieces(surface)

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
