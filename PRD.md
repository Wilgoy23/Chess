# PRD — Chess Engine Playground v2

**Owner:** Will Goyens
**Date:** 2026-07-19
**Status:** Draft

---

## 1. Vision

Turn this project from a working chess GUI with a few AIs into a **chess agent
laboratory**: a place to implement, compare, and benchmark search and learning
agents against each other and against Stockfish, with a polished UI for humans
to play and observe.

The product serves two personas:

1. **The builder (primary)** — implements new agents, wants fast iteration,
   objective strength measurement, and confidence the rules engine is correct.
2. **The player/observer** — plays against agents or watches AI-vs-AI games,
   wants a smooth, informative UI.

## 2. Current state (v1)

What works today:

- Complete rules: legal move generation, check/mate/stalemate, castling,
  en passant, promotion with picker, fifty-move / threefold / insufficient-material draws.
- Pygame UI: config modal, human clocks, AI think-time selection, pause/step/back
  controls for AI-vs-AI, undo, game-over overlay.
- Agents: Random, Minimax (alpha-beta + rich eval), MCTS (UCT + capture-biased
  rollouts), Stockfish (UCI wrapper with auto-detect + path picker).
- Non-blocking AI via background threads.

Known gaps and defects (drive the requirements below):

| # | Gap | Impact |
|---|-----|--------|
| G1 | `Agents/GreedyAgent.py`, `NegaScoutAgent.py`, `CNNAgent.py`, `OpeningBookAgent.py` are empty files | Planned agents don't exist; dead files in repo |
| G2 | `rules.square_attacked` scans all 64 squares and regenerates enemy moves; legality test deep-copies the grid per move | Move gen is the bottleneck; Minimax depth and MCTS sims are far below potential |
| G3 | No automated tests; no perft validation | Rule regressions are invisible; agent bugs indistinguishable from weakness |
| G4 | Search threads cannot be stopped (`_cancel_search` joins for 50 ms and abandons) | Wasted CPU after undo/pause/new-game; stale threads pile up |
| G5 | StockfishAgent sends FEN with hardcoded `0 1` clocks and drops the engine's promotion choice | Stockfish is blind to fifty-move/repetition; forced queen promotions |
| G6 | No headless mode / tournament runner | Comparing agents means watching games one at a time |
| G7 | No PGN export/import, no FEN setup, no in-app move list | Games can't be saved, analyzed, or resumed; console is the only record |
| G8 | Click-only movement, no board flip, no animations/sounds, fixed 800×912 window | Table-stakes UX gaps vs. any chess site |
| G9 | `main.py` is a 760-line monolith mixing game loop, UI widgets, config, threading | Hard to test or extend; every feature lands in one file |
| G10 | No `requirements.txt` / `pyproject.toml`, no CI; README says "three agent types" but ships five | Setup friction; docs drift |

## 3. Goals & non-goals

**Goals**

- G-A: Objective agent benchmarking (win rates, Elo estimates) with zero manual effort.
- G-B: Rules engine proven correct via perft; fast enough that search strength is
  limited by algorithms, not board representation.
- G-C: Ship the four placeholder agents.
- G-D: Bring the human-facing UI to parity with baseline chess-site expectations
  (drag, move list, flip, save/load).
- G-E: Codebase where a new agent or UI feature touches one module, covered by CI.

**Non-goals (this cycle)**

- Online/multiplayer play, engine-vs-engine over network.
- A full NN training pipeline (CNNAgent ships with a pre-trained or simple
  self-trained model; training infra is out of scope).
- Mobile/web ports.
- 3D rendering or themes beyond a light/dark board swap.

## 4. Requirements

### Epic 1 — Correctness & performance foundation (P0)

The prerequisite for everything else: you can't compare agents on a slow,
unverified rules engine.

**1.1 Perft test suite**
- Add `tests/test_perft.py` with standard positions (startpos, Kiwipete,
  positions 3–6 from the CPW perft page) validated to depth ≥ 4.
- Acceptance: all node counts match published values; suite runs in CI.

**1.2 Move-generation performance**
- Replace the O(64 × moves) `square_attacked` with directional ray/knight/pawn
  lookups from the target square (no enemy move generation).
- Make-unmake move application in the search path instead of grid deep-copies
  (agents may keep `apply_move` for the root).
- Target: ≥ 10× perft(4) throughput vs. current baseline (measure first, record
  the number in the PR).
- Acceptance: perft suite still passes; benchmark script committed under `tools/`.

**1.3 Cancellable search**
- `AgentInterface` gains an optional `stop()` / `stop_event` contract; Minimax
  checks it between iterative-deepening iterations, MCTS between simulations,
  Stockfish sends UCI `stop`.
- Acceptance: pressing Undo/Pause/New during AI thinking terminates the worker
  thread within 100 ms (assert via test with a fake slow agent).

**1.4 Stockfish fidelity**
- Pass real halfmove clock and fullmove number in the FEN; alternatively use
  `position startpos moves …` with full move history.
- Honor the engine's promotion piece.
- Acceptance: a scripted repetition position shows Stockfish avoiding/forcing
  the draw correctly; promotion to knight is possible.

### Epic 2 — Agent roadmap (P0/P1)

Fill the placeholder files, each conforming to `AgentInterface`, selectable in
the config modal, and covered by a smoke test (plays a full legal game vs Random).

**2.1 GreedyAgent (P0)** — one-ply material capture maximizer with random
tie-break. Purpose: a rung between Random and Minimax on the strength ladder.

