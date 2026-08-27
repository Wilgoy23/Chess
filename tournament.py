"""Headless tournament runner — plays N games between two agents with no
pygame window, parallel across worker processes.

    python -m tournament --white minimax --black montecarlo --games 100 --time 0.5 --seed 42

Everything this module touches (fen.py, rules.py, agent_factory.py) is free
of pygame, so it runs the same on a display-less machine as it does here.
Each game is played directly against rules.py/fen.py rather than through
GameState, since that avoids any dataclass/logging overhead in a loop that
may run thousands of times across a tournament.
"""

import argparse
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import fen
import rules
from agent_factory import AGENT_KINDS, make_agent

# Adjudicated as a draw beyond this many plies — bounds worst-case game
# length for agents (e.g. two weak ones) that might otherwise shuffle forever
# without tripping fifty-move/repetition detection in a reasonable time.
MAX_PLIES_DEFAULT = 300

_TOURNAMENT_KINDS = [k for k in AGENT_KINDS if k != "human"]


def play_game(white_kind: str, black_kind: str, ai_time: float = 0.5,
              seed: int = 0, max_plies: int = MAX_PLIES_DEFAULT,
              stockfish_path: str | None = None) -> dict:
    """Play one game to completion (or to max_plies) and return a result:
    {white, black, winner, draw_reason, plies, seconds}.
    winner is "white", "black", or None (draw, or adjudicated at max_plies).
    """
    random.seed(seed)

    pos = fen.parse_fen(fen.START_FEN)
    grid, turn = pos.grid, pos.turn
    castling_rights, en_passant_target = pos.castling_rights, pos.en_passant_target
    halfmove_clock = 0
    position_counts = {rules.position_key(grid, turn, castling_rights, en_passant_target): 1}

    agents = {
        "white": make_agent(white_kind, "white", ai_time, stockfish_path),
        "black": make_agent(black_kind, "black", ai_time, stockfish_path),
    }

    start = time.perf_counter()
    winner = None
    draw_reason = None
    plies = 0

    while True:
        result = rules.get_game_result(grid, turn, castling_rights, en_passant_target,
                                        halfmove_clock, position_counts)
        if result is not None:
            if result == "checkmate":
                winner = "black" if turn == "white" else "white"
            else:
                draw_reason = result
            break
        if plies >= max_plies:
            draw_reason = "move_limit"
            break

        move = agents[turn].get_move(grid, turn, castling_rights, en_passant_target)
        if move is None:
            draw_reason = "no_move"
            break
        from_pos, to_pos = move

        grid, castling_rights, en_passant_target, is_irreversible = rules.apply_move(
            grid, from_pos, to_pos, castling_rights, en_passant_target)
        halfmove_clock = 0 if is_irreversible else halfmove_clock + 1
        turn = "black" if turn == "white" else "white"
        plies += 1

        key = rules.position_key(grid, turn, castling_rights, en_passant_target)
        position_counts[key] = position_counts.get(key, 0) + 1

    return {
        "white": white_kind, "black": black_kind,
        "winner": winner, "draw_reason": draw_reason,
        "plies": plies, "seconds": time.perf_counter() - start,
    }


def _run_one(job: tuple) -> dict:
    white_kind, black_kind, ai_time, seed, max_plies, stockfish_path = job
    return play_game(white_kind, black_kind, ai_time, seed, max_plies, stockfish_path)


def run_match(white_kind: str, black_kind: str, games: int, ai_time: float, seed: int,
              max_plies: int = MAX_PLIES_DEFAULT, workers: int = 1,
              stockfish_path: str | None = None) -> list:
    """Play `games` games, each with a distinct seed (seed + game index) so a
    run is reproducible. Runs sequentially if workers <= 1, else spreads
    games across a process pool."""
    jobs = [(white_kind, black_kind, ai_time, seed + i, max_plies, stockfish_path)
            for i in range(games)]

    if workers <= 1:
        return [_run_one(job) for job in jobs]

    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one, job) for job in jobs]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def summarize(results: list) -> str:
    n = len(results)
    if n == 0:
        return "No games played."

    white_wins = sum(1 for r in results if r["winner"] == "white")
    black_wins = sum(1 for r in results if r["winner"] == "black")
    draws = n - white_wins - black_wins
    total_plies = sum(r["plies"] for r in results)
    total_seconds = sum(r["seconds"] for r in results)
    pct = lambda x: f"{100 * x / n:.1f}%"

    return "\n".join([
        f"White: {results[0]['white']}   Black: {results[0]['black']}   Games: {n}",
        f"White wins: {white_wins} ({pct(white_wins)})   "
        f"Black wins: {black_wins} ({pct(black_wins)})   "
        f"Draws: {draws} ({pct(draws)})",
        f"Avg game length: {total_plies / n:.1f} plies",
        f"Total agent time: {total_seconds:.1f}s  (avg {total_seconds / n:.2f}s/game)",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless agent-vs-agent tournament runner")
    parser.add_argument("--white", required=True, choices=_TOURNAMENT_KINDS)
    parser.add_argument("--black", required=True, choices=_TOURNAMENT_KINDS)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--time", type=float, default=0.5, dest="ai_time",
                        help="per-move think time in seconds, for time-limited agents (default: 0.5)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-plies", type=int, default=MAX_PLIES_DEFAULT,
                        help=f"adjudicate as a draw beyond this many plies (default: {MAX_PLIES_DEFAULT})")
    parser.add_argument("--workers", type=int, default=None,
                        help="parallel worker processes (default: min(games, cpu count))")
    parser.add_argument("--stockfish-path", default=None)
    args = parser.parse_args()

    workers = args.workers or max(1, min(args.games, os.cpu_count() or 1))

    wall_start = time.perf_counter()
    results = run_match(args.white, args.black, args.games, args.ai_time, args.seed,
                        args.max_plies, workers, args.stockfish_path)
    wall = time.perf_counter() - wall_start

    print(summarize(results))
    print(f"Wall time: {wall:.1f}s ({workers} worker{'s' if workers != 1 else ''})")


if __name__ == "__main__":
    main()
