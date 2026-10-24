"""Game controller: manual play, level selection, solver runs and auto replay.

Owns gameplay flow only. It never touches Panda3D directly: the host injects
  * make_manager(board_data, snapshot) -> AnimationManager
  * load_visual_board(visual_board)    -> load into renderer + refit camera
  * hud                                 -> HudShell (update_view_model/bind_*)
Core (Board/BloxorzState) stays authoritative; animation only visualises it.
"""
from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.core.board import Board
from src.gui.animation_contracts import (
    AnimationEvent, AnimationKind, AnimationRequest, AnimationStatus,
    EventKind, TerminalVisualOutcome, as_visual_board,
)
from src.gui.animation_math import RollDirection
from src.gui.hud import HudViewModel
from src.gui.render_adapter import build_board_data, build_game_snapshot

# Core action -> visual roll. Board row 0 is the TOP of the screen (+Y world).
# If rolls fail with "does not match one physical 90-degree roll", swap U/D.
ACTION_TO_ROLL = {
    'U': RollDirection.UP, 'D': RollDirection.DOWN,
    'L': RollDirection.LEFT, 'R': RollDirection.RIGHT,
}
KEY_TO_ACTION = {
    'arrow_up': 'U', 'w': 'U', 'arrow_down': 'D', 's': 'D',
    'arrow_left': 'L', 'a': 'L', 'arrow_right': 'R', 'd': 'R',
}
# HUD button name -> (module, class). Adjust class names to the real solvers.
SOLVER_SPECS = {
    'BFS': ('src.solvers.bfs', 'BFSSolver'),
    'DFS': ('src.solvers.dfs', 'DFSSolver'),
    'IDS': ('src.solvers.ids', 'IDSSolver'),
    'UCS': ('src.solvers.UCS_Algorithm.ucs', 'UCSSolver'),
    'Greedy': ('src.solvers.greedy', 'GreedySolver'),
    'A*': ('src.solvers.astar', 'AStarSolver'),
}
SPEED_RANGE = (0.25, 4.0)


@dataclass(frozen=True)
class LevelEntry:
    level_id: str
    path: Path
    title: str


class LevelCatalog:
    """levels/*.json in natural order (level_2 before level_10)."""

    def __init__(self, directory='levels'):
        def natural(path):
            return [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', path.stem)]

        self.entries = []
        for path in sorted(Path(directory).glob('*.json'), key=natural):
            title = path.stem
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, dict) and isinstance(data.get('name'), str):
                    title = data['name']
            except (OSError, ValueError):
                pass
            self.entries.append(LevelEntry(path.stem, path, title))
        if not self.entries:
            raise FileNotFoundError(f'No level JSON files found in {directory!r}.')

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        return self.entries[index]


class Replay(Enum):
    IDLE = 'IDLE'
    PLAYING = 'PLAYING'
    PAUSED = 'PAUSED'


