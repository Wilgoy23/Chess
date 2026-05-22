import copy
import queue
import threading

import pygame
from Agents.MinimaxAgent import MinimaxAgent
from Agents.MonteCarloAgent import MonteCarloAgent
from Agents.RandomAgent import RandomAgent
from board import Board

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
SQUARE_SIZE = 100
BOARD_PX    = SQUARE_SIZE * 8          # 800 — board play area
INFO_H      = 60                        # player / clock strip below board
CTRL_H      = 52                        # button strip at bottom
WIN_W       = BOARD_PX
WIN_H       = BOARD_PX + INFO_H + CTRL_H   # 912

INFO_Y = BOARD_PX                       # y-origin of info strip
CTRL_Y = BOARD_PX + INFO_H             # y-origin of control strip

pygame.init()

# Probe for a Unicode-capable font.  The default SysFont(None) uses Arial on
# Windows which lacks block/symbol glyphs (▶ ⏸ ◀ ⚙ …).  Segoe UI Symbol
# ships with every Windows 10/11 install and covers all the characters we use.
_UI_FONT: str | None = None
for _candidate in ["segoeuisymbol", "segoe ui symbol", "Arial Unicode MS",
                   "dejavusans", "freesans", "notosans"]:
    try:
        _probe = pygame.font.SysFont(_candidate, 20)
        _surf  = _probe.render("▶⏸◀⚙", True, (255, 255, 255))
        if _surf.get_width() > 16:      # each glyph must have at least 4 px
            _UI_FONT = _candidate
            break
    except Exception:
        pass

screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Chess")
clock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Configuration  (mutated by the config modal)
# ---------------------------------------------------------------------------
AGENT_TYPES  = ["human", "random", "minimax", "montecarlo"]
AGENT_LABELS = {
    "human":      "Human",
    "random":     "Random",
    "minimax":    "Minimax",
    "montecarlo": "MCTS",
}
AI_TIMES     = [0.5, 1.0, 2.0, 5.0]
AI_TIME_LBLS = ["0.5 s", "1 s", "2 s", "5 s"]
H_TIMES      = [0, 60, 180, 300, 600]          # 0 = unlimited
H_TIME_LBLS  = ["∞", "1 min", "3 min", "5 min", "10 min"]

_cfg: dict = {
    "white":      "montecarlo",
    "black":      "minimax",
    "ai_time":    2.0,
    "human_time": 0,            # seconds per side, 0 = unlimited
}

# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------
def _make_agent(kind: str, color: str, ai_time: float):
    if kind == "human":       return None
    if kind == "random":      return RandomAgent(color)
    if kind == "minimax":     return MinimaxAgent(color, time_limit=ai_time)
    if kind == "montecarlo":  return MonteCarloAgent(color, time_limit=ai_time)
    return None

WHITE_PLAYER = _make_agent(_cfg["white"], "white", _cfg["ai_time"])
BLACK_PLAYER = _make_agent(_cfg["black"], "black", _cfg["ai_time"])

board = Board(square_size=SQUARE_SIZE)


def current_agent():
    return WHITE_PLAYER if board.turn == "white" else BLACK_PLAYER


def _both_ai() -> bool:
    return WHITE_PLAYER is not None and BLACK_PLAYER is not None


def _agent_label(agent) -> str:
    if agent is None:
        return "Human"
    return type(agent).__name__.replace("Agent", "")


# ---------------------------------------------------------------------------
# Thread-safe move pipeline
# ---------------------------------------------------------------------------
_move_queue  = queue.Queue(maxsize=1)
_move_lock   = threading.Lock()
_search_gen  = 0
_agent_thread: threading.Thread | None = None


def _run_agent(agent, grid: list, turn: str, gen: int) -> None:
    move = agent.get_move(grid, turn)
    if move:
        with _move_lock:
            if gen == _search_gen:
                try:
                    _move_queue.put_nowait(move)
                except queue.Full:
                    pass


def _cancel_search() -> None:
    global _agent_thread, _search_gen
    with _move_lock:
        _search_gen += 1
        while not _move_queue.empty():
            try:
                _move_queue.get_nowait()
            except queue.Empty:
                break
    if _agent_thread is not None:
        _agent_thread.join(timeout=0.05)
    _agent_thread = None


