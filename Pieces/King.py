from Pieces.PieceInterface import PieceInterface

class King(PieceInterface):
    def __init__(self, color):
        self.color = color

    def get_possible_moves(self, board, position, en_passant_target=None):
        moves = []
        row, col = position
        # King moves one square in any direction
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target is None or target.get_color() != self.color:
                        moves.append((nr, nc))
        return moves

    def get_color(self):
        return self.color

    def get_type(self):
        return "King"

    def move(self, grid: list, from_pos: tuple, to_pos: tuple,
             promotion: str = None, en_passant_target: tuple = None) -> list:
        fr, fc = from_pos
        tc = to_pos[1]
        mutations = [(from_pos, to_pos, self)]

        if abs(tc - fc) == 2:               # castling detected
            if tc == 6:                     # kingside: rook h→f
                rook_origin, rook_dest = (fr, 7), (fr, 5)
            else:                           # queenside: rook a→d
                rook_origin, rook_dest = (fr, 0), (fr, 3)

            rook = grid[rook_origin[0]][rook_origin[1]]
            if rook is not None:
                mutations.append((rook_origin, rook_dest, rook))

        return mutations

    def is_valid_move(self, board, start_pos, end_pos):
        pass