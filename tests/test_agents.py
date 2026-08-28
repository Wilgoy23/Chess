"""2.1 acceptance: GreedyAgent plays a full legal game against RandomAgent.

Reuses tournament.play_game (the same headless game loop the tournament CLI
runs) so this exercises the real agent-vs-agent path instead of a
hand-rolled duplicate, and doubles as a light regression test for
tournament.py itself.
"""

from tournament import play_game

_DRAW_REASONS = {"stalemate", "fifty_move_rule", "threefold_repetition",
                 "insufficient_material", "move_limit", "no_move"}


def _assert_valid_result(result):
    assert result["winner"] in (None, "white", "black")
    if result["winner"] is None:
        assert result["draw_reason"] in _DRAW_REASONS


def test_greedy_vs_random_completes():
    _assert_valid_result(play_game("greedy", "random", ai_time=0.1, seed=1, max_plies=200))


def test_random_vs_greedy_completes():
    _assert_valid_result(play_game("random", "greedy", ai_time=0.1, seed=2, max_plies=200))
