"""Entry point: pygame window/event loop, wiring GameController (game.py) to
the ui/ views. No game rules or agent-threading logic lives here — see
game.py for that and ui/ for rendering.
"""

import pygame

from game import GameController
from ui import bars, layout
from ui.board_view import BoardView
from ui.config_modal import ConfigModal
from ui.widgets import set_ui_font

pygame.init()
set_ui_font(layout.find_ui_font())

screen = pygame.display.set_mode((layout.WIN_W, layout.WIN_H))
pygame.display.set_caption("Chess")
clock = pygame.time.Clock()

controller   = GameController()
board_view   = BoardView(square_size=layout.SQUARE_SIZE)
config_modal = ConfigModal()

in_config = True   # always open config on launch


def _try_start() -> None:
    global in_config
    cfg = config_modal.cfg
    err = controller.new_game(
        cfg["white"], cfg["black"], cfg["ai_time"], cfg["human_time"],
        cfg["stockfish_path"] or None,
    )
    config_modal.sf_error = err or ""
    if err is None:
        in_config = False
        board_view.reset_selection()


def _open_config() -> None:
    global in_config
    controller.cancel_search()
    in_config = True


running = True
while running:
    dt = clock.tick(60) / 1000.0       # seconds elapsed this frame

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if in_config:
                if config_modal.sf_path_active:
                    config_modal.handle_key(event)
                elif event.key == pygame.K_RETURN:
                    _try_start()
            else:
                if event.key in (pygame.K_r, pygame.K_s):
                    _open_config()
                elif event.key == pygame.K_z:
                    controller.undo_action()
                    board_view.reset_selection()
                if controller.both_ai() and not in_config:
                    if event.key == pygame.K_SPACE:
                        controller.toggle_pause()
                    elif event.key == pygame.K_RIGHT:
                        controller.request_step()
                    elif event.key == pygame.K_LEFT:
                        controller.undo_action()
                        board_view.reset_selection()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()

            if in_config:
                if config_modal.handle_click(mx, my) == "start":
                    _try_start()
                continue

            if my >= layout.CTRL_Y:
                action = bars.ctrl_hit_test(mx, my, controller)
                if action in ("new", "cfg"):
                    _open_config()
                elif action in ("undo", "back"):
                    controller.undo_action()
                    board_view.reset_selection()
                elif action == "pause":
                    controller.toggle_pause()
                elif action == "step":
                    controller.request_step()
            elif controller.current_agent is None and my < layout.BOARD_PX:
                move = board_view.handle_click(mx, my, controller.state)
                if move is not None:
                    controller.play_move(*move)

    if in_config:
        board_view.draw(screen, controller.state)
        config_modal.draw(screen, layout.WIN_W, layout.WIN_H)
        pygame.display.flip()
        continue

    controller.tick_human_clock(dt)
    controller.tick_agent()

    thinking = controller.is_thinking()
    board_view.draw(screen, controller.state)
    if controller.state.game_over:
        bars.draw_game_over(screen, controller)
    bars.draw_info_bar(screen, controller, thinking)
    bars.draw_ctrl_bar(screen, controller, controller.paused)
    bars.update_caption(controller, thinking)
    pygame.display.flip()

pygame.quit()