def _start_search(agent) -> None:
    global _agent_thread
    _agent_thread = threading.Thread(
        target=_run_agent,
        args=(agent, [row[:] for row in board.grid], board.turn, _search_gen),
        daemon=True,
    )
    _agent_thread.start()


# ---------------------------------------------------------------------------
# Human chess clocks
# ---------------------------------------------------------------------------
_h_clocks: dict[str, float] = {
    "white": float(_cfg["human_time"]),
    "black": float(_cfg["human_time"]),
}


def _fmt_clock(secs: float) -> str:
    if secs <= 0:
        return "0:00"
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def _clock_col(secs: float) -> tuple:
    if secs > 30:  return (100, 210, 100)
    if secs > 10:  return (220, 190, 60)
    return (220, 60, 60)


# ---------------------------------------------------------------------------
# History / undo  (all game modes)
# ---------------------------------------------------------------------------
_history: list[dict] = []


def _snapshot() -> dict:
    return {
        "grid":     [[p for p in row] for row in board.grid],
        "turn":     board.turn,
        "castling": copy.deepcopy(board.castling_rights),
        "last":     board.last_move,
        "check":    board.in_check,
        "over":     board.game_over,
        "winner":   board.winner,
        "clocks":   dict(_h_clocks),    # restore clocks on undo
    }


def _restore(snap: dict) -> None:
    board.grid            = [[p for p in row] for row in snap["grid"]]
    board.turn            = snap["turn"]
    board.castling_rights = copy.deepcopy(snap["castling"])
    board.last_move       = snap["last"]
    board.in_check        = snap["check"]
    board.game_over       = snap["over"]
    board.winner          = snap["winner"]
    board.selected        = None
    board.valid_moves     = []
    _h_clocks.update(snap["clocks"])


def _undo() -> None:
    if not _history:
        return
    _cancel_search()
    _restore(_history.pop())


# ---------------------------------------------------------------------------
# Config → new game
# ---------------------------------------------------------------------------
def _apply_config() -> None:
    """Build agents from _cfg, reset the board, and start playing."""
    global board, WHITE_PLAYER, BLACK_PLAYER, _paused, _step_requested, _in_config
    _cancel_search()
    board        = Board(square_size=SQUARE_SIZE)
    WHITE_PLAYER = _make_agent(_cfg["white"], "white", _cfg["ai_time"])
    BLACK_PLAYER = _make_agent(_cfg["black"], "black", _cfg["ai_time"])
    _h_clocks["white"] = float(_cfg["human_time"])
    _h_clocks["black"] = float(_cfg["human_time"])
    _history.clear()
    _paused         = _both_ai()
    _step_requested = False
    _in_config      = False


def _open_config() -> None:
    global _in_config
    _cancel_search()
    _in_config = True


# ---------------------------------------------------------------------------
# Fonts  (lazy, keyed by size)
# ---------------------------------------------------------------------------
_fonts: dict[int, pygame.font.Font] = {}


def _f(size: int) -> pygame.font.Font:
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont(_UI_FONT, size)
    return _fonts[size]


# ---------------------------------------------------------------------------
# Generic UI helpers
# ---------------------------------------------------------------------------
def _filled_btn(surface: pygame.Surface, label: str, rect: pygame.Rect,
                bg: tuple, fg: tuple = (255, 255, 255),
                highlight: bool = False, fsize: int = 22) -> None:
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    if highlight:
        pygame.draw.rect(surface, (255, 210, 50), rect, 2, border_radius=6)
    txt = _f(fsize).render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=rect.center))


def _centered(surface: pygame.Surface, text: str, size: int,
              color: tuple, cx: int, cy: int) -> None:
    s = _f(size).render(text, True, color)
    surface.blit(s, s.get_rect(center=(cx, cy)))


# ---------------------------------------------------------------------------
# Config modal
# ---------------------------------------------------------------------------
_cfg_rects: dict[str, pygame.Rect] = {}   # populated each frame in config mode


