# Chess

[![CI](https://github.com/Wilgoy23/Chess/actions/workflows/ci.yml/badge.svg)](https://github.com/Wilgoy23/Chess/actions/workflows/ci.yml)

A In-Progress chess engine built in Python with Pygame. Supports human vs. human, human vs. AI, and AI vs. AI play with three interchangeable agent types.

## Features

- Complete chess rules: legal move generation, check/checkmate/stalemate detection, castling, and pawn promotion
- Visual highlighting: selected piece, valid move dots/rings, last-move tint, check indicator
- PNG piece images with Unicode fallback rendering
- Non-blocking AI via background threading — the board stays responsive while the engine thinks
- Console move log in algebraic notation

### Rules implemented

- En passant capture
- Pawn promotion with a choice of Queen, Rook, Bishop, or Knight (human players pick via an on-board picker; AI agents always promote to Queen)
- Draw detection: fifty-move rule, threefold repetition, and insufficient material (in addition to stalemate)

## Agents

| Agent | Algorithm | Strength |
|---|---|---|
| `MinimaxAgent` | Alpha-beta minimax, depth 5, 2 s time limit | Strong |
| `MonteCarloAgent` | MCTS with UCT selection, 1000 simulations, 2 s time limit | Strong |
| `GreedyAgent` | One-ply material-capture maximizer, random tie-break | Weak |
| `RandomAgent` | Uniform random legal move | Baseline |

Agents cooperate with cancellation: `AgentInterface.stop()` sets a
`threading.Event` (`stop_event`) that Minimax/MCTS poll between search
iterations, and that StockfishAgent's override turns into a UCI `stop`
command — so pausing, undoing, or starting a new game while an agent is
thinking interrupts its worker thread instead of leaving it to finish
unseen.

### MinimaxAgent evaluation

The static evaluator combines:
- **Material** — standard piece values (P=1, N/B=3, R=5, Q=9)
- **Piece-square tables** — positional bonuses for all six piece types; king PST switches between midgame and endgame tables based on remaining heavy-piece material
- **Mobility** — normalized difference in legal move counts
- **King safety** — pawn/piece shield around each king
- **Pawn structure** — penalties for doubled and isolated pawns
- **Bishop pair bonus**
- **Endgame mating heuristic** — rewards pushing the opponent king to a corner and closing the kings' distance when ahead in material
- **Repetition penalty** — discourages returning to previously seen positions

### MonteCarloAgent

Standard MCTS loop: selection via UCT (C = 1.414), random expansion, capture-biased rollout capped at 20 half-moves, backpropagation. Rollouts prefer the most valuable capture over a random move (80% on the first ply, 50% after), respect 3-fold repetition (scored as a draw), and end in a graded score from the material balance, so every captured point shifts the result. Terminal nodes (checkmate/stalemate) are scored exactly. The best move is chosen by highest visit count (win rate as tie-break).

## Project structure

```
Chess/
├── main.py                  # Thin pygame entry point: window, event loop
├── game.py                  # GameController: state, history, clocks, agent
│                             #   threading — no rendering
├── game_state.py             # GameState: pure grid/turn/rights + move
│                             #   application, no pygame import
├── agent_factory.py          # Builds an agent instance from a kind string;
│                             #   shared by main.py and tournament.py
├── tournament.py             # Headless CLI: agent-vs-agent games, no pygame
│                             #   (python -m tournament ...)
├── rules.py                  # Central rules engine: move generation, check,
│                             #   move application, game-end conditions
├── fen.py                    # FEN parsing (also pygame-free)
├── ui/
│   ├── layout.py             # Window/board layout constants
│   ├── widgets.py            # Shared font cache + small draw helpers
│   ├── board_view.py         # Board rendering + click-to-move interaction
│   ├── config_modal.py       # Game-setup modal
│   └── bars.py                # Info bar, control bar, game-over overlay
├── Pieces/
│   ├── PieceInterface.py    # Abstract base class for all pieces
│   ├── Pawn.py
│   ├── Rook.py
│   ├── Knight.py
│   ├── Bishop.py
│   ├── Queen.py
│   └── King.py
├── Agents/
│   ├── AgentInterface.py    # Abstract base class for all agents
│   ├── MinimaxAgent.py
│   ├── MonteCarloAgent.py
│   ├── GreedyAgent.py
│   ├── RandomAgent.py
│   └── StockfishAgent.py
└── pieces/                  # PNG piece images (wPawn.png, bRook.png, …)
```

## Requirements

- Python 3.10+ (the codebase uses `X | None` type hints)
- [Pygame](https://www.pygame.org/)

## Running

```bash
pip install -r requirements.txt
python main.py
```

## Development

```bash
pip install -r requirements-dev.txt
python -m ruff check .   # lint
python -m pytest         # tests (perft's slow deep cases are skipped by default;
                          # pass --runslow or set PERFT_SLOW=1 to include them)
```

CI (`.github/workflows/ci.yml`) runs both on every push/PR against Python 3.10
and 3.13.

### Tournament (headless)

Play agents against each other with no pygame window, parallel across
worker processes:

```bash
python -m tournament --white random --black greedy --games 100 --time 0.5 --seed 42
```

`--white`/`--black` accept any agent kind except `human` (`random`, `greedy`,
`minimax`, `montecarlo`, `stockfish`). Prints W-D-L, average game length, and
total/wall time; `--workers` controls parallelism (default: one process per
game, up to the CPU count).

## Configuring players

Options are displayed on launch

| Value | Effect |
|---|---|
| `None` | Human player (mouse clicks) |
| `MinimaxAgent("color")` | Minimax AI |
| `MonteCarloAgent("color")` | MCTS AI |
| `RandomAgent("color")` | Random AI |


## Extending

To add a new agent, subclass `AgentInterface` and implement
`get_move(self, grid, color, castling_rights, en_passant_target=None) -> tuple`:

```python
from Agents.AgentInterface import AgentInterface
import rules

class MyAgent(AgentInterface):
    def __init__(self, color):
        super().__init__()   # sets up self.stop_event for cancellable search
        self.color = color

    def get_move(self, grid, color, castling_rights, en_passant_target=None):
        # grid              : 8x8 list of piece objects (or None)
        # castling_rights   : {"white": {"kingside": bool, "queenside": bool},
        #                       "black": {...}}
        # en_passant_target : (row, col) capturable en passant this move, or None
        # return: ((from_row, from_col), (to_row, to_col))
        return rules.get_legal_moves(grid, color, castling_rights, en_passant_target)[0]
```
