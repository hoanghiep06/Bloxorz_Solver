"""Main-thread visual animation ownership; no Controller, input or solver queue."""
from collections import deque
from dataclasses import replace
import math
import threading

from panda3d.core import ClockObject

from src.gui.animation_contracts import (
    AnimationKind, AnimationStatus as Status, AnimationResult, EventKind,
    as_visual_board, as_visual_snapshot, validate_request,
)
from src.gui.animation_math import (
    VisualPose, RollPlan, canonical_poses, smoothstep, lerp, add, rotate, slerp, finite,
)
from src.gui.animation_timeline import AnimationTimeline
from src.gui.animation_effects import AnimatedActorRig, event_progress
from src.gui.advanced_contracts import validate_snapshot


class AnimationManager:
    """Own one persistent rig and optionally one updater task.

    submit rejects by exception before acceptance. Each accepted request emits
    exactly one synchronous terminal result when completed/cancelled/failed.
    Callback exceptions propagate after terminal bookkeeping, never create a
    second result. Cancel restores known before-state and its visual orientation.
    Explicit resync/release may intentionally reset to the canonical face basis.
    """
    def __init__(self, renderer, board_data, snapshot, block_root, *, surface_layer=None,
                 pitch=1.0, task_mgr=None):
        self._thread = threading.get_ident()
        self.renderer = renderer
        self.board = as_visual_board(board_data)
        self._pitch = pitch
        self.surface_layer = surface_layer
        if surface_layer is not None and surface_layer.board != self.board:
            raise ValueError('Surface layer board must match animation board.')
        validate_snapshot(as_visual_snapshot(snapshot), self.board)
        poses = canonical_poses(snapshot, self.board, pitch=pitch)
        self._disposed = self._barrier = False
        self._request = self._callback = self._timeline = None
        self._rate = 1.0
        self._status = Status.IDLE
        self._progress = 0.0
        self._terminal = None
        self._recent_ids = deque(maxlen=128)
        self._task_mgr, self._task = task_mgr, None
        self._rig = None
        self._snapshot, self._poses = snapshot, poses
        try:
            self._rig = AnimatedActorRig(block_root, pitch=pitch)
            renderer.show_snapshot(as_visual_snapshot(snapshot))
            renderer.set_actor_visuals_visible(False)
            self._draw(poses, as_visual_snapshot(snapshot).active_cube_id)
            if task_mgr is not None:
                self._task = task_mgr.add(self._update, f'BloxorzAnimation-{id(self)}')
        except BaseException:
            self.dispose()
            raise

    @property
    def status(self):
        return self._status

    @property
    def is_busy(self):
        return self._request is not None

    @property
    def current_request_id(self):
        return None if self._request is None else self._request.request_id

    @property
    def progress(self):
        return self._progress

    @property
    def current_snapshot(self):
        return self._snapshot

    @property
    def current_visual_poses(self):
        return tuple(self._poses.items())

    @property
    def terminal_outcome(self):
        return self._terminal

    def _check(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('Animation API must be called on its owning main thread.')
        if self._disposed or self._barrier:
            raise RuntimeError('Animation manager is disposed or inside a resync/dispose barrier.')

    def _update(self, task):
        self.advance(ClockObject.getGlobalClock().getDt())
        return task.cont

    def submit(self, request, on_finished=None):
        self._check()
        if self.is_busy:
            raise RuntimeError('Animation manager is busy; no queue is provided.')
        if self._terminal is not None:
            raise RuntimeError('Terminal visual outcome requires explicit resync before another request.')
        if on_finished is not None and not callable(on_finished):
            raise TypeError('on_finished must be callable or None.')
        validate_request(request, self.board)
        if request.before_snapshot != self._snapshot:
            raise ValueError('Request before snapshot must exactly match current authoritative visual input.')
        if (request.session_id, request.request_id) in self._recent_ids:
            raise ValueError('Duplicate request_id (recent bounded history).')
        if self.surface_layer is None and any(e.kind in (
            EventKind.FRAGILE_BREAK, EventKind.BRIDGE_PRESENT, EventKind.BRIDGE_ABSENT,
            EventKind.SWITCH_ACTIVATE, EventKind.SWITCH_DEACTIVATE) for e in request.events):
            raise ValueError('Surface effects require an explicitly wired AnimatedSurfaceLayer.')
        target = None if request.after_snapshot is None else canonical_poses(
            request.after_snapshot, self.board, pitch=self._pitch)
        plan = None
        if request.kind is AnimationKind.ROLL:
            plan = RollPlan(self._poses[request.actor_id], request.direction)
            plan.validate_target(target[request.actor_id])
        elif request.terminal is not None and request.terminal.roll_direction is not None:
            plan = RollPlan(self._poses[request.terminal.actor_id], request.terminal.roll_direction)
        self._start_poses = self._poses.copy()
        self._targets, self._roll = target, plan
        self._timeline = AnimationTimeline(request.duration, self._rate)
        self._request, self._callback = request, on_finished
        self._recent_ids.append((request.session_id, request.request_id))
        self._status, self._progress = Status.PLAYING, 0.0
        try:
            self._sample(0)
        except Exception as error:
            self._fail(error)
            raise

    def _draw(self, poses, active_id, *, weights=None, opacity=None, scales=None):
        self._rig.apply(poses, active_weights=({active_id: 1} if active_id is not None else {})
                        if weights is None else weights, opacity=opacity, scales=scales)

    def _sample(self, progress):
        request = self._request
        before = as_visual_snapshot(request.before_snapshot)
        poses = self._start_poses.copy()
        active = before.active_cube_id
        weights, opacity, scales = None, {}, {}
        if self._roll is not None:
            key = request.actor_id if request.kind is AnimationKind.ROLL else request.terminal.actor_id
            poses[key] = self._roll.sample(progress if request.kind is AnimationKind.ROLL
                                           else min(1, progress / .45))
        for event in request.events:
            if progress < event.start:
                continue
            u = smoothstep(event_progress(event, progress))
            if event.kind is EventKind.SPLIT:
                source = self._start_poses[None]
                poses = {}
                for cube_id, sign in zip(event.cube_ids, (-1, 1)):
                    start = add(source.center, rotate(source.quaternion, (0, 0, sign*self._pitch/2)))
                    center = add(lerp(start, self._targets[cube_id].center, u),
                                 (0, 0, .35*self._pitch*math.sin(math.pi*u)))
                    poses[cube_id] = VisualPose(center, source.quaternion, (self._pitch,)*3)
                if u == 0:
                    poses = self._start_poses.copy()
                active = event.active_cube_id
            elif event.kind is EventKind.MERGE:
                destination = self._targets[None]
                poses = {}
                for cube_id, sign in zip(event.cube_ids, (-1, 1)):
                    start = self._start_poses[cube_id]
                    target = add(destination.center, rotate(destination.quaternion, (0, 0, sign*self._pitch/2)))
                    poses[cube_id] = VisualPose(add(lerp(start.center, target, u),
                        (0, 0, .35*self._pitch*math.sin(math.pi*u))),
                        slerp(start.quaternion, destination.quaternion, u), start.nominal_dimensions)
                if u == 1:
                    poses = {None: destination}
                active = before.active_cube_id if u < 1 else None
            elif event.kind is EventKind.ACTIVE_CUBE_CHANGE:
                weights = {}
                if before.active_cube_id is not None:
                    weights[before.active_cube_id] = 1-u
                if event.active_cube_id is not None:
                    weights[event.active_cube_id] = u
            elif event.kind is EventKind.FALL:
                key = request.terminal.actor_id
                if self._roll is not None:
                    if progress < .45:
                        continue
                    source = self._roll.sample(1)
                    u = smoothstep((progress - .45) / .55)
                else:
                    source = self._start_poses[key]
                poses[key] = replace(source, center=add(source.center, (0, 0, -request.terminal.fall_distance*self._pitch*u*u)))
                opacity[key] = max(0, 1-2*max(0, u-.5))
            elif event.kind is EventKind.GOAL_COMPLETE:
                # A stationary shrink/fade proxy above the mouth, never rigid-body
                # sinking through the Stage 3 goal aperture (.76 < block width 1).
                key = request.terminal.actor_id
                scales[key], opacity[key] = 1-.75*u, 1-u
        if self.surface_layer is not None:
            self.surface_layer.sample(before, request.events, progress)
        self._draw(poses, active, weights=weights, opacity=opacity, scales=scales)
        self._poses = poses
        self._progress = progress

    def advance(self, dt):
        self._check()
        finite(dt, 'dt')
        if self._request is None or self._status is Status.PAUSED:
            return self._progress
        try:
            progress = self._timeline.advance(dt)
            self._sample(progress)
            complete = progress >= 1
            if complete:
                if self.surface_layer is not None:
                    self.surface_layer.release()
                if self._request.after_snapshot is not None:
                    self.renderer.show_snapshot(as_visual_snapshot(self._request.after_snapshot))
                    self._snapshot = self._request.after_snapshot
                else:
                    self._terminal = self._request.terminal
        except Exception as error:
            self._fail(error)
            raise
        if complete:
            self._notify(Status.COMPLETED)
        return self._progress

    def _restore_before(self):
        if self.surface_layer is not None:
            self.surface_layer.release()
        self._poses = self._start_poses.copy()
        self._draw(self._poses, as_visual_snapshot(self._snapshot).active_cube_id)
        self._progress = 0.0

    def _notify(self, status, error=None):
        request, callback = self._request, self._callback
        self._request = self._callback = self._timeline = None
        self._status = status
        result = AnimationResult(request.request_id, request.session_id, request.board_revision,
            request.from_state_revision, request.to_state_revision if status is Status.COMPLETED else None,
            status, request.terminal if status is Status.COMPLETED else None, error)
        if callback is not None:
            callback(result)

    def _fail(self, error):
        message = str(error) or type(error).__name__
        try:
            self._restore_before()
        except Exception as rollback_error:
            message += '; visual rollback failed: ' + str(rollback_error)
        self._notify(Status.FAILED, message)

    def pause(self):
        self._check()
        if not self.is_busy or not self._timeline.pause():
            return False
        self._status = Status.PAUSED
        return True

    def resume(self):
        self._check()
        if not self.is_busy or not self._timeline.resume():
            return False
        self._status = Status.PLAYING
        return True

    def set_playback_rate(self, rate):
        self._check()
        check = AnimationTimeline(1, rate)
        self._rate = check.rate
        if self._timeline is not None:
            self._timeline.set_playback_rate(rate)

    def cancel(self):
        self._check()
        if not self.is_busy:
            return False
        try:
            self._restore_before()
        except Exception as error:
            self._notify(Status.FAILED, str(error) or type(error).__name__)
            raise
        self._notify(Status.CANCELLED)
        return True

    def resync(self, snapshot):
        self._check()
        validate_snapshot(as_visual_snapshot(snapshot), self.board)
        poses = canonical_poses(snapshot, self.board, pitch=self._pitch)
        # Validate same-session stale/conflicting resync before cancelling a request.
        current = self._snapshot
        if snapshot.session_id == current.session_id and (snapshot.state_revision < current.state_revision or
            snapshot.state_revision == current.state_revision and as_visual_snapshot(snapshot) != as_visual_snapshot(current)):
            raise ValueError('Resync cannot reuse a conflicting or stale same-session revision.')
        self._barrier = True
        try:
            if self.is_busy:
                self._restore_before()
                self._notify(Status.CANCELLED)
            self.renderer.show_snapshot(as_visual_snapshot(snapshot))
            self._draw(poses, as_visual_snapshot(snapshot).active_cube_id)
            self._snapshot, self._poses = snapshot, poses
            self._terminal, self._status, self._progress = None, Status.IDLE, 0.0
        finally:
            self._barrier = False

    def dispose(self):
        if self._disposed:
            return
        if threading.get_ident() != self._thread:
            raise RuntimeError('Dispose must run on the owning thread.')
        self._barrier = True
        try:
            if self._task is not None:
                self._task_mgr.remove(self._task)
                self._task = None
            if self.is_busy:
                try:
                    self._restore_before()
                finally:
                    self._notify(Status.CANCELLED)
        finally:
            try:
                if self.surface_layer is not None:
                    self.surface_layer.release()
                self.renderer.set_actor_visuals_visible(True)
            finally:
                if self._rig is not None:
                    self._rig.dispose()
                self._disposed = True
                self._barrier = False
