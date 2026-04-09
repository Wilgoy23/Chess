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
    LAST_MOVE_COLOR = (205, 210, 106)
    CHECK_COLOR = (220, 20, 20)

    _COL_NAMES = "abcdefgh"
    _ROW_NAMES = "87654321"  # row 0 = rank 8

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
        self.last_move = None   # (from_pos, to_pos) of the most recent move
        self.in_check = False   # True when the side to move is in check
        self.game_over = False
        self.winner = None      # "white", "black", or None (stalemate)
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
    # Check / legality helpers
    # -------------------------------------------------------------------------

    def _is_square_attacked(self, grid, row, col, by_color):
        """Return True if (row, col) is reachable by any piece of by_color."""
        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p and p.get_color() == by_color:
                    if (row, col) in (p.get_possible_moves(grid, (r, c)) or []):
                        return True
        return False

    def _is_in_check(self, grid, color):
        """Return True if color's king is currently attacked."""
        opponent = "black" if color == "white" else "white"
        for r in range(8):
            for c in range(8):
                p = grid[r][c]
                if p and p.get_type() == "King" and p.get_color() == color:
                    return self._is_square_attacked(grid, r, c, opponent)
        return False  # king not found (shouldn't happen)

    def _get_legal_moves(self, from_pos):
        """Return moves for the piece at from_pos that don't leave own king in check."""
        fr, fc = from_pos
        piece = self.grid[fr][fc]
        if piece is None:
            return []
        color = piece.get_color()
        raw = list(piece.get_possible_moves(self.grid, from_pos) or [])
        if piece.get_type() == "King":
            raw += self._get_castling_moves(color)

        legal = []
        for to_pos in raw:
            tr, tc = to_pos
            test = [row[:] for row in self.grid]
            test[tr][tc] = test[fr][fc]
            test[fr][fc] = None
            # Simulate castling rook relocation in the test grid
            if piece.get_type() == "King" and abs(tc - fc) == 2:
                if tc == 6:
                    test[fr][5] = test[fr][7]
                    test[fr][7] = None
                else:
                    test[fr][3] = test[fr][0]
                    test[fr][0] = None
            if not self._is_in_check(test, color):
                legal.append(to_pos)
        return legal

    def _has_any_legal_move(self, color):
        """Return True if color has at least one legal move."""
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p and p.get_color() == color:
                    if self._get_legal_moves((r, c)):
                        return True
        return False

    def _square_name(self, row, col):
        return f"{self._COL_NAMES[col]}{self._ROW_NAMES[row]}"

    # -------------------------------------------------------------------------
    # Input handling
    # -------------------------------------------------------------------------

    def handle_click(self, pixel_x, pixel_y):
        if self.game_over:
            return
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
            self.valid_moves = self._get_legal_moves((row, col))
        else:
            self.selected = None
            self.valid_moves = []

    def _get_castling_moves(self, color):
        moves = []
        row = 7 if color == "white" else 0
        rights = self.castling_rights[color]
        opponent = "black" if color == "white" else "white"

        king = self.grid[row][4]
        if king is None or king.get_type() != "King":
            return moves
        # Can't castle while in check
        if self._is_in_check(self.grid, color):
            return moves

        # Kingside: e→f→g must be clear and f,g not attacked
        if (rights["kingside"]
                and self.grid[row][5] is None
                and self.grid[row][6] is None
                and not self._is_square_attacked(self.grid, row, 5, opponent)
                and not self._is_square_attacked(self.grid, row, 6, opponent)):
            moves.append((row, 6))

        # Queenside: b,c,d must be empty; d,c not attacked (king passes through d,c)
        if (rights["queenside"]
                and self.grid[row][1] is None
                and self.grid[row][2] is None
                and self.grid[row][3] is None
                and not self._is_square_attacked(self.grid, row, 3, opponent)
                and not self._is_square_attacked(self.grid, row, 2, opponent)):
            moves.append((row, 2))

        return moves

    def _move(self, from_pos, to_pos):
        fr, fc = from_pos
        piece    = self.grid[fr][fc]
        captured = self.grid[to_pos[0]][to_pos[1]]

        # Revoke castling rights if a corner rook is captured
        if captured is not None and captured.get_type() == "Rook":
            if   to_pos == (7, 0): self.castling_rights["white"]["queenside"] = False
            elif to_pos == (7, 7): self.castling_rights["white"]["kingside"]  = False
            elif to_pos == (0, 0): self.castling_rights["black"]["queenside"] = False
            elif to_pos == (0, 7): self.castling_rights["black"]["kingside"]  = False

        # Delegate grid mutations to the piece
        for origin, destination, piece_obj in piece.move(self.grid, from_pos, to_pos):
            self.grid[destination[0]][destination[1]] = piece_obj
            self.grid[origin[0]][origin[1]] = None

        # Board-owned castling rights revocation
        ptype, color = piece.get_type(), piece.get_color()
        if ptype == "King":
            self.castling_rights[color]["kingside"]  = False
            self.castling_rights[color]["queenside"] = False
        if ptype == "Rook":
            if   (fr, fc) == (7, 0): self.castling_rights["white"]["queenside"] = False
            elif (fr, fc) == (7, 7): self.castling_rights["white"]["kingside"]  = False
            elif (fr, fc) == (0, 0): self.castling_rights["black"]["queenside"] = False
            elif (fr, fc) == (0, 7): self.castling_rights["black"]["kingside"]  = False

        # Console move log
        mover = piece.get_color()
        print(f"[{mover.capitalize():5}] {piece.get_type()} "
              f"{self._square_name(fr, fc)} → {self._square_name(*to_pos)}")

        self.last_move   = (from_pos, to_pos)
        self.turn        = "black" if self.turn == "white" else "white"
        self.selected    = None
        self.valid_moves = []

        # Check / checkmate / stalemate detection
        self.in_check = self._is_in_check(self.grid, self.turn)
        if not self._has_any_legal_move(self.turn):
            self.game_over = True
            if self.in_check:
                self.winner = mover   # the side that just moved wins
                print(f"Checkmate! {mover.capitalize()} wins.")
            else:
                self.winner = None
                print("Stalemate! Draw.")
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
