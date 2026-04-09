import threading

import pygame
from board import Board
from Agents.minimax import MinimaxAgent

# -----------------------------------------------------------------------------
# Game mode — set your players here:
#   None         = human (uses mouse clicks)
#   MinimaxAgent = AI
#
# Examples:
#   Human vs Human:  WHITE_PLAYER = None,               BLACK_PLAYER = None
#   Human vs AI:     WHITE_PLAYER = None,               BLACK_PLAYER = MinimaxAgent("black")
#   AI vs Human:     WHITE_PLAYER = MinimaxAgent("white"), BLACK_PLAYER = None
#   AI vs AI:        WHITE_PLAYER = MinimaxAgent("white"), BLACK_PLAYER = MinimaxAgent("black")
# -----------------------------------------------------------------------------
WHITE_PLAYER = None
BLACK_PLAYER = MinimaxAgent("black", depth=3, time_limit=5.0)

SQUARE_SIZE = 100
WINDOW_SIZE = SQUARE_SIZE * 8  # 800x800

pygame.init()
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
pygame.display.set_caption("Chess")
clock = pygame.time.Clock()

board = Board(square_size=SQUARE_SIZE)


def current_agent():
    """Return the agent for whoever's turn it is, or None if it's a human."""
    if board.turn == "white":
        return WHITE_PLAYER
    return BLACK_PLAYER


# --- Agent threading state ---
_agent_thread = None
_pending_move  = None   # (from_pos, to_pos) written by background thread


def _run_agent(agent, grid, turn):
    global _pending_move
    move = agent.get_move(grid, turn)
    if move:
        _pending_move = move


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Only pass clicks to the board when it's a human's turn
        if event.type == pygame.MOUSEBUTTONDOWN and current_agent() is None:
            board.handle_click(*pygame.mouse.get_pos())

    # Agent turn: non-blocking search via background thread
    agent = current_agent()
    if agent is not None:
        if _pending_move is not None:           # search finished — apply move
            from_pos, to_pos = _pending_move
            _pending_move = None
            _agent_thread = None
            board._move(from_pos, to_pos)
        elif _agent_thread is None:             # idle — kick off search
            grid_copy = [row[:] for row in board.grid]
            _agent_thread = threading.Thread(
                target=_run_agent,
                args=(agent, grid_copy, board.turn),
                daemon=True,
            )
            _agent_thread.start()
        # else: search in progress — keep rendering

    board.draw(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
