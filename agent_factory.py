"""Builds AgentInterface instances by kind name.

Shared by the interactive game (game.py) and the headless tournament runner
(tournament.py), so both agree on what agent kinds exist and how they're
constructed. StockfishAgent is imported lazily — its constructor spawns a
subprocess, which callers that never select "stockfish" shouldn't pay for.
"""

from Agents.GreedyAgent import GreedyAgent
from Agents.MinimaxAgent import MinimaxAgent
from Agents.MonteCarloAgent import MonteCarloAgent
from Agents.RandomAgent import RandomAgent

AGENT_KINDS = ["human", "random", "greedy", "minimax", "montecarlo", "stockfish"]
AGENT_LABELS = {
    "human":      "Human",
    "random":     "Random",
    "greedy":     "Greedy",
    "minimax":    "Minimax",
    "montecarlo": "MCTS",
    "stockfish":  "Stockfish",
}


def make_agent(kind: str, color: str, time_limit: float = 2.0,
                stockfish_path: str | None = None):
    """Return a new agent instance for `kind`, or None for "human".

    Raises ValueError for an unrecognized kind. A Stockfish binary that can't
    be found returns None (and prints why) rather than raising, matching how
    the config modal reports the failure inline instead of crashing.
    """
    if kind == "human":
        return None
    if kind == "random":
        return RandomAgent(color)
    if kind == "greedy":
        return GreedyAgent(color)
    if kind == "minimax":
        return MinimaxAgent(color, time_limit=time_limit)
    if kind == "montecarlo":
        return MonteCarloAgent(color, time_limit=time_limit)
    if kind == "stockfish":
        from Agents.StockfishAgent import StockfishAgent
        try:
            return StockfishAgent(color, time_limit=time_limit, stockfish_path=stockfish_path)
        except FileNotFoundError as exc:
            print(f"[Stockfish] {exc}")
            return None
    raise ValueError(f"unknown agent kind: {kind!r}")
