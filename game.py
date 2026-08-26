"""GameController: state, undo history, human clocks, and agent search
threading for one interactive game. No rendering — main.py owns the pygame
window and delegates to this class plus ui/board_view.py, ui/config_modal.py,
and ui/bars.py.
"""

import copy
import queue
import threading

from agent_factory import make_agent
from game_state import GameState


class GameController:

    def __init__(self):
        self.state = GameState()
        self.white_agent = None
        self.black_agent = None
        self.ai_time = 2.0
        self.human_time = 0            # seconds per side, 0 = unlimited
        self.h_clocks = {"white": 0.0, "black": 0.0}
        self.history: list[dict] = []
        self.last_log = ""
        self.paused = False
        self.step_requested = False

        self._move_queue = queue.Queue(maxsize=1)
        self._move_lock = threading.Lock()
        self._search_gen = 0
        self._agent_thread: threading.Thread | None = None
        self._searching_agent = None

    # -------------------------------------------------------------------------
    # Players
    # -------------------------------------------------------------------------

    def agent_for(self, color: str):
        return self.white_agent if color == "white" else self.black_agent

    @property
    def current_agent(self):
        return self.agent_for(self.state.turn)

    def both_ai(self) -> bool:
        return self.white_agent is not None and self.black_agent is not None

    @staticmethod
    def agent_label(agent) -> str:
        if agent is None:
            return "Human"
        return type(agent).__name__.replace("Agent", "")

    # -------------------------------------------------------------------------
    # New game / config
    # -------------------------------------------------------------------------

    def new_game(self, white_kind: str, black_kind: str, ai_time: float,
                 human_time: int, stockfish_path: str | None = None) -> str | None:
        """Build agents from config and reset state.

        Returns an error message if agent construction failed (e.g. the
        Stockfish binary wasn't found), in which case state is left as it was
        before the call — the caller should stay in its config screen.
        """
        white_agent = make_agent(white_kind, "white", ai_time, stockfish_path)
        black_agent = make_agent(black_kind, "black", ai_time, stockfish_path)
        sf_failed = ((white_kind == "stockfish" and white_agent is None) or
                     (black_kind == "stockfish" and black_agent is None))
        if sf_failed:
            return "Binary not found — enter the full path to stockfish.exe above"

        self.cancel_search()
        self.state = GameState()
        self.white_agent = white_agent
        self.black_agent = black_agent
        self.ai_time = ai_time
        self.human_time = human_time
        self.h_clocks = {"white": float(human_time), "black": float(human_time)}
        self.history.clear()
        self.last_log = ""
        self.paused = self.both_ai()
        self.step_requested = False
        return None

    # -------------------------------------------------------------------------
    # Moves / undo
    # -------------------------------------------------------------------------

    def play_move(self, from_pos: tuple, to_pos: tuple, promotion: str | None = None) -> None:
        self.history.append(self._snapshot())
        result = self.state.make_move(from_pos, to_pos, promotion=promotion)
        self.last_log = result.move_log()
        print(self.last_log)

    def _snapshot(self) -> dict:
        snap = self.state.snapshot()
        snap["clocks"] = dict(self.h_clocks)
        return snap

    def _restore(self, snap: dict) -> None:
        clocks = snap.pop("clocks")
        self.state.restore(snap)
        self.h_clocks.update(clocks)

    def undo(self) -> None:
        if not self.history:
            return
        self.cancel_search()
        self._restore(self.history.pop())

    def undo_action(self) -> None:
        """Undo triggered from a UI control (Undo/Back button, Z/Left key):
        also re-pauses AI-vs-AI play so it doesn't immediately resume."""
        self.undo()
        if self.both_ai():
            self.paused = True
            self.step_requested = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            self.cancel_search()

    def request_step(self) -> None:
        if self.paused:
            self.step_requested = True

    # -------------------------------------------------------------------------
    # Human clock
    # -------------------------------------------------------------------------

    def tick_human_clock(self, dt: float) -> None:
        if self.state.game_over or self.current_agent is not None or self.human_time <= 0:
            return
        side = self.state.turn
        self.h_clocks[side] = max(0.0, self.h_clocks[side] - dt)
        if self.h_clocks[side] == 0.0:
            self.state.game_over = True
            self.state.winner = "black" if side == "white" else "white"
            print(f"[Clock] {side.capitalize()} ran out of time — "
                  f"{self.state.winner.capitalize()} wins!")

    # -------------------------------------------------------------------------
    # Agent search threading
    # -------------------------------------------------------------------------

    def _run_agent(self, agent, grid, turn, castling_rights, en_passant_target, gen) -> None:
        move = agent.get_move(grid, turn, castling_rights, en_passant_target)
        if move:
            with self._move_lock:
                if gen == self._search_gen:
                    try:
                        self._move_queue.put_nowait(move)
                    except queue.Full:
                        pass

    def start_search(self) -> None:
        agent = self.current_agent
        if agent is None or self._agent_thread is not None:
            return
        agent.stop_event.clear()
        self._searching_agent = agent
        self._agent_thread = threading.Thread(
            target=self._run_agent,
            args=(agent, [row[:] for row in self.state.grid], self.state.turn,
                  copy.deepcopy(self.state.castling_rights), self.state.en_passant_target,
                  self._search_gen),
            daemon=True,
        )
        self._agent_thread.start()

    def poll_search(self) -> bool:
        """Apply a completed agent move if one is ready. Returns True if a
        move was applied."""
        try:
            from_pos, to_pos = self._move_queue.get_nowait()
        except queue.Empty:
            return False
        self._agent_thread = None
        self._searching_agent = None
        self.play_move(from_pos, to_pos)
        return True

    def is_thinking(self) -> bool:
        return self._agent_thread is not None and self._agent_thread.is_alive()

    def cancel_search(self) -> None:
        """Stop any in-progress search and block until its thread exits.

        Bumps the generation counter first so a move that sneaks into the
        queue between the stop signal and thread exit is still discarded by
        _run_agent's own generation check.
        """
        with self._move_lock:
            self._search_gen += 1
            while not self._move_queue.empty():
                try:
                    self._move_queue.get_nowait()
                except queue.Empty:
                    break
        if self._searching_agent is not None:
            self._searching_agent.stop()
        if self._agent_thread is not None:
            self._agent_thread.join(timeout=1.0)
        self._agent_thread = None
        self._searching_agent = None

    def tick_agent(self) -> None:
        """Drive the current agent's search: apply a finished move, start a
        new search, or cancel one if AI-vs-AI play is paused."""
        agent = self.current_agent
        if agent is None or self.state.game_over:
            return

        active = not self.both_ai() or (not self.paused or self.step_requested)
        if active:
            if self.poll_search():
                self.step_requested = False
                return
            if self._agent_thread is None or not self._agent_thread.is_alive():
                self._agent_thread = None
                self.start_search()
        elif self._agent_thread is not None:
            self.cancel_search()
