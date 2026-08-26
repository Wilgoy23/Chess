"""Small drawing helpers shared across the ui/ modules: a lazy per-size font
cache (keyed off the probed UI font name) plus a couple of common draw calls.
"""

import pygame

_fonts: dict[int, "pygame.font.Font"] = {}
_ui_font_name: str | None = None


def set_ui_font(name: str | None) -> None:
    """Set the font family used by font(); call once after find_ui_font()."""
    global _ui_font_name, _fonts
    _ui_font_name = name
    _fonts = {}


def font(size: int) -> "pygame.font.Font":
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont(_ui_font_name, size)
    return _fonts[size]


def filled_btn(surface, label: str, rect: pygame.Rect, bg: tuple,
                fg: tuple = (255, 255, 255), highlight: bool = False,
                fsize: int = 22) -> None:
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    if highlight:
        pygame.draw.rect(surface, (255, 210, 50), rect, 2, border_radius=6)
    txt = font(fsize).render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=rect.center))


def centered(surface, text: str, size: int, color: tuple, cx: int, cy: int) -> None:
    s = font(size).render(text, True, color)
    surface.blit(s, s.get_rect(center=(cx, cy)))
