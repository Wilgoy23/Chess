"""1.3 acceptance: cancelling a search terminates the worker thread quickly.

Uses a fake agent that only returns once its stop_event is set, standing in
for a real search (Minimax/MCTS check the same event between iterations;
Stockfish's stop() sends UCI `stop` instead, since it's blocked on a
subprocess read rather than looping in Python).
"""

import time

from Agents.AgentInterface import AgentInterface
from game import GameController


class FakeSlowAgent(AgentInterface):
    """Polls stop_event every 5 ms, up to a 10 s safety cap, instead of
    actually searching — models a cooperative long-running agent."""

    def __init__(self, color):
        super().__init__()
        self.color = color

    def get_move(self, grid, color, castling_rights, en_passant_target=None):
        for _ in range(2000):
            if self.stop_event.wait(0.005):
                break
        return None


def test_cancel_search_terminates_quickly():
    controller = GameController()
    controller.white_agent = FakeSlowAgent("white")
    controller.black_agent = None

    controller.start_search()
    time.sleep(0.05)   # let the worker thread actually start and enter its poll loop
    assert controller.is_thinking()

    t0 = time.perf_counter()
    controller.cancel_search()
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.1
    assert not controller.is_thinking()
