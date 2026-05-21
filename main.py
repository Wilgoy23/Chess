import copy
import queue
import threading

import pygame
from Agents.MinimaxAgent import MinimaxAgent
from Agents.MonteCarloAgent import MonteCarloAgent
from board import Board

# ---------------------------------------------------------------------------
# Player configuration
#   None            = human (mouse clicks)
#   MinimaxAgent    = alpha-beta minimax
#   MonteCarloAgent = Monte Carlo Tree Search
#   RandomAgent     = random legal move
# ---------------------------------------------------------------------------
WHITE_PLAYER = MonteCarloAgent("white")
BLACK_PLAYER = MinimaxAgent("black")

SQUARE_SIZE = 100
BOARD_PX    = SQUARE_SIZE * 8
CTRL_H      = 56

_both_ai = WHITE_PLAYER is not None and BLACK_PLAYER is not None
WIN_H    = BOARD_PX + (CTRL_H if _both_ai else 0)

pygame.init()
screen = pygame.display.set_mode((BOARD_PX, WIN_H))
pygame.display.set_caption("Chess")
clock = pygame.time.Clock()
board = Board(square_size=SQUARE_SIZE)


def current_agent():
    return WHITE_PLAYER if board.turn == "white" else BLACK_PLAYER


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
# History / undo  (works in every game mode)
#
# A snapshot is pushed before every move — AI or human.
# 'Z' pops the last snapshot and restores it.
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


def _undo() -> None:
    if not _history:
        return
    _cancel_search()
    _restore(_history.pop())


# ---------------------------------------------------------------------------
# New game
# ---------------------------------------------------------------------------
def _new_game() -> None:
    global board, WHITE_PLAYER, BLACK_PLAYER, _paused, _step_requested
    _cancel_search()
    board = Board(square_size=SQUARE_SIZE)
    # Recreate agents so internal state (position history etc.) resets cleanly
    if WHITE_PLAYER is not None:
        WHITE_PLAYER = type(WHITE_PLAYER)(WHITE_PLAYER.color)
    if BLACK_PLAYER is not None:
        BLACK_PLAYER = type(BLACK_PLAYER)(BLACK_PLAYER.color)
    _history.clear()
    _paused         = _both_ai
    _step_requested = False


# ---------------------------------------------------------------------------
# Window caption  (called once per frame after all state updates)
# ---------------------------------------------------------------------------
def _update_caption(thinking: bool = False) -> None:
    if board.game_over:
        result = f"{board.winner.capitalize()} wins!" if board.winner else "Draw"
        pygame.display.set_caption(f"Chess — {result}  (R = new game)")
        return
    agent  = current_agent()
    who    = f"{board.turn.capitalize()} ({_agent_label(agent)})"
    suffix = " — thinking…" if thinking else "'s turn"
    check  = "  [CHECK]" if board.in_check else ""
    pygame.display.set_caption(f"Chess — {who}{suffix}{check}")


# ---------------------------------------------------------------------------
# Game-over overlay
# ---------------------------------------------------------------------------
_ov_font_big: pygame.font.Font | None = None
_ov_font_med: pygame.font.Font | None = None


def _draw_game_over(surface: pygame.Surface) -> None:
    global _ov_font_big, _ov_font_med
    if _ov_font_big is None:
        _ov_font_big = pygame.font.SysFont(None, 72)
        _ov_font_med = pygame.font.SysFont(None, 36)

    overlay = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    cx = BOARD_PX // 2
    if board.winner:
        headline = f"{board.winner.capitalize()} wins!"
        hcol     = (255, 215, 0)
    else:
        headline = "Stalemate — Draw"
        hcol     = (210, 210, 210)

    txt  = _ov_font_big.render(headline, True, hcol)
    hint = _ov_font_med.render("Press  R  to play again  |  Z  to undo", True, (180, 180, 180))
    surface.blit(txt,  txt.get_rect(center=(cx, BOARD_PX // 2 - 26)))
    surface.blit(hint, hint.get_rect(center=(cx, BOARD_PX // 2 + 36)))


# ---------------------------------------------------------------------------
# Control bar  (AI vs AI only)
# ---------------------------------------------------------------------------
_ctrl_font: pygame.font.Font | None = None


def _ctrl_font_get() -> pygame.font.Font:
    global _ctrl_font
    if _ctrl_font is None:
        _ctrl_font = pygame.font.SysFont(None, 24)
    return _ctrl_font


def _draw_btn(surface: pygame.Surface, label: str,
              rect: pygame.Rect, color: tuple) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=6)
    txt = _ctrl_font_get().render(label, True, (255, 255, 255))
    surface.blit(txt, txt.get_rect(center=rect.center))


# Button rects are constant — build them once
_r_play = pygame.Rect(10,  BOARD_PX + 11, 136, 34)
_r_back = pygame.Rect(156, BOARD_PX + 11,  94, 34)
_r_step = pygame.Rect(258, BOARD_PX + 11,  94, 34)
_r_new  = pygame.Rect(360, BOARD_PX + 11,  80, 34)


def _draw_controls(surface: pygame.Surface, paused: bool, thinking: bool,
                   move_num: int) -> None:
    pygame.draw.rect(surface, (28, 28, 28), pygame.Rect(0, BOARD_PX, BOARD_PX, CTRL_H))

    play_col = (46, 148, 46) if paused else (160, 46, 46)
    play_lbl = "▶ Play  [Spc]" if paused else "⏸ Pause [Spc]"
    _draw_btn(surface, play_lbl,      _r_play, play_col)
    _draw_btn(surface, "◀ Back  [←]", _r_back, (56, 56, 140))
    _draw_btn(surface, "Step ▶  [→]", _r_step, (56, 56, 140))
    _draw_btn(surface, "New  [R]",    _r_new,  (90, 50, 50))

    font = _ctrl_font_get()
    w_lbl  = _agent_label(WHITE_PLAYER)
    b_lbl  = _agent_label(BLACK_PLAYER)
    status = "⏳ thinking…" if thinking else f"move {move_num}"
    info   = font.render(f"W: {w_lbl}   B: {b_lbl}   {status}", True, (160, 160, 160))
    surface.blit(info, (450, BOARD_PX + (CTRL_H - info.get_height()) // 2))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
_paused         = _both_ai
_step_requested = False

running = True
while running:

    # ── Events ───────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                _new_game()

            elif event.key == pygame.K_z:
                _undo()
                if _both_ai:
                    _paused         = True
                    _step_requested = False

            if _both_ai:
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
            if _both_ai and my >= BOARD_PX:
                if _r_play.collidepoint(mx, my):
                    _paused = not _paused
                    if _paused:
                        _cancel_search()
                elif _r_back.collidepoint(mx, my):
                    _undo()
                    _paused         = True
                    _step_requested = False
                elif _r_step.collidepoint(mx, my) and _paused:
                    _step_requested = True
                elif _r_new.collidepoint(mx, my):
                    _new_game()
            elif current_agent() is None and my < BOARD_PX:
                # Snapshot before the click so 'Z' can undo human moves
                prev_last = board.last_move
                snap      = _snapshot()
                board.handle_click(mx, my)
                if board.last_move != prev_last:
                    _history.append(snap)

    # ── Agent logic ───────────────────────────────────────────────────────────
    agent = current_agent()
    if agent is not None and not board.game_over:
        active = not _both_ai or (not _paused or _step_requested)

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
    if _both_ai:
        _draw_controls(screen, _paused, thinking, len(_history))
    _update_caption(thinking)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