class GameController:
    MOVE_DURATION = 0.35
    TERMINAL_DURATION = 0.9

    def __init__(self, *, catalog, make_manager, load_visual_board, hud,
                 task_mgr=None, solver_specs=None, speed=1.0, on_event=None):
        self._catalog = catalog
        self._make_manager = make_manager
        self._load_visual_board = load_visual_board
        self._hud = hud
        self._task_mgr = task_mgr
        self._solver_specs = dict(SOLVER_SPECS if solver_specs is None else solver_specs)
        self.speed = min(max(speed, SPEED_RANGE[0]), SPEED_RANGE[1])
        self.board = self.board_data = self.manager = self.state = None
        self.level_index = 0
        self.session_id = ''
        self.revision = self.moves = 0
        self.phase = 'READY'          # READY | SOLVING | GOAL | FELL | ERROR
        self.search = None            # last SearchResult
        self.search_name = None
        self._actions, self._index, self._mode = (), 0, Replay.IDLE
        self._epoch = self._sessions = self._requests = 0
        self._deferred = None
        self._status = None           # transient HUD status override
        self._disposed = False
        self._on_event = on_event     # callable(name): roll | goal | fall | restart
        self.input_enabled = True     # False while a menu is on screen
        self.keyboard_enabled = True  # False when the player chose mouse control
        self.used_guide = False       # a solver ran in this attempt: no stars
        self.selected = None          # algorithm chosen in the HUD (not run yet)
        self.guide_active = False     # Play/Step pressed: guide mode is on

    # ------------------------------------------------------------ wiring
    def start(self, level_index=0):
        self._load_level(level_index)

    def bind_hud(self):
        # Exit / Restart / Guide belong to the menu flow (screens.UIFlow).
        actions = {'Play': self.toggle_play, 'Step': lambda: self.start_guide('step'),
                   'Close': self.cancel_guide}
        for name in self._solver_specs:
            actions[name] = lambda name=name: self.select_solver(name)
        for name, callback in actions.items():
            self._hud.bind_action(name, callback)
        self._hud.bind_speed(self.set_speed)

    def bind_keys(self, accept):
        """accept = DirectObject.accept (e.g. app.accept)."""
        for key, action in KEY_TO_ACTION.items():
            accept(key, self._key_move, [action])
        accept('r', self._gated, [self.restart_level])
        accept('enter', self._gated, [self.toggle_play])
        accept('p', self._gated, [self.toggle_play])

    def _key_move(self, action):
        if self.input_enabled and self.keyboard_enabled:
            self.manual_move(action)

    def _gated(self, command):
        if self.input_enabled:
            command()

    # ------------------------------------------------------------ session
    def _snapshot(self, revision=None):
        return build_game_snapshot(
            self.state, board_data=self.board_data, session_id=self.session_id,
            state_revision=self.revision if revision is None else revision)

    def _reset_state(self):
        """Fresh session; the epoch bump makes every pending callback stale."""
        self._epoch += 1
        self._sessions += 1
        self.session_id = f'play-{self._sessions}'
        self.state = self.board.get_initial_state()
        self.revision = self.moves = 0
        self.phase, self._status = 'READY', None
        self.used_guide = False
        self._index, self._mode = 0, Replay.IDLE
        return self._snapshot()

    def _reset_to_start(self, *, keep_solution):
        snapshot = self._reset_state()   # invalidates callbacks first
        self.manager.resync(snapshot)    # cancels any running request
        if not keep_solution:
            self._actions, self.search, self.search_name = (), None, None

    def _load_level(self, index):
        entry = self._catalog[index % len(self._catalog)]
        try:  # validate fully before touching the live scene
            board = Board(str(entry.path))
            board_data = build_board_data(board, level_id=entry.level_id)
        except (ValueError, TypeError, OSError) as error:
            self._status = f'LEVEL ERROR: {error}'
            self._refresh_hud()
            return False
        self._cancel_deferred()
        self._dispose_manager()
        self.board, self.board_data = board, board_data
        self.level_index = index % len(self._catalog)
        self._actions, self.search, self.search_name = (), None, None
        self.selected, self.guide_active = None, False
        snapshot = self._reset_state()
        self._load_visual_board(as_visual_board(board_data))
        self.manager = self._make_manager(board_data, snapshot)
        self.manager.set_playback_rate(self.speed)
        self._refresh_hud()
        return True

    def _dispose_manager(self):
        if self.manager is not None:
            self._epoch += 1
            self.manager.dispose()
            self.manager = None

    def _emit(self, name):
        if self._on_event is not None:
            self._on_event(name)

    def load_level(self, index):
        """Public entry for the level menu; False when the level cannot be shown."""
        return self._load_level(index)

    # ------------------------------------------------------------ game buttons
    def new_game(self):
        if self.phase != 'SOLVING':
            self._load_level(0)

    def restart_level(self):
        if self.phase != 'SOLVING':
            self._reset_to_start(keep_solution=False)
            self._refresh_hud()
            self._emit('restart')

    def select_level(self):
        """Cycle to the next level (simple Select Level)."""
        if self.phase != 'SOLVING':
            self._load_level(self.level_index + 1)

    # ------------------------------------------------------------ manual play
    def manual_move(self, action):
        if self.phase != 'READY' or self.manager is None:
            return
        if self._mode is not Replay.IDLE:
            self._status = 'Finish or hide the solution first'
            self._refresh_hud()
            return
        self._submit_move(action)

    def _next_request_id(self):
        self._requests += 1
        return f'req-{self._requests}'

    def _submit_move(self, action):
        if self.manager.is_busy or self.phase != 'READY':
            return False
        nxt = self.board.transition(self.state, action)
        if nxt is None:                      # illegal move: block falls off
            return self._begin_terminal(EventKind.FALL)
        after = build_game_snapshot(nxt, board_data=self.board_data,
                                    session_id=self.session_id,
                                    state_revision=self.revision + 1)
        request = AnimationRequest(
            1, self._next_request_id(), self._snapshot(), after,
            AnimationKind.ROLL, self.MOVE_DURATION, direction=ACTION_TO_ROLL[action])
        epoch = self._epoch
        accepted = self._safe_submit(request, lambda result: self._on_move_done(epoch, nxt, result))
        if accepted:
            self._emit('roll')
        return accepted

    def _begin_terminal(self, kind):
        request = AnimationRequest(
            1, self._next_request_id(), self._snapshot(), None, AnimationKind.TERMINAL,
            self.TERMINAL_DURATION, events=(AnimationEvent(kind),),
            terminal=TerminalVisualOutcome(kind))
        epoch = self._epoch
        return self._safe_submit(request, lambda result: self._on_terminal_done(epoch, kind, result))

    def _safe_submit(self, request, callback):
        try:
            self.manager.submit(request, callback)
        except (ValueError, TypeError, RuntimeError) as error:
            self._enter_error(str(error))
            return False
        return True

    def _on_move_done(self, epoch, nxt, result):
        if epoch != self._epoch:
            return
        if result.status is not AnimationStatus.COMPLETED:
            self._enter_error(result.error or result.status.value)
            return
        self.state, self.revision = nxt, result.to_state_revision
        self.moves += 1
        if self.board.is_goal(self.state):
            self._begin_terminal(EventKind.GOAL_COMPLETE)
        else:
            self._refresh_hud()
            self._continue_replay()

    def _on_terminal_done(self, epoch, kind, result):
        if epoch != self._epoch:
            return
        if result.status is not AnimationStatus.COMPLETED:
            self._enter_error(result.error or result.status.value)
            return
        self.phase = 'GOAL' if kind is EventKind.GOAL_COMPLETE else 'FELL'
        self._mode = Replay.IDLE
        self._refresh_hud()
        self._emit('goal' if kind is EventKind.GOAL_COMPLETE else 'fall')

    def _enter_error(self, message):
        self.phase, self._mode = 'ERROR', Replay.IDLE
        self._status = f'ERROR: {message}'
        self._refresh_hud()

    # ------------------------------------------------------------ solvers
    def run_solver(self, name, after='play'):
        if self.phase == 'SOLVING' or name not in self._solver_specs:
            return
        self._reset_to_start(keep_solution=False)
        self.used_guide = True
        self.phase = 'SOLVING'
        self._status = f'SOLVING {name}…'
        self._refresh_hud()
        self._defer(lambda: self._solve(name, after))  # let the HUD repaint first

    def _defer(self, fn):
        if self._task_mgr is None:
            fn()
            return

        def run(task):
            self._deferred = None
            fn()
            return task.done

        self._deferred = self._task_mgr.doMethodLater(0.05, run, 'ControllerSolve')

    def _cancel_deferred(self):
        if self._deferred is not None and self._task_mgr is not None:
            self._task_mgr.remove(self._deferred)
        self._deferred = None

    def _solve(self, name, after='play'):
        module, class_name = self._solver_specs[name]
        try:  # a solver bug must not kill the GUI
            solver = getattr(importlib.import_module(module), class_name)(self.board)
            result = solver.solve()
        except Exception as error:
            self.phase, self._status, self.guide_active = 'READY', f'{name} ERROR: {error}', False
            self._refresh_hud()
            return
        self.search, self.search_name = result, name
        self.phase = 'READY'
        if not result.success:
            self._status, self.guide_active = f'{name}: NO SOLUTION', False
            self._refresh_hud()
            return
        self._status = None
        self._actions, self._index, self._mode = tuple(result.actions), 0, Replay.IDLE
        self.step() if after == 'step' else self.play()

    # ------------------------------------------------------------ replay
    # ------------------------------------------------------------ guide flow
    def select_solver(self, name):
        """Only marks the algorithm; nothing runs until Play/Step."""
        if self.phase == 'SOLVING' or name not in self._solver_specs or self.manager is None:
            return False
        self.selected, self.guide_active = name, False
        self._reset_to_start(keep_solution=False)
        self._refresh_hud()
        return True

    def start_guide(self, mode):
        """mode: 'play' or 'step'. Solves first if this algorithm has not run yet."""
        if self.selected is None or self.phase in ('SOLVING', 'ERROR'):
            return
        self.guide_active = True
        if self._actions and self.search_name == self.selected:
            self.used_guide = True
            self.play() if mode == 'play' else self.step()
        else:
            self.run_solver(self.selected, after=mode)

    def toggle_play(self):
        if self._mode is Replay.PLAYING:
            self.pause()
        else:
            self.start_guide('play')

    def end_guide(self):
        """Solution finished: block returns to the start for the player."""
        if self.manager is None:
            return
        self._reset_to_start(keep_solution=False)
        self.selected, self.guide_active = None, False
        self.used_guide = True
        self._refresh_hud()

    def cancel_guide(self):
        """Hide Solution / leaving the level."""
        if self.manager is None or not (self.guide_active or self.selected):
            return
        guided = self.guide_active
        if self.phase == 'SOLVING':
            self._cancel_deferred()
            self.phase = 'READY'
        self._reset_to_start(keep_solution=False)
        self.selected, self.guide_active = None, False
        self.used_guide = guided
        self._refresh_hud()

    def _prepare_replay(self):
        """Return False if nothing can play; restart from start when out of sync."""
        if not self._actions or self.phase in ('SOLVING', 'ERROR'):
            return False
        out_of_sync = self._mode is Replay.IDLE and (
            self.moves != self._index or self._index >= len(self._actions)
            or self.phase in ('GOAL', 'FELL'))
        if out_of_sync:
            self._reset_to_start(keep_solution=True)
        return True

    def play(self):
        if not self._prepare_replay():
            return
        self._mode = Replay.PLAYING
        if self.manager.is_busy:
            self.manager.resume()
        else:
            self._replay_step()
        self._refresh_hud()

    def pause(self):
        if self._mode is Replay.PLAYING:
            self._mode = Replay.PAUSED
            if self.manager.is_busy:
                self.manager.pause()
            self._refresh_hud()

    def toggle_pause(self):
        self.pause() if self._mode is Replay.PLAYING else self.play()

    def step(self):
        """Advance exactly one solution move, then stay paused."""
        if self.manager is None or self.manager.is_busy or not self._prepare_replay():
            return
        if self._index >= len(self._actions):
            return
        self._mode = Replay.PAUSED
        self._replay_step()
        self._refresh_hud()

    def stop(self):
        if self.phase != 'SOLVING' and self.manager is not None:
            self._reset_to_start(keep_solution=True)
            self._refresh_hud()

    def _replay_step(self):
        if self._index >= len(self._actions):
            self._mode = Replay.IDLE
            return
        action = self._actions[self._index]
        self._index += 1
        self._submit_move(action)

    def _continue_replay(self):
        if self._mode is Replay.PLAYING:
            self._replay_step()

    # ------------------------------------------------------------ speed / HUD
    def set_speed(self, value):
        self.speed = min(max(float(value), SPEED_RANGE[0]), SPEED_RANGE[1])
        if self.manager is not None:
            self.manager.set_playback_rate(self.speed)

    def _status_text(self):
        if self._status:
            return self._status
        if self.phase == 'GOAL':
            return 'GOAL REACHED'
        if self.phase == 'FELL':
            return 'FELL — press R'
        if self._mode is Replay.PLAYING:
            return f'REPLAY {self.search_name} {self._index}/{len(self._actions)}'
        if self._mode is Replay.PAUSED:
            return f'PAUSED {self._index}/{len(self._actions)}'
        return 'READY'

    def _refresh_hud(self):
        result = self.search
        entry = self._catalog[self.level_index]
        self._hud.update_view_model(HudViewModel(
            level_label=f'{entry.title} ({self.level_index + 1}/{len(self._catalog)})',
            runtime_status=self._status_text(),
            move_count=self.moves,
            search_time_ms=None if result is None else result.time_taken * 1000,
            expanded_nodes=None if result is None else result.expanded_nodes,
            solution_length=result.solution_length if result is not None and result.success else None,
            peak_python_memory_bytes=None if result is None else round(result.peak_memory * 1024)))
        self._hud.set_playing(self.guide_active and self._mode is Replay.PLAYING)
        self._hud.set_guide_mode(self.guide_active)

    @property
    def is_idle(self):
        """Nothing animating, solving or replaying (attract mode may start a run)."""
        return (self.manager is not None and not self.manager.is_busy
                and self.phase != 'SOLVING' and self._mode is Replay.IDLE
                and self._deferred is None)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self._cancel_deferred()
        self._dispose_manager()