**2.2 OpeningBookAgent (P1)** — wraps any inner agent; plays from a Polyglot
`.bin` book (or a small bundled JSON book) while in book, then delegates.
Config UI lets it wrap Minimax or MCTS.

**2.3 NegaScoutAgent (P1)** — principal-variation search with iterative
deepening, transposition table, and move ordering (TT move, MVV-LVA, killers).
Target: beats current MinimaxAgent ≥ 60% at equal time (measured via Epic 3).

**2.4 CNNAgent (P2)** — policy/value network evaluated at the leaves of a
shallow search or as MCTS prior. Ships with a small model trained from
self-play or public game data; inference must stay under the configured move
time on CPU. Depends on 2.x tournament harness for evaluation.

### Epic 3 — Tournament & benchmarking harness (P0)

**3.1 Headless runner** — `python -m tournament --white minimax --black mcts
--games 100 --time 0.5 --seed 42` runs games with no pygame window, parallel
across processes, and prints/saves W-D-L, average game length, and time usage.
- Board/rules must import without initializing pygame (this forces part of the
  Epic 4 refactor: no `pygame` import in `rules.py` or the core state class).

**3.2 Results & Elo** — results append to `results/*.jsonl`; a report command
computes pairwise win rates and Bayesian Elo estimates with error bars.
- Acceptance: README gains a strength-ladder table generated by the tool.

**3.3 Regression gate (P2)** — optional CI job: candidate agent vs. pinned
baseline, N fast games; flags strength regressions on agent PRs.

### Epic 4 — Architecture & project hygiene (P1)

**4.1 Split `main.py`** into `game.py` (GameController: state, history, clocks,
agent threading — no rendering), `ui/` (board view, config modal, info/control
bars), and a thin `main.py` entry point. Board state separates from Board
rendering (prerequisite for 3.1).

**4.2 Packaging & CI** — `pyproject.toml` (or `requirements.txt`) with pinned
deps; GitHub Actions running lint + tests on push; `.gitignore` covers
`__pycache__` (currently committed).

**4.3 README refresh** — accurate agent list, config-modal instructions,
tournament usage, strength ladder. Remove the stale "three agent types" text
and the obsolete "configuring players in code" table.

### Epic 5 — Player experience (P1/P2)

**5.1 Move list panel (P1)** — sidebar with numbered SAN moves; click to jump
to that position (read-only review; resuming from a past position truncates
forward history, with confirmation). Window widens to accommodate.

**5.2 Drag-and-drop (P1)** — drag pieces in addition to click-click; legal
targets shown on pickup; snap-back on illegal drop.

**5.3 PGN / FEN (P1)** — export finished/ongoing game to PGN (with headers:
players = agent labels, result, date); copy current FEN; start a game from a
pasted FEN (validated). Import PGN for replay (P2).

**5.4 Board flip (P2)** — flip orientation; auto-flip option when the human
plays black (currently human-as-black plays upside-down with no recourse).

**5.5 Sounds & animation (P2)** — move/capture/check sounds, ~100 ms move
animation, both toggleable.

**5.6 Eval bar (P2)** — live evaluation strip fed by the thinking agent's
score (Minimax/NegaScout eval, MCTS win rate, Stockfish cp). Off by default;
great for AI-vs-AI observation.

**5.7 Clock increments (P3)** — Fischer increment options for human clocks;
AI per-move time stays as-is.

## 5. Prioritized delivery plan

| Phase | Contents | Exit criterion |
|-------|----------|----------------|
| 1 | 1.1 perft, 1.2 perf, 4.2 packaging/CI | Perft green in CI; ≥10× movegen speedup recorded |
| 2 | 3.1 headless runner, 4.1 refactor, 1.3 cancel, 2.1 Greedy | 100-game Random-vs-Greedy tournament runs headless from CLI |
| 3 | 2.3 NegaScout, 3.2 Elo report, 1.4 Stockfish fidelity | Ladder table in README with error bars; NegaScout > Minimax at 60%+ |
| 4 | 5.1 move list, 5.2 drag, 5.3 PGN/FEN, 4.3 README | A human game can be played with drag input and exported as valid PGN |
| 5 | 2.2 book, 5.4–5.6 polish, 2.4 CNN, 3.3 gate | CNNAgent on the ladder; observer-mode polish shipped |

## 6. Success metrics

- Perft(5) from startpos completes in < 30 s on the dev machine (proxy for
  search speed; today it is not measurable in reasonable time).
- 100-game tournament between any two agents runs unattended in < 15 min at
  0.5 s/move.
- Strength ladder is strictly ordered: Random < Greedy < Minimax < NegaScout
  ≤ Stockfish, each gap statistically significant.
- New agent can be added and benchmarked touching only `Agents/` + one
  config-list entry.
- CI green on every commit to `main`.

## 7. Open questions

1. **CNNAgent scope** — train from self-play (slow, self-contained) or from
   public PGN data (faster, needs a data pipeline)? Decide before Phase 5.
2. **Board representation** — is 1.2's target achievable on the current
   object-grid, or is a mailbox/bitboard rewrite justified? Measure after the
   ray-lookup fix before committing to a rewrite.
3. **Window layout** — fixed wider window vs. resizable? Resizable pygame
   layouts are significant extra work; default assumption is a fixed ~1100×912.
4. **Python version floor** — code uses `X | None` syntax (3.10+); pin 3.10 or
   3.11+ in packaging?
