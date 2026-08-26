"""Shared pygame window/board layout constants."""

import pygame

SQUARE_SIZE = 100
BOARD_PX    = SQUARE_SIZE * 8           # 800 — board play area
INFO_H      = 60                         # player / clock strip below board
CTRL_H      = 52                         # button strip at bottom
WIN_W       = BOARD_PX
WIN_H       = BOARD_PX + INFO_H + CTRL_H   # 912

INFO_Y = BOARD_PX                        # y-origin of info strip
CTRL_Y = BOARD_PX + INFO_H               # y-origin of control strip


def find_ui_font() -> str | None:
    """Probe for a Unicode-capable font. Must run after pygame.init() — the
    default SysFont(None) uses Arial on Windows, which lacks the block/symbol
    glyphs (▶ ⏸ ◀ ⚙) the control bar renders. Segoe UI Symbol ships with
    every Windows 10/11 install and covers all the characters used here."""
    for candidate in ["segoeuisymbol", "segoe ui symbol", "Arial Unicode MS",
                      "dejavusans", "freesans", "notosans"]:
        try:
            probe = pygame.font.SysFont(candidate, 20)
            surf = probe.render("▶⏸◀⚙", True, (255, 255, 255))
            if surf.get_width() > 16:      # each glyph must have at least 4 px
                return candidate
        except Exception:
            pass
    return None