def _draw_config(surface: pygame.Surface) -> dict[str, pygame.Rect]:
    # Dim the board behind the modal
    dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 180))
    surface.blit(dim, (0, 0))

    MW, MH = 620, 468
    MX = (WIN_W - MW) // 2
    MY = (WIN_H - MH) // 2
    pygame.draw.rect(surface, (28, 28, 40), (MX, MY, MW, MH), border_radius=12)
    pygame.draw.rect(surface, (70, 70, 110), (MX, MY, MW, MH), 2, border_radius=12)

    rects: dict[str, pygame.Rect] = {}
    cx = MX + MW // 2

    _centered(surface, "GAME SETUP", 36, (210, 210, 255), cx, MY + 28)
    pygame.draw.line(surface, (60, 60, 90), (MX + 20, MY + 52), (MX + MW - 20, MY + 52))

    # ── Player columns ──────────────────────────────────────────────────────
    for side, col_cx in (("white", MX + 155), ("black", MX + 465)):
        label = "WHITE" if side == "white" else "BLACK"
        col   = (230, 230, 230) if side == "white" else (160, 160, 160)
        _centered(surface, label, 22, col, col_cx, MY + 72)

        for i, atype in enumerate(AGENT_TYPES):
            r   = pygame.Rect(col_cx - 70, MY + 88 + i * 42, 140, 34)
            sel = _cfg[side] == atype
            _filled_btn(surface, AGENT_LABELS[atype], r,
                        bg=(50, 90, 50) if sel else (40, 40, 58),
                        highlight=sel)
            rects[f"{side}_{atype}"] = r

    # vertical separator
    sx = cx
    pygame.draw.line(surface, (60, 60, 90), (sx, MY + 60), (sx, MY + 260))

    # ── AI think time ────────────────────────────────────────────────────────
    pygame.draw.line(surface, (60, 60, 90), (MX + 20, MY + 262), (MX + MW - 20, MY + 262))
    _centered(surface, "AI THINK TIME  (per move)", 21, (170, 170, 200), cx, MY + 280)

    btn_w  = 86
    gap    = 10
    row_w  = len(AI_TIMES) * btn_w + (len(AI_TIMES) - 1) * gap
    row_x0 = cx - row_w // 2
    for i, (t, lbl) in enumerate(zip(AI_TIMES, AI_TIME_LBLS)):
        r   = pygame.Rect(row_x0 + i * (btn_w + gap), MY + 296, btn_w, 32)
        sel = abs(_cfg["ai_time"] - t) < 0.01
        _filled_btn(surface, lbl, r, bg=(50, 90, 50) if sel else (40, 40, 58),
                    highlight=sel)
        rects[f"ai_{t}"] = r

    # ── Human clock ──────────────────────────────────────────────────────────
    pygame.draw.line(surface, (60, 60, 90), (MX + 20, MY + 342), (MX + MW - 20, MY + 342))
    _centered(surface, "HUMAN CLOCK  (per side, total game)", 21, (170, 170, 200),
              cx, MY + 360)

    btn_w  = 82
    gap    = 8
    row_w  = len(H_TIMES) * btn_w + (len(H_TIMES) - 1) * gap
    row_x0 = cx - row_w // 2
    for i, (t, lbl) in enumerate(zip(H_TIMES, H_TIME_LBLS)):
        r   = pygame.Rect(row_x0 + i * (btn_w + gap), MY + 376, btn_w, 32)
        sel = _cfg["human_time"] == t
        _filled_btn(surface, lbl, r, bg=(50, 90, 50) if sel else (40, 40, 58),
                    highlight=sel)
        rects[f"ht_{t}"] = r

    # ── Start button ─────────────────────────────────────────────────────────
    start_r = pygame.Rect(cx - 110, MY + MH - 52, 220, 40)
    pygame.draw.rect(surface, (36, 120, 56), start_r, border_radius=8)
    pygame.draw.rect(surface, (70, 190, 90), start_r, 2, border_radius=8)
    _centered(surface, "▶  START GAME", 26, (255, 255, 255),
              start_r.centerx, start_r.centery)
    rects["start"] = start_r

    return rects


def _config_click(mx: int, my: int) -> None:
    for key, rect in _cfg_rects.items():
        if not rect.collidepoint(mx, my):
            continue
        if key == "start":
            _apply_config()
        elif "_" in key:
            prefix, _, val = key.partition("_")
            if prefix in ("white", "black"):
                _cfg[prefix] = val
            elif prefix == "ai":
                _cfg["ai_time"] = float(val)
            elif prefix == "ht":
                _cfg["human_time"] = int(val)
        return


