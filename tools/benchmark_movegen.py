"""Move-generation throughput benchmark (PRD 1.2).

Runs perft over a fixed set of representative positions/depths and reports
nodes/sec, so a before/after change to rules.py (square_attacked, make/unmake,
etc.) has a number to compare against. This is the number to record in a PR
description alongside the PRD's 10x target.

    python tools/benchmark_movegen.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fen import parse_fen, START_FEN
from perft import perft

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

# (label, FEN, depth) — depths chosen to each finish in a few seconds even
# at the pre-optimization baseline (~51k nodes/s).
CASES = [
    ("startpos", START_FEN, 4),
    ("kiwipete", KIWIPETE, 4),
]


def main():
    total_nodes = 0
    total_elapsed = 0.0

    for label, fen, depth in CASES:
        position = parse_fen(fen)
        start = time.perf_counter()
        nodes = perft(position, depth)
        elapsed = time.perf_counter() - start

        total_nodes += nodes
        total_elapsed += elapsed
        print(f"{label:10} perft({depth}) = {nodes:>8,} in {elapsed:6.2f}s "
              f"({nodes / elapsed:>13,.0f} nodes/s)")

    print(f"{'TOTAL':10} {'':>17} {total_elapsed:6.2f}s "
          f"({total_nodes / total_elapsed:>13,.0f} nodes/s)")


if __name__ == "__main__":
    main()
