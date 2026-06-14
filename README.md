# Chess

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
| `RandomAgent` | Uniform random legal move | Baseline |

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
├── main.py                  # Entry point, game loop, agent threading
├── board.py                 # Board state, rendering, move execution
├── rules.py                 # Central rules engine: move generation, check,
│                             #   move application, game-end conditions
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
│   ├── RandomAgent.py
│   └── StockfishAgent.py
└── pieces/                  # PNG piece images (wPawn.png, bRook.png, …)
```

## Requirements

- Python 3.10+
- [Pygame](https://www.pygame.org/) — `pip install pygame`

## Running

```bash
python main.py
```

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
        self.color = color

    def get_move(self, grid, color, castling_rights, en_passant_target=None):
        # grid              : 8x8 list of piece objects (or None)
        # castling_rights   : {"white": {"kingside": bool, "queenside": bool},
        #                       "black": {...}}
        # en_passant_target : (row, col) capturable en passant this move, or None
        # return: ((from_row, from_col), (to_row, to_col))
        return rules.get_legal_moves(grid, color, castling_rights, en_passant_target)[0]
```
