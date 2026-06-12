"""
Stockfish engine wrapper — communicates over the UCI protocol.

Requirements
------------
The Stockfish binary must be available either:
  • on PATH  (just install it and the agent finds it automatically), or
  • at one of the well-known Windows paths listed in _find_stockfish(), or
  • passed explicitly as stockfish_path=

Download: https://stockfishchess.org/download/
"""

import os
import shutil
import subprocess

from Agents.AgentInterface import AgentInterface

# UCI piece letters (white = upper, black = lower)
_PIECE_LETTER = {
    "Pawn": "P", "Rook": "R", "Knight": "N",
    "Bishop": "B", "Queen": "Q", "King": "K",
}
_COL_IDX = {c: i for i, c in enumerate("abcdefgh")}


# ---------------------------------------------------------------------------
# FEN helpers
# ---------------------------------------------------------------------------

def _grid_to_fen(grid, color: str, castling_rights, en_passant_target=None) -> str:
    """Convert the internal board state to a FEN position string."""
    ranks = []
    for row in range(8):            # row 0 = rank 8, row 7 = rank 1
        s, empty = "", 0
        for col in range(8):        # col 0 = a-file, col 7 = h-file
            p = grid[row][col]
            if p is None:
                empty += 1
            else:
                if empty:
                    s += str(empty)
                    empty = 0
                letter = _PIECE_LETTER[p.get_type()]
                if p.get_color() == "black":
                    letter = letter.lower()
                s += letter
        if empty:
            s += str(empty)
        ranks.append(s)

    castling = ""
    if castling_rights["white"]["kingside"]:
        castling += "K"
    if castling_rights["white"]["queenside"]:
        castling += "Q"
    if castling_rights["black"]["kingside"]:
        castling += "k"
    if castling_rights["black"]["queenside"]:
        castling += "q"
    castling = castling or "-"

    if en_passant_target is not None:
        er, ec = en_passant_target
        en_passant = f"{'abcdefgh'[ec]}{8 - er}"
    else:
        en_passant = "-"

    active = "w" if color == "white" else "b"
    return f"{'/'.join(ranks)} {active} {castling} {en_passant} 0 1"


def _uci_to_move(uci: str) -> tuple:
    """Parse a UCI move string into ((from_row, from_col), (to_row, to_col)).

    The optional promotion character (e.g. 'q' in 'e7e8q') is ignored
    because the board always promotes to Queen.
    """
    fc = _COL_IDX[uci[0]];  fr = 8 - int(uci[1])
    tc = _COL_IDX[uci[2]];  tr = 8 - int(uci[3])
    return (fr, fc), (tr, tc)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class StockfishAgent(AgentInterface):
    """Chess agent backed by the Stockfish engine via UCI.

    Parameters
    ----------
    color : str
        "white" or "black"
    time_limit : float
        Seconds per move (sent as movetime to Stockfish).
    skill_level : int
        0 (weakest) to 20 (strongest, default).
    stockfish_path : str | None
        Explicit path to the binary.  Auto-detected when None.
    """

    def __init__(self, color: str, time_limit: float = 2.0,
                 skill_level: int = 20,
                 stockfish_path: str | None = None) -> None:
        self.color       = color
        self.time_limit  = time_limit
        self.skill_level = skill_level

        path = stockfish_path or StockfishAgent._find_stockfish()
        if path is None:
            raise FileNotFoundError(
                "Stockfish binary not found.\n"
                "  Download from https://stockfishchess.org/download/\n"
                "  then add it to PATH, or pass stockfish_path= explicitly."
            )

        self._proc = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        # UCI handshake
        self._send("uci")
        self._read_until("uciok")
        self._send(f"setoption name Skill Level value {skill_level}")
        self._send("isready")
        self._read_until("readyok")
        print(f"[Stockfish] ready  path={path}  "
              f"skill={skill_level}  time_limit={time_limit}s")

    # -------------------------------------------------------------------------
    # AgentInterface
    # -------------------------------------------------------------------------

    def get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple | None:
        fen = _grid_to_fen(grid, color, castling_rights, en_passant_target)
        self._send(f"position fen {fen}")
        self._send(f"go movetime {max(1, int(self.time_limit * 1000))}")

        while True:
            line = self._proc.stdout.readline()
            if not line:            # process died unexpectedly
                return None
            parts = line.split()
            if parts and parts[0] == "bestmove":
                if len(parts) >= 2 and parts[1] != "(none)":
                    return _uci_to_move(parts[1])
                return None

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _send(self, cmd: str) -> None:
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _read_until(self, token: str) -> str:
        """Block until a stdout line containing *token* is received."""
        while True:
            line = self._proc.stdout.readline().strip()
            if token in line:
                return line

    @staticmethod
    def _find_stockfish() -> str | None:
        """Return the path to a Stockfish binary, or None if not found."""
        # Search PATH first — works after a standard install or if user added it
        found = shutil.which("stockfish") or shutil.which("stockfish.exe")
        if found:
            return found

        # Common Windows locations
        home    = os.path.expanduser("~")
        appdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(home,    "stockfish", "stockfish.exe"),
            os.path.join(home,    "stockfish", "stockfish"),
            os.path.join(home,    "Downloads", "stockfish.exe"),
            os.path.join(appdata, "Programs",  "stockfish", "stockfish.exe"),
            r"C:\stockfish\stockfish.exe",
            r"C:\Program Files\Stockfish\stockfish.exe",
            r"C:\Program Files (x86)\Stockfish\stockfish.exe",
        ]
        for p in candidates:
            if p and os.path.isfile(p):
                return p

        # Last resort: Stockfish is usually downloaded as a zip and extracted
        # into a versioned subfolder (e.g. Downloads\stockfish-windows-x86-64-
        # avx2\stockfish\stockfish-windows-x86-64-avx2.exe). Search a few
        # levels deep in the places people tend to extract zips.
        for base in (os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), home):
            found = StockfishAgent._search_for_binary(base, max_depth=3)
            if found:
                return found
        return None

    @staticmethod
    def _search_for_binary(base: str, max_depth: int = 3) -> str | None:
        """Recursively look under `base` (up to `max_depth` levels deep) for a
        file named stockfish*.exe, returning the first match found."""
        if not os.path.isdir(base):
            return None
        base_depth = base.rstrip("\\/").count(os.sep)
        for root, dirs, files in os.walk(base):
            if root.rstrip("\\/").count(os.sep) - base_depth >= max_depth:
                dirs[:] = []   # don't descend further
                continue
            for f in files:
                if f.lower().startswith("stockfish") and f.lower().endswith(".exe"):
                    return os.path.join(root, f)
        return None

    def __del__(self) -> None:
        try:
            self._send("quit")
            self._proc.wait(timeout=2)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
