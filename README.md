# Chess

A In-Progress chess engine built in Python with Pygame. Supports human vs. human, human vs. AI, and AI vs. AI play with three interchangeable agent types.

## Features

- Complete chess rules: legal move generation, check/checkmate/stalemate detection, castling, and pawn promotion
- Visual highlighting: selected piece, valid move dots/rings, last-move tint, check indicator
- PNG piece images with Unicode fallback rendering
- Non-blocking AI via background threading — the board stays responsive while the engine thinks
- Console move log in algebraic notation

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

Standard MCTS loop: selection via UCT (C = 1.414), random expansion, random rollout capped at 50 half-moves, backpropagation. Rollouts respect 3-fold repetition (scored as a draw) and detect checkmate/stalemate. The best move is chosen by highest visit count.

## Project structure

```
Chess/
├── main.py                  # Entry point, game loop, agent threading
├── board.py                 # Board state, rendering, move execution
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
│   ├── chess_utils.py       # Shared move generation and check utilities
│   ├── MinimaxAgent.py
│   ├── MonteCarloAgent.py
│   └── RandomAgent.py
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

Edit the two lines near the top of [main.py](main.py):

```python
WHITE_PLAYER = MonteCarloAgent("white")
BLACK_PLAYER = MinimaxAgent("black")
```

| Value | Effect |
|---|---|
| `None` | Human player (mouse clicks) |
| `MinimaxAgent("color")` | Minimax AI |
| `MonteCarloAgent("color")` | MCTS AI |
| `RandomAgent("color")` | Random AI |

Examples:

```python
# Human vs Human
WHITE_PLAYER = None
BLACK_PLAYER = None

# Human (white) vs Minimax AI (black)
WHITE_PLAYER = None
BLACK_PLAYER = MinimaxAgent("black")

# AI vs AI
WHITE_PLAYER = MonteCarloAgent("white")
BLACK_PLAYER = MinimaxAgent("black")
```

## Extending

To add a new agent, subclass `AgentInterface` and implement `get_move(grid, color) -> tuple`:

```python
from Agents.AgentInterface import AgentInterface

class MyAgent(AgentInterface):
    def __init__(self, color):
        self.color = color

    def get_move(self, grid, color):
        # grid: 8x8 list of piece objects (or None)
        # return: ((from_row, from_col), (to_row, to_col))
        ...
```
