"""Game-setup modal: agent pickers per side, AI think-time, human clock, and
the Stockfish binary path field. Owns only the pending `cfg` dict — applying
it into a running game is GameController.new_game()'s job (called by
main.py once this modal reports "start").
"""

import os

import pygame

from agent_factory import AGENT_KINDS, AGENT_LABELS
from ui.widgets import centered, filled_btn, font

AI_TIMES     = [0.5, 1.0, 2.0, 5.0]
AI_TIME_LBLS = ["0.5 s", "1 s", "2 s", "5 s"]
H_TIMES      = [0, 60, 180, 300, 600]          # 0 = unlimited
H_TIME_LBLS  = ["∞", "1 min", "3 min", "5 min", "10 min"]


class ConfigModal:

    def __init__(self):
        self.cfg: dict = {
            "white":          "montecarlo",
            "black":          "minimax",
            "ai_time":        2.0,
            "human_time":     0,
            "stockfish_path": "",
        }
        self.sf_path_active = False   # True while the user is typing the SF path
        self.sf_error = ""            # non-empty when Stockfish failed to load
        self._rects: dict = {}
        self._sf_path_rect: pygame.Rect | None = None

    # -------------------------------------------------------------------------
    # Keyboard (Stockfish path text entry)
    # -------------------------------------------------------------------------

    def handle_key(self, event) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.sf_path_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.cfg["stockfish_path"] = self.cfg["stockfish_path"][:-1]
            self.sf_error = ""
        elif event.unicode and event.unicode.isprintable():
            self.cfg["stockfish_path"] += event.unicode
            self.sf_error = ""

    # -------------------------------------------------------------------------
    # Mouse
    # -------------------------------------------------------------------------

    def handle_click(self, mx: int, my: int) -> str | None:
        """Mutates self.cfg on option clicks. Returns "start" once the Start
        button is clicked, else None."""
        for key, rect in self._rects.items():
            if not rect.collidepoint(mx, my):
                continue
            if key == "sf_path":
                self.sf_path_active = True
                return None
            if key == "sf_browse":
                self.sf_path_active = False
                self._browse_stockfish()
                return None
            self.sf_path_active = False
            if key == "start":
                return "start"
            if "_" in key:
                prefix, _, val = key.partition("_")
                if prefix in ("white", "black"):
                    self.cfg[prefix] = val
                    self.sf_error = ""
                elif prefix == "ai":
                    self.cfg["ai_time"] = float(val)
                elif prefix == "ht":
                    self.cfg["human_time"] = int(val)
            return None
        self.sf_path_active = False   # clicked outside all rects
        return None

    def _browse_stockfish(self) -> None:
        """Open a native file-picker dialog and store the chosen path in cfg."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            current = self.cfg["stockfish_path"]
            initialdir = (os.path.dirname(current)
                          if current and os.path.isfile(current)
                          else os.path.expanduser("~"))
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            path = filedialog.askopenfilename(
                parent=root,
                title="Select Stockfish binary",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
                initialdir=initialdir,
            )
            root.destroy()
            if path:
                self.cfg["stockfish_path"] = path.replace("/", "\\")
                self.sf_error = ""
        except Exception as exc:
            print(f"[Browse] {exc}")

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------

    def draw(self, surface, win_w: int, win_h: int) -> None:
        dim = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))

        sf_selected = (self.cfg["white"] == "stockfish" or self.cfg["black"] == "stockfish")

        n = len(AGENT_KINDS)
        mw = 620
        sf_extra = (60 + (24 if self.sf_error else 0)) if sf_selected else 0
        mh = 88 + n * 42 + 170 + sf_extra + 60
        mx0 = (win_w - mw) // 2
        my0 = (win_h - mh) // 2
        pygame.draw.rect(surface, (28, 28, 40), (mx0, my0, mw, mh), border_radius=12)
        pygame.draw.rect(surface, (70, 70, 110), (mx0, my0, mw, mh), 2, border_radius=12)

        rects: dict = {}
        cx = mx0 + mw // 2

        centered(surface, "GAME SETUP", 36, (210, 210, 255), cx, my0 + 28)
        pygame.draw.line(surface, (60, 60, 90),
                         (mx0 + 20, my0 + 52), (mx0 + mw - 20, my0 + 52))

        agent_top = my0 + 88
        for side, col_cx in (("white", mx0 + 155), ("black", mx0 + 465)):
            label = "WHITE" if side == "white" else "BLACK"
            col = (230, 230, 230) if side == "white" else (160, 160, 160)
            centered(surface, label, 22, col, col_cx, my0 + 72)

            for i, kind in enumerate(AGENT_KINDS):
                r = pygame.Rect(col_cx - 70, agent_top + i * 42, 140, 34)
                sel = self.cfg[side] == kind
                bg = (50, 90, 50) if sel else (40, 40, 58)
                filled_btn(surface, AGENT_LABELS[kind], r, bg=bg, highlight=sel)
                rects[f"{side}_{kind}"] = r

        col_bot = agent_top + (n - 1) * 42 + 34
        pygame.draw.line(surface, (60, 60, 90), (cx, my0 + 60), (cx, col_bot + 4))

        sep1_y = col_bot + 14
        ai_lbl_y = sep1_y + 18
        ai_btn_y = ai_lbl_y + 16
        pygame.draw.line(surface, (60, 60, 90),
                         (mx0 + 20, sep1_y), (mx0 + mw - 20, sep1_y))
        centered(surface, "AI THINK TIME  (per move)", 21, (170, 170, 200), cx, ai_lbl_y)

        btn_w, gap = 86, 10
        row_w = len(AI_TIMES) * btn_w + (len(AI_TIMES) - 1) * gap
        row_x0 = cx - row_w // 2
        for i, (t, lbl) in enumerate(zip(AI_TIMES, AI_TIME_LBLS)):
            r = pygame.Rect(row_x0 + i * (btn_w + gap), ai_btn_y, btn_w, 32)
            sel = abs(self.cfg["ai_time"] - t) < 0.01
            filled_btn(surface, lbl, r, bg=(50, 90, 50) if sel else (40, 40, 58), highlight=sel)
            rects[f"ai_{t}"] = r

        sep2_y = ai_btn_y + 32 + 14
        clk_lbl_y = sep2_y + 18
        clk_btn_y = clk_lbl_y + 16
        pygame.draw.line(surface, (60, 60, 90),
                         (mx0 + 20, sep2_y), (mx0 + mw - 20, sep2_y))
        centered(surface, "HUMAN CLOCK  (per side, total game)", 21,
                 (170, 170, 200), cx, clk_lbl_y)

        btn_w, gap = 82, 8
        row_w = len(H_TIMES) * btn_w + (len(H_TIMES) - 1) * gap
        row_x0 = cx - row_w // 2
        for i, (t, lbl) in enumerate(zip(H_TIMES, H_TIME_LBLS)):
            r = pygame.Rect(row_x0 + i * (btn_w + gap), clk_btn_y, btn_w, 32)
            sel = self.cfg["human_time"] == t
            filled_btn(surface, lbl, r, bg=(50, 90, 50) if sel else (40, 40, 58), highlight=sel)
            rects[f"ht_{t}"] = r

        if sf_selected:
            sf_sep_y = clk_btn_y + 32 + 10
            sf_lbl_y = sf_sep_y + 18
            sf_inp_top = sf_lbl_y + 14
            pygame.draw.line(surface, (60, 60, 90),
                             (mx0 + 20, sf_sep_y), (mx0 + mw - 20, sf_sep_y))
            centered(surface, "Stockfish binary path", 21, (170, 170, 200), cx, sf_lbl_y)

            browse_rect = pygame.Rect(mx0 + mw - 20 - 88, sf_inp_top, 88, 30)
            sf_rect = pygame.Rect(mx0 + 20, sf_inp_top, mw - 40 - 88 - 8, 30)
            self._sf_path_rect = sf_rect

            border_col = (120, 160, 220) if self.sf_path_active else (70, 70, 110)
            pygame.draw.rect(surface, (18, 18, 28), sf_rect, border_radius=4)
            pygame.draw.rect(surface, border_col, sf_rect, 2, border_radius=4)
            filled_btn(surface, "Browse…", browse_rect, bg=(50, 60, 90), fsize=18)
            rects["sf_browse"] = browse_rect

            path = self.cfg["stockfish_path"]
            if path:
                txt_surf = font(18).render(path, True, (200, 200, 220))
                clip_w = sf_rect.width - 12
                ty = sf_rect.centery - txt_surf.get_height() // 2
                if txt_surf.get_width() > clip_w:
                    src_x = txt_surf.get_width() - clip_w
                    surface.blit(txt_surf, (sf_rect.x + 6, ty),
                                 (src_x, 0, clip_w, txt_surf.get_height()))
                    cursor_x = sf_rect.right - 6
                else:
                    surface.blit(txt_surf, (sf_rect.x + 6, ty))
                    cursor_x = sf_rect.x + 6 + txt_surf.get_width()
                if self.sf_path_active and pygame.time.get_ticks() // 500 % 2 == 0:
                    pygame.draw.line(surface, (200, 200, 220),
                                     (cursor_x, sf_rect.y + 5),
                                     (cursor_x, sf_rect.bottom - 5), 2)
            else:
                if self.sf_path_active:
                    if pygame.time.get_ticks() // 500 % 2 == 0:
                        pygame.draw.line(surface, (200, 200, 220),
                                         (sf_rect.x + 8, sf_rect.y + 5),
                                         (sf_rect.x + 8, sf_rect.bottom - 5), 2)
                else:
                    ph = font(18).render("Leave blank to auto-detect", True, (75, 75, 100))
                    surface.blit(ph, (sf_rect.x + 6, sf_rect.centery - ph.get_height() // 2))

            if self.sf_error:
                err = font(16).render(self.sf_error, True, (220, 80, 80))
                surface.blit(err, err.get_rect(center=(cx, sf_rect.bottom + 12)))

            rects["sf_path"] = sf_rect
        else:
            self._sf_path_rect = None

        start_r = pygame.Rect(cx - 110, my0 + mh - 52, 220, 40)
        pygame.draw.rect(surface, (36, 120, 56), start_r, border_radius=8)
        pygame.draw.rect(surface, (70, 190, 90), start_r, 2, border_radius=8)
        centered(surface, "START GAME", 26, (255, 255, 255), start_r.centerx, start_r.centery)
        rects["start"] = start_r

        self._rects = rects