# ---------------------------------------------------------------------------
# Info bar  (always visible, below the board)
# ---------------------------------------------------------------------------
def _draw_info_bar(surface: pygame.Surface, thinking: bool, move_num: int) -> None:
    pygame.draw.rect(surface, (18, 18, 24), pygame.Rect(0, INFO_Y, WIN_W, INFO_H))

    unlimited = _cfg["human_time"] == 0

    for side, x_cx in (("white", WIN_W // 4), ("black", 3 * WIN_W // 4)):
        agent = WHITE_PLAYER if side == "white" else BLACK_PLAYER
        name  = _agent_label(agent)

        name_col = (220, 220, 220) if side == "white" else (160, 160, 160)
        _centered(surface, f"{side.capitalize()} — {name}", 22, name_col,
                  x_cx, INFO_Y + 16)

        is_active = (board.turn == side) and not board.game_over

        if agent is None:                                   # human player
            if unlimited:
                clk_str = "∞"
                clk_col = (100, 100, 120)
            else:
                remaining = _h_clocks[side]
                clk_str   = _fmt_clock(remaining)
                clk_col   = _clock_color_active(remaining, is_active)
            _centered(surface, clk_str, 30, clk_col, x_cx, INFO_Y + 42)
        else:                                               # AI player
            ai_str = f"{_cfg['ai_time']:.4g} s / move"
            ai_col = (255, 200, 50) if (is_active and thinking) else (90, 90, 110)
            _centered(surface, ai_str, 24, ai_col, x_cx, INFO_Y + 42)

    # Centre dividers and move counter
    pygame.draw.line(surface, (40, 40, 55), (WIN_W // 2, INFO_Y + 8),
                     (WIN_W // 2, INFO_Y + INFO_H - 8))
    status = f"move {move_num}" if not thinking else "thinking…"
    _centered(surface, status, 20, (100, 100, 130), WIN_W // 2, INFO_Y + INFO_H // 2)


def _clock_color_active(secs: float, is_active: bool) -> tuple:
    if not is_active:
        return (80, 120, 80)
    return _clock_col(secs)


# ---------------------------------------------------------------------------
# Control bar  (always visible, at the bottom)
# ---------------------------------------------------------------------------
# Constant rects — left cluster
_r_new  = pygame.Rect(10,  CTRL_Y + 9, 100, 34)
_r_cfg  = pygame.Rect(118, CTRL_Y + 9,  80, 34)
_r_undo = pygame.Rect(206, CTRL_Y + 9,  80, 34)
# Right cluster (AI vs AI controls — right-aligned)
_r_back  = pygame.Rect(462, CTRL_Y + 9,  90, 34)
_r_pause = pygame.Rect(560, CTRL_Y + 9, 132, 34)
_r_step  = pygame.Rect(700, CTRL_Y + 9,  90, 34)


def _draw_ctrl_bar(surface: pygame.Surface, paused: bool) -> None:
    pygame.draw.rect(surface, (22, 22, 30), pygame.Rect(0, CTRL_Y, WIN_W, CTRL_H))

    _filled_btn(surface, "New  [R]",     _r_new,  (80, 42, 42))
    _filled_btn(surface, "⚙ Settings",  _r_cfg,  (42, 55, 80))
    _filled_btn(surface, "Undo  [Z]",   _r_undo, (42, 65, 75))

    if _both_ai():
        play_col = (40, 130, 40) if paused else (140, 40, 40)
        play_lbl = "▶ Play  [Spc]" if paused else "⏸ Pause [Spc]"
        _filled_btn(surface, "◀ Back  [←]", _r_back,  (44, 44, 120))
        _filled_btn(surface, play_lbl,       _r_pause, play_col)
        _filled_btn(surface, "Step ▶  [→]", _r_step,  (44, 44, 120))


# ---------------------------------------------------------------------------
# Game-over overlay
# ---------------------------------------------------------------------------
def _draw_game_over(surface: pygame.Surface) -> None:
    dim = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150))
    surface.blit(dim, (0, 0))

    cx = BOARD_PX // 2
    if board.winner:
        headline = f"{board.winner.capitalize()} wins!"
        hcol     = (255, 215, 0)
    else:
        headline = "Stalemate — Draw"
        hcol     = (210, 210, 210)

    txt  = _f(72).render(headline, True, hcol)
    hint = _f(32).render("R = new game  |  Z = undo", True, (180, 180, 180))
    surface.blit(txt,  txt.get_rect(center=(cx, BOARD_PX // 2 - 26)))
    surface.blit(hint, hint.get_rect(center=(cx, BOARD_PX // 2 + 38)))


# ---------------------------------------------------------------------------
# Window caption
# ---------------------------------------------------------------------------
def _update_caption(thinking: bool) -> None:
    if board.game_over:
        res = f"{board.winner.capitalize()} wins!" if board.winner else "Draw"
        pygame.display.set_caption(f"Chess — {res}  (R = new game)")
        return
    agent  = current_agent()
    who    = f"{board.turn.capitalize()} ({_agent_label(agent)})"
    suffix = " — thinking…" if thinking else "'s turn"
    check  = "  [CHECK]" if board.in_check else ""
    pygame.display.set_caption(f"Chess — {who}{suffix}{check}")


# ---------------------------------------------------------------------------
# Main loop state
# ---------------------------------------------------------------------------
_paused         = _both_ai()
_step_requested = False
_in_config      = True           # always open config on launch

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
running = True
while running:
    dt = clock.tick(60) / 1000.0       # seconds elapsed this frame

    # ── Events ───────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if _in_config:
                if event.key == pygame.K_RETURN:
                    _apply_config()
            else:
                if event.key == pygame.K_r:
                    _open_config()
                elif event.key == pygame.K_s:
                    _open_config()
                elif event.key == pygame.K_z:
                    _undo()
                    if _both_ai():
                        _paused         = True
                        _step_requested = False
                if _both_ai() and not _in_config:
                    if event.key == pygame.K_SPACE:
                        _paused = not _paused
                        if _paused:
                            _cancel_search()
                    elif event.key == pygame.K_RIGHT and _paused:
                        _step_requested = True
                    elif event.key == pygame.K_LEFT:
                        _undo()
                        _paused         = True
                        _step_requested = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()

            if _in_config:
                _config_click(mx, my)
                continue

            # Control bar
            if my >= CTRL_Y:
                if _r_new.collidepoint(mx, my):
                    _open_config()
                elif _r_cfg.collidepoint(mx, my):
                    _open_config()
                elif _r_undo.collidepoint(mx, my):
                    _undo()
                    if _both_ai():
                        _paused         = True
                        _step_requested = False
                elif _both_ai():
                    if _r_back.collidepoint(mx, my):
                        _undo()
                        _paused         = True
                        _step_requested = False
                    elif _r_pause.collidepoint(mx, my):
                        _paused = not _paused
                        if _paused:
                            _cancel_search()
                    elif _r_step.collidepoint(mx, my) and _paused:
                        _step_requested = True

            # Board — human moves only
            elif current_agent() is None and my < BOARD_PX:
                prev_last = board.last_move
                snap      = _snapshot()
                board.handle_click(mx, my)
                if board.last_move != prev_last:
                    _history.append(snap)

    if _in_config:
        board.draw(screen)
        _cfg_rects = _draw_config(screen)
        pygame.display.flip()
        continue

    # ── Human clock ──────────────────────────────────────────────────────────
    if (not board.game_over
            and current_agent() is None
            and _cfg["human_time"] > 0):
        _h_clocks[board.turn] = max(0.0, _h_clocks[board.turn] - dt)
        if _h_clocks[board.turn] == 0.0:
            board.game_over = True
            board.winner    = "black" if board.turn == "white" else "white"
            print(f"[Clock] {board.turn.capitalize()} ran out of time — "
                  f"{board.winner.capitalize()} wins!")

    # ── Agent logic ───────────────────────────────────────────────────────────
    agent = current_agent()
    if agent is not None and not board.game_over:
        active = not _both_ai() or (not _paused or _step_requested)

        if active:
            try:
                from_pos, to_pos = _move_queue.get_nowait()
                _history.append(_snapshot())
                _agent_thread   = None
                board._move(from_pos, to_pos)
                _step_requested = False
            except queue.Empty:
                if _agent_thread is None or not _agent_thread.is_alive():
                    _agent_thread = None
                    _start_search(agent)
        elif _agent_thread is not None:
            _cancel_search()

    # ── Render ────────────────────────────────────────────────────────────────
    thinking = _agent_thread is not None and _agent_thread.is_alive()
    board.draw(screen)
    if board.game_over:
        _draw_game_over(screen)
    _draw_info_bar(screen, thinking, len(_history))
    _draw_ctrl_bar(screen, _paused)
    _update_caption(thinking)
    pygame.display.flip()

pygame.quit()
