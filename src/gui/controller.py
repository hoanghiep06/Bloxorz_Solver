"""Main-thread gameplay orchestration; Core owns rules, visual phases own no rules."""
from __future__ import annotations
import importlib
import json
import math
import re
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from src.core.board import Board
from src.gui.action_plan import plan_action, DIRECTIONS
from src.gui.animation_contracts import (
    AnimationEvent, AnimationKind, AnimationRequest, AnimationStatus,
    EventKind, TerminalVisualOutcome, validate_request,
)
from src.gui.game_adapter import prepare_level, build_game_snapshot
from src.gui.hud import HudViewModel
from src.gui.solver_worker import SolverJob
ACTION_TO_ROLL = DIRECTIONS
KEY_TO_ACTION = {
    'arrow_up': 'U', 'w': 'U', 'arrow_down': 'D', 's': 'D',
    'arrow_left': 'L', 'a': 'L', 'arrow_right': 'R', 'd': 'R', 'space': 'SPACE',
}
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

    def __init__(self, directory='levels'):

        def natural(path):
            return [int(p) if p.isdigit() else p.lower() for p in re.split('(\\d+)', path.stem)]
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

    def __init__(self, *, catalog, hud, make_manager=None, load_visual_board=None,
                 prepare_scene=None, task_mgr=None, solver_specs=None, speed=1.0,
                 on_event=None, solver_job_factory=SolverJob):
        self._catalog, self._hud = (catalog, hud)
        self._make_manager, self._load_visual_board = (make_manager, load_visual_board)
        self._prepare_scene, self._scene = (prepare_scene, None)
        self._task_mgr, self._job_factory = (task_mgr, solver_job_factory)
        self._solver_specs = dict(SOLVER_SPECS if solver_specs is None else solver_specs)
        self.speed = min(max(float(speed), SPEED_RANGE[0]), SPEED_RANGE[1])
        self.board = self.board_data = self.manager = self.state = None
        self.level_index = 0
        self.session_id = ''
        self.revision = self.moves = 0
        self.phase = 'READY'
        self.search = self.search_name = None
        self._actions, self._index, self._mode = ((), 0, Replay.IDLE)
        self._epoch = self._sessions = self._requests = 0
        self._deferred = self._job = self._job_task = None
        self._status = None
        self._disposed = False
        self._on_event = on_event
        self.input_enabled = self.keyboard_enabled = True
        self.used_guide = self.guide_active = False
        self.selected = None
        self._current_plan = None
        self._pending_requests = deque()

    def start(self, level_index=0):
        return self._load_level(level_index)

    def bind_hud(self):
        actions = {'Play': self.toggle_play, 'Step': lambda: self.start_guide('step'), 'Close': self.cancel_guide}
        for name in self._solver_specs:
            actions[name] = lambda name=name: self.select_solver(name)
        for name, callback in actions.items():
            self._hud.bind_action(name, callback)
        self._hud.bind_speed(self.set_speed)

    def bind_keys(self, accept):
        for key, action in KEY_TO_ACTION.items():
            accept(key, self._key_move, [action])
        accept('r', self._gated, [self.restart_level])
        accept('enter', self._gated, [self.toggle_play])
        accept('p', self._gated, [self.toggle_play])

    def _key_move(self, action):
        if self.input_enabled and (self.keyboard_enabled or action == 'SPACE'):
            self.manual_move(action)

    def _gated(self, command):
        if self.input_enabled:
            command()

    def _snapshot(self, revision=None):
        """Return the current visual phase; intermediate visual poses need not be committed Core states."""
        if revision is None and self.manager is not None:
            return self.manager.current_snapshot
        return build_game_snapshot(self.state, board_data=self.board_data, session_id=self.session_id, state_revision=self.revision if revision is None else revision)

    def _reset_state(self):
        self._epoch += 1
        self._sessions += 1
        self.session_id = f'play-{self._sessions}'
        self.state = self.board.get_initial_state()
        self.revision = self.moves = 0
        self.phase, self._status = ('READY', None)
        self.used_guide = False
        self._index, self._mode = (0, Replay.IDLE)
        self._current_plan = None
        self._pending_requests.clear()
        return build_game_snapshot(self.state, board_data=self.board_data, session_id=self.session_id, state_revision=0)

    def _reset_to_start(self, *, keep_solution, preserve_result=False):
        """Cancel pending computation before invalidating old animation callbacks."""
        self._cancel_deferred()
        snapshot = self._reset_state()
        self.manager.resync(snapshot)
        if not keep_solution:
            self._actions = ()
            if not preserve_result:
                self.search = self.search_name = None

    def _load_level(self, index):
        """Prepare the complete snapshot and hidden scene before replacing the live session."""
        index %= len(self._catalog)
        entry = self._catalog[index]
        new_scene = new_manager = None
        try:
            board = Board(str(entry.path))
            session = f'play-{self._sessions + 1}'
            data, initial, snapshot = prepare_level(board, level_id=entry.level_id, session_id=session)
            if self._prepare_scene is not None:
                new_scene = self._prepare_scene(data, snapshot)
                new_manager = new_scene.manager
                new_manager.set_playback_rate(self.speed)
                new_scene.activate()
            else:
                self._load_visual_board(data)
                new_manager = self._make_manager(data, snapshot)
                new_manager.set_playback_rate(self.speed)
        except Exception as error:
            if new_scene is not None:
                new_scene.dispose()
            elif new_manager is not None:
                new_manager.dispose()
            if self._scene is not None:
                self._scene.activate()
            if self.manager is not None and self._prepare_scene is None:
                self._load_visual_board(self.board_data)
                self.manager.resync(self.manager.current_snapshot)
                self.manager.renderer.set_actor_visuals_visible(False)
            self._status = f'LEVEL ERROR: {error}'
            self._refresh_hud()
            return False
        self._cancel_deferred()
        self._dispose_manager()
        self._scene, self.manager = (new_scene, new_manager)
        self.board, self.board_data, self.state = (board, data, initial)
        self.level_index = index
        self._sessions += 1
        self.session_id = session
        self.revision = self.moves = self._index = 0
        self._actions = ()
        self.search = self.search_name = self.selected = None
        self.guide_active = self.used_guide = False
        self.phase, self._status, self._mode = ('READY', None, Replay.IDLE)
        self.manager.renderer.set_actor_visuals_visible(False)
        self._refresh_hud()
        if board.is_goal(initial):
            self._begin_terminal(EventKind.GOAL_COMPLETE)
        return True

    def _dispose_manager(self):
        self._epoch += 1
        self._current_plan = None
        self._pending_requests.clear()
        if self._scene is not None:
            self._scene.dispose()
        elif self.manager is not None:
            self.manager.dispose()
        self._scene = self.manager = None

    def _emit(self, name):
        if self._on_event is not None:
            self._on_event(name)

    def load_level(self, index):
        return self._load_level(index)

    def new_game(self):
        return self._load_level(0)

    def select_level(self):
        return self._load_level(self.level_index + 1)

    def restart_level(self):
        if self.manager is None:
            return
        self._reset_to_start(keep_solution=False)
        self.guide_active = False
        self._refresh_hud()
        self._emit('restart')
        if self.board.is_goal(self.state):
            self._begin_terminal(EventKind.GOAL_COMPLETE)

    def manual_move(self, action):
        if self.phase != 'READY' or self.manager is None:
            return False
        if self._mode is not Replay.IDLE:
            self._status = 'Finish or hide the solution first'
            self._refresh_hud()
            return False
        return self._submit_move(action)

    def _next_request_id(self):
        self._requests += 1
        return f'req-{self._requests}'

    def _submit_move(self, action):
        """Validate a complete visual plan before accepting one authoritative Core action."""
        if self.manager.is_busy or self._current_plan is not None or self.phase != 'READY':
            return False
        try:
            plan = plan_action(self.board, self.state, self.board_data, self.manager.current_snapshot, action, self._next_request_id, move_duration=self.MOVE_DURATION, terminal_duration=self.TERMINAL_DURATION)
            if not plan.requests:
                return False
            for request in plan.requests:
                validate_request(request, self.board_data)
            self._current_plan = plan
            self._pending_requests = deque(plan.requests)
            accepted = self._submit_next_phase()
            if accepted and action in ACTION_TO_ROLL:
                self._emit('roll')
            return accepted
        except Exception as error:
            self._enter_error(str(error))
            return False

    def _submit_next_phase(self):
        request = self._pending_requests.popleft()
        epoch = self._epoch
        return self._safe_submit(request, lambda result: self._on_phase_done(epoch, result))

    def _on_phase_done(self, epoch, result):
        """Advance visual revisions per phase; commit Core state and move count only once."""
        if epoch != self._epoch:
            return
        if result.status is not AnimationStatus.COMPLETED:
            self._enter_error(result.error or result.status.value)
            return
        self.revision = self.manager.current_snapshot.state_revision
        if self._pending_requests:
            self._submit_next_phase()
            return
        plan, self._current_plan = (self._current_plan, None)
        if plan.failure:
            self.phase, self._mode = ('FELL', Replay.IDLE)
            self._refresh_hud()
            self._emit('fall')
            return
        self.state = plan.next_state
        self.moves += 1
        if self.board.is_goal(self.state):
            self._begin_terminal(EventKind.GOAL_COMPLETE)
        else:
            self._refresh_hud()
            self._continue_replay()

    def _begin_terminal(self, kind):
        epoch = self._epoch
        request = AnimationRequest(1, self._next_request_id(), self.manager.current_snapshot, None, AnimationKind.TERMINAL, self.TERMINAL_DURATION, events=(AnimationEvent(kind),), terminal=TerminalVisualOutcome(kind))
        return self._safe_submit(request, lambda result: self._on_terminal_done(epoch, kind, result))

    def _safe_submit(self, request, callback):
        try:
            self.manager.submit(request, callback)
        except Exception as error:
            self._enter_error(str(error))
            return False
        return True

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
        """Invalidate callbacks and restore the last committed Core pose in a fresh visual session."""
        self._epoch += 1
        self._current_plan = None
        self._pending_requests.clear()
        self._cancel_deferred()
        if self.manager is not None and self.state is not None:
            self._sessions += 1
            self.session_id = f'play-{self._sessions}'
            self.revision = 0
            try:
                self.manager.resync(build_game_snapshot(self.state, board_data=self.board_data, session_id=self.session_id, state_revision=0))
            except Exception as rollback:
                message += f'; rollback: {rollback}'
        self.phase, self._mode = ('ERROR', Replay.IDLE)
        self._status = f'ERROR: {message}'
        self._refresh_hud()

    def run_solver(self, name, after='play'):
        if name not in self._solver_specs or self.manager is None:
            return
        self._reset_to_start(keep_solution=False)
        self.used_guide = True
        self.phase = 'SOLVING'
        self._status = f'SOLVING {name}…'
        self._refresh_hud()
        self._defer(lambda: self._solve(name, after))

    def _defer(self, fn):
        if self._task_mgr is None:
            fn()
            return

        def run(task):
            self._deferred = None
            fn()
            return task.done
        self._deferred = self._task_mgr.doMethodLater(0.05, run, f'ControllerSolve-{id(self)}')

    def _cancel_deferred(self):
        for task in (self._deferred, self._job_task):
            if task is not None and self._task_mgr is not None:
                self._task_mgr.remove(task)
        self._deferred = self._job_task = None
        if self._job is not None:
            self._job.cancel()
            self._job = None

    def _solve(self, name, after='play'):
        """Keep Panda calls on this thread; compute and measure native-game solvers in a child process."""
        module, class_name = self._solver_specs[name]
        try:
            if self._task_mgr is None:
                result = getattr(importlib.import_module(module), class_name)(self.board).solve()
                self._finish_search(name, after, True, result)
            else:
                self._job = self._job_factory(self.board, module, class_name)
                epoch = self._epoch

                def poll(task):
                    if epoch != self._epoch:
                        return task.done
                    try:
                        outcome = self._job.poll()
                    except Exception as error:
                        self._job.cancel()
                        outcome = (False, str(error))
                    if outcome is None:
                        return task.cont
                    self._job = self._job_task = None
                    self._finish_search(name, after, *outcome)
                    return task.done
                self._job_task = self._task_mgr.add(poll, f'SolverPoll-{id(self)}')
        except Exception as error:
            self._finish_search(name, after, False, str(error))

    def _finish_search(self, name, after, success, result):
        self.phase = 'READY'
        if not success:
            self._status = f'{name} ERROR: {result}'
            self.guide_active = False
            self._refresh_hud()
            return
        self.search, self.search_name = (result, name)
        if not result.success:
            self._status = f'{name}: NO SOLUTION'
            self.guide_active = False
            self._refresh_hud()
            return
        self._status = None
        self._actions, self._index, self._mode = (tuple(result.actions), 0, Replay.IDLE)
        self._refresh_hud()
        if not self._actions:
            if self.board.is_goal(self.state):
                self._begin_terminal(EventKind.GOAL_COMPLETE)
            else:
                self._enter_error('Solver returned an empty solution outside the goal.')
            return
        self.step() if after == 'step' else self.play()

    def select_solver(self, name):
        if name not in self._solver_specs or self.manager is None:
            return False
        self._reset_to_start(keep_solution=False)
        self.selected, self.guide_active = (name, False)
        self._refresh_hud()
        return True

    def deselect_solver(self):
        """Close AI selection without rewinding manual play; cancel active work."""
        if self.guide_active or self.phase == 'SOLVING' or self._mode is not Replay.IDLE:
            self.cancel_guide()
        else:
            self.selected = None
            self._refresh_hud()

    def start_guide(self, mode):
        if self.selected is None or self.phase == 'ERROR':
            return
        self.guide_active = True
        if self.search_name == self.selected and self.search is not None and self.search.success:
            self.used_guide = True
            self.play() if mode == 'play' else self.step()
        elif self.phase != 'SOLVING':
            self.run_solver(self.selected, after=mode)

    def toggle_play(self):
        if self._mode is Replay.PLAYING:
            self.pause()
        else:
            self.start_guide('play')

    def end_guide(self):
        """Return control to the player while retaining the completed solver metrics."""
        if self.manager is None:
            return
        self._reset_to_start(keep_solution=False, preserve_result=True)
        self.selected, self.guide_active = (None, False)
        self.used_guide = True
        self._refresh_hud()

    def cancel_guide(self):
        if self.manager is None or not (self.guide_active or self.selected or self.phase == 'SOLVING'):
            return
        guided = self.guide_active
        self._reset_to_start(keep_solution=False, preserve_result=True)
        self.selected, self.guide_active = (None, False)
        self.used_guide = guided
        self._refresh_hud()

    def _prepare_replay(self):
        if not self._actions or self.phase in ('SOLVING', 'ERROR'):
            return False
        if self._mode is Replay.IDLE and (self.moves != self._index or self._index >= len(self._actions) or self.phase in ('GOAL', 'FELL')):
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
        """Finish the current Core action, including remaining effects, then pause before the next action."""
        if self.manager is None or not self._prepare_replay():
            return
        self._mode = Replay.PAUSED
        if self.manager.is_busy:
            self.manager.resume()
        elif self._index < len(self._actions):
            self._replay_step()
        self._refresh_hud()

    def stop(self):
        if self.manager is not None:
            self._reset_to_start(keep_solution=True)
            self._refresh_hud()

    def _replay_step(self):
        if self._index >= len(self._actions):
            self._mode = Replay.IDLE
            return
        if self._submit_move(self._actions[self._index]):
            self._index += 1
        elif self.phase != 'ERROR':
            self._enter_error('Solution contains a blocked action.')

    def _continue_replay(self):
        if self._mode is Replay.PLAYING:
            self._replay_step()

    def set_speed(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Playback speed must be finite.')
        self.speed = min(max(value, SPEED_RANGE[0]), SPEED_RANGE[1])
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
        self._hud.update_view_model(HudViewModel(level_label=f'{entry.title} ({self.level_index + 1}/{len(self._catalog)})', runtime_status=self._status_text(), move_count=self.moves, search_time_ms=None if result is None else result.time_taken * 1000, expanded_nodes=None if result is None else result.expanded_nodes, solution_length=result.solution_length if result is not None and result.success else None, peak_python_memory_bytes=None if result is None else round(result.peak_memory * 1024)))
        self._hud.set_playing(self.guide_active and self._mode is Replay.PLAYING)
        self._hud.set_guide_mode(self.guide_active)

    @property
    def is_idle(self):
        return self.manager is not None and (not self.manager.is_busy) and (self._current_plan is None) and (self.phase not in ('SOLVING', 'ERROR')) and (self._mode is Replay.IDLE) and (self._deferred is None) and (self._job is None)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self._cancel_deferred()
        self._dispose_manager()
