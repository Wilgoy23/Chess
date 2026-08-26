"""Info strip, control strip, and game-over overlay — the always-visible
chrome below the board — plus the window-caption updater. All read from a
GameController; none mutate it (button clicks are dispatched by main.py,
which calls back into the controller)."""

import pygame

from ui.layout import BOARD_PX, CTRL_H, CTRL_Y, INFO_H, INFO_Y, WIN_W
from ui.widgets import centered, filled_btn, font

_DRAW_REASON_LABELS = {
    "stalemate":             "Stalemate — Draw",
    "fifty_move_rule":       "Fifty-move rule — Draw",
    "threefold_repetition":  "Threefold repetition — Draw",
    "insufficient_material": "Insufficient material — Draw",
}

# Control-bar button rects — left cluster
R_NEW  = pygame.Rect(10,  CTRL_Y + 9, 100, 34)
R_CFG  = pygame.Rect(118, CTRL_Y + 9,  80, 34)
R_UNDO = pygame.Rect(206, CTRL_Y + 9,  80, 34)
# Right cluster (AI vs AI controls — right-aligned)
R_BACK  = pygame.Rect(462, CTRL_Y + 9,  90, 34)
R_PAUSE = pygame.Rect(560, CTRL_Y + 9, 132, 34)
R_STEP  = pygame.Rect(700, CTRL_Y + 9,  90, 34)


def _fmt_clock(secs: float) -> str:
    if secs <= 0:
        return "0:00"
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def _clock_col(secs: float) -> tuple:
    if secs > 30: return (100, 210, 100)
    if secs > 10: return (220, 190, 60)
    return (220, 60, 60)


def _clock_color_active(secs: float, is_active: bool) -> tuple:
    if not is_active:
        return (80, 120, 80)
    return _clock_col(secs)


# -------------------------------------------------------------------------
# Info bar
# -------------------------------------------------------------------------

def draw_info_bar(surface, controller, thinking: bool) -> None:
    pygame.draw.rect(surface, (18, 18, 24), pygame.Rect(0, INFO_Y, WIN_W, INFO_H))

    unlimited = controller.human_time == 0
    state = controller.state

    for side, x_cx in (("white", WIN_W // 4), ("black", 3 * WIN_W // 4)):
        agent = controller.agent_for(side)
        name = controller.agent_label(agent)

        name_col = (220, 220, 220) if side == "white" else (160, 160, 160)
        centered(surface, f"{side.capitalize()} — {name}", 22, name_col, x_cx, INFO_Y + 16)

        is_active = (state.turn == side) and not state.game_over

        if agent is None:
            if unlimited:
                clk_str, clk_col = "∞", (100, 100, 120)
            else:
                remaining = controller.h_clocks[side]
                clk_str = _fmt_clock(remaining)
                clk_col = _clock_color_active(remaining, is_active)
            centered(surface, clk_str, 30, clk_col, x_cx, INFO_Y + 42)
        else:
            ai_str = f"{controller.ai_time:.4g} s / move"
            ai_col = (255, 200, 50) if (is_active and thinking) else (90, 90, 110)
            centered(surface, ai_str, 24, ai_col, x_cx, INFO_Y + 42)

    pygame.draw.line(surface, (40, 40, 55), (WIN_W // 2, INFO_Y + 8),
                     (WIN_W // 2, INFO_Y + INFO_H - 8))
    status = f"move {len(controller.history)}" if not thinking else "thinking…"
    centered(surface, status, 20, (100, 100, 130), WIN_W // 2, INFO_Y + INFO_H // 2)


# -------------------------------------------------------------------------
# Control bar
# -------------------------------------------------------------------------

def draw_ctrl_bar(surface, controller, paused: bool) -> None:
    pygame.draw.rect(surface, (22, 22, 30), pygame.Rect(0, CTRL_Y, WIN_W, CTRL_H))

    filled_btn(surface, "New  [R]",   R_NEW,  (80, 42, 42))
    filled_btn(surface, "⚙ Settings", R_CFG,  (42, 55, 80))
    filled_btn(surface, "Undo  [Z]",  R_UNDO, (42, 65, 75))

    if controller.both_ai():
        play_col = (40, 130, 40) if paused else (140, 40, 40)
        play_lbl = "▶ Play  [Spc]" if paused else "⏸ Pause [Spc]"
        filled_btn(surface, "◀ Back  [←]", R_BACK,  (44, 44, 120))
        filled_btn(surface, play_lbl,       R_PAUSE, play_col)
        filled_btn(surface, "Step ▶  [→]", R_STEP,  (44, 44, 120))


def ctrl_hit_test(mx: int, my: int, controller) -> str | None:
    """Return an action key for a control-bar click at (mx, my), or None."""
    if R_NEW.collidepoint(mx, my):
        return "new"
    if R_CFG.collidepoint(mx, my):
        return "cfg"
    if R_UNDO.collidepoint(mx, my):
        return "undo"
    if controller.both_ai():
        if R_BACK.collidepoint(mx, my):
            return "back"
        if R_PAUSE.collidepoint(mx, my):
            return "pause"
        if R_STEP.collidepoint(mx, my):
            return "step"
    return None


# -------------------------------------------------------------------------
# Game-over overlay
# -------------------------------------------------------------------------

def draw_game_over(surface, controller) -> None:
    state = controller.state
    dim = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150))
    surface.blit(dim, (0, 0))

    cx = BOARD_PX // 2
    if state.winner:
        headline = f"{state.winner.capitalize()} wins!"
        hcol = (255, 215, 0)
    else:
        headline = _DRAW_REASON_LABELS.get(state.draw_reason, "Draw")
        hcol = (210, 210, 210)

    txt = font(72).render(headline, True, hcol)
    hint = font(32).render("R = new game  |  Z = undo", True, (180, 180, 180))
    surface.blit(txt, txt.get_rect(center=(cx, BOARD_PX // 2 - 26)))
    surface.blit(hint, hint.get_rect(center=(cx, BOARD_PX // 2 + 38)))


# -------------------------------------------------------------------------
# Window caption
# -------------------------------------------------------------------------

def update_caption(controller, thinking: bool) -> None:
    state = controller.state
    if state.game_over:
        res = f"{state.winner.capitalize()} wins!" if state.winner else "Draw"
        pygame.display.set_caption(f"Chess — {res}  (R = new game)")
        return
    agent = controller.current_agent
    who = f"{state.turn.capitalize()} ({controller.agent_label(agent)})"
    suffix = " — thinking…" if thinking else "'s turn"
    check = "  [CHECK]" if state.in_check else ""
    pygame.display.set_caption(f"Chess — {who}{suffix}{check}")
