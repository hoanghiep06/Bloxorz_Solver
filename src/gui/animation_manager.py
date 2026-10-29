"""Main-thread visual animation ownership; no Controller, input or solver queue."""
from collections import deque
from dataclasses import replace
import threading

from panda3d.core import ClockObject

from src.gui.animation_contracts import (
    AnimationKind, AnimationStatus as Status, AnimationResult, EventKind,
    as_visual_board, as_visual_snapshot, validate_request,
)
from src.gui.animation_math import (
    VisualPose, RollPlan, canonical_poses, smoothstep, lerp, add, rotate, finite,
)
from src.gui.animation_timeline import AnimationTimeline
from src.gui.fall_math import FallPlan
from src.gui.split_teleport_math import SplitTeleportPlan, MergeTeleportPlan
from src.gui.split_teleport_vfx import SplitTeleportVFX
from src.gui.animation_effects import AnimatedActorRig, event_progress
from src.gui.advanced_contracts import validate_snapshot, SwitchVisualKind


class AnimationManager:
    """Own one persistent rig and optionally one updater task.

    submit rejects by exception before acceptance. Each accepted request emits
    exactly one synchronous terminal result when completed/cancelled/failed.
    Callback exceptions propagate after terminal bookkeeping, never create a
    second result. Cancel restores known before-state and its visual orientation.
    Explicit resync/release may intentionally reset to the canonical face basis.
    """
    def __init__(self, renderer, board_data, snapshot, block_root, *, surface_layer=None,
                 pitch=1.0, task_mgr=None, audio=None):
        self._thread = threading.get_ident()
        self.renderer = renderer
        self._audio,self._audio_track=audio,None
        self.board = as_visual_board(board_data)
        self._pitch = pitch
        from src.gui.geometry_math import cell_to_world
        from src.gui.advanced_contracts import AdvancedTileKind
        self._support_patches = tuple((cell, cell_to_world(*cell, rows=self.board.rows,
            cols=self.board.cols, pitch=pitch)) for cell in (
            (r,c) for r,row in enumerate(self.board.tiles) for c,kind in enumerate(row)
            if kind in (AdvancedTileKind.FLOOR,AdvancedTileKind.FRAGILE))
            if cell not in self.board.goal_cells)
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
        self._fall = None
        self._split_plan = self._split_vfx = None
        self._recent_ids = deque(maxlen=128)
        self._task_mgr, self._task = task_mgr, None
        self._rig = None
        self._snapshot, self._poses = snapshot, poses
        try:
            self._rig = AnimatedActorRig(block_root, pitch=pitch)
            # Prewarm on boards declaring a split switch, so activation does not
            # allocate geometry or change the stable scene resource budget.
            if any(switch.kind is SwitchVisualKind.SPLIT for switch in self.board.switches):
                self._split_vfx = SplitTeleportVFX(self._rig.root,pitch=pitch)
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
        if self.surface_layer is None and (request.terminal is not None
                and request.terminal.collapse_cell is not None):
            raise ValueError('Fragile collapse requires an explicitly wired surface layer.')
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
        self._fall = None
        if request.terminal is not None and request.terminal.kind is EventKind.FALL:
            from src.gui.advanced_contracts import AdvancedTileKind as Tile
            from src.gui.geometry_math import cell_to_world
            before=as_visual_snapshot(request.before_snapshot)
            present={b.bridge_id for b in before.bridge_states if b.present}
            bridge_cells={cell for b in self.board.bridges if b.bridge_id in present for cell in b.cells}
            supports=tuple(cell_to_world(r,c,rows=self.board.rows,cols=self.board.cols,pitch=self._pitch)
                for r,row in enumerate(self.board.tiles) for c,kind in enumerate(row)
                if (r,c) not in self.board.goal_cells and (r,c) not in before.broken_fragile_cells
                and (kind in (Tile.FLOOR,Tile.FRAGILE) or (r,c) in bridge_cells))
            self._fall=FallPlan(self._poses[request.terminal.actor_id],duration=request.duration,
                pitch=self._pitch,supports=supports,roll_direction=request.terminal.roll_direction,
                fall_distance=request.terminal.fall_distance)
        self._start_poses = self._poses.copy()
        self._targets, self._roll = target, plan
        self._timeline = AnimationTimeline(request.duration, self._rate)
        self._request, self._callback = request, on_finished
        self._recent_ids.append((request.session_id, request.request_id))
        self._status, self._progress = Status.PLAYING, 0.0
        try:
            self._split_plan = None
            for event in request.events:
                if event.kind is EventKind.SPLIT:
                    self._split_plan = SplitTeleportPlan(self._start_poses[None], target,
                        event.cube_ids, event.active_cube_id, self._pitch)
                elif event.kind is EventKind.MERGE:
                    self._split_plan = MergeTeleportPlan(self._start_poses,target[None],
                        event.cube_ids,as_visual_snapshot(request.before_snapshot).active_cube_id,self._pitch)
                if event.kind in (EventKind.SPLIT,EventKind.MERGE):
                    if self._split_vfx is None:
                        self._split_vfx = SplitTeleportVFX(self._rig.root,pitch=self._pitch)
                    self._split_vfx.configure(self._split_plan)
            if self._audio is not None:
                from src.gui.audio_events import AnimationAudioTrack
                self._audio_track=AnimationAudioTrack(self._audio,request,self.board,self._fall)
            self._sample(0)
        except Exception as error:
            self._fail(error)
            raise

    def _draw(self, poses, active_id, *, weights=None, opacity=None, scales=None,
              support_snapshot=None):
        broken = as_visual_snapshot(support_snapshot or self._snapshot).broken_fragile_cells
        if support_snapshot is None and self._request is not None:
            broken = as_visual_snapshot(self._request.before_snapshot).broken_fragile_cells
        self._rig.apply(poses, supports=tuple(xy for cell,xy in self._support_patches if cell not in broken), active_weights=({active_id: 1} if active_id is not None else {})
                        if weights is None else weights, opacity=opacity, scales=scales)

    def _sample(self, progress):
        request = self._request
        before = as_visual_snapshot(request.before_snapshot)
        poses = self._start_poses.copy()
        active = before.active_cube_id
        weights, opacity, scales = None, {}, {}
        if self._roll is not None and self._fall is None:
            key = request.actor_id if request.kind is AnimationKind.ROLL else request.terminal.actor_id
            poses[key] = self._roll.sample(progress if request.kind is AnimationKind.ROLL
                                           else min(1, progress / .45))
        for event in request.events:
            if progress < event.start:
                continue
            u = smoothstep(event_progress(event, progress))
            if event.kind in (EventKind.SPLIT,EventKind.MERGE):
                frame = self._split_plan.sample(event_progress(event, progress))
                poses, opacity, scales, weights = frame.poses, frame.opacity, frame.scales, frame.weights
                self._split_vfx.sample(frame)
                active = event.active_cube_id if event.kind is EventKind.SPLIT else (
                    before.active_cube_id if None not in poses else None)
            elif event.kind is EventKind.ACTIVE_CUBE_CHANGE:
                weights = {}
                if before.active_cube_id is not None:
                    weights[before.active_cube_id] = 1-u
                if event.active_cube_id is not None:
                    weights[event.active_cube_id] = u
            elif event.kind is EventKind.FALL:
                key = request.terminal.actor_id
                sample=self._fall.sample(event_progress(event,progress)*request.duration)
                poses[key]=sample.pose
                opacity[key]=sample.opacity
            elif event.kind is EventKind.GOAL_COMPLETE:
                key = request.terminal.actor_id
                source = self._start_poses[key]
                shrink = smoothstep(min(1, progress / .35))
                scale = 1 - .30*shrink
                sink = max(0, (progress-.35)/.65)
                # Keep bottom on the support plane until width .70 fits inside
                # the existing .76 aperture; only then begin downward suction.
                poses[key] = replace(source, center=(source.center[0], source.center[1],
                    source.extents[2]*scale - 2.4*self._pitch*sink*sink))
                scales[key] = scale
                opacity[key] = 1-smoothstep(min(1, max(0, (progress-.7)/.3)))
        if self.surface_layer is not None:
            self.surface_layer.sample(before, request.events, progress,
                collapse_cell=request.terminal.collapse_cell if request.terminal else None)
        self._draw(poses, active, weights=weights, opacity=opacity, scales=scales)
        self._poses = poses
        self._progress = progress
        self._audio_call('sample',progress)

    def _audio_call(self,method,*args):
        if self._audio_track is None:return
        try:getattr(self._audio_track,method)(*args)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Audio cue failed; gameplay continues.')
            try:self._audio.stop_scope(self._audio_track.scope)
            except Exception:pass  # A disappearing audio device must not fail the visual action.
            self._audio_track=None

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
                if self._split_vfx is not None:
                    self._split_vfx.release()
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
        if self._split_vfx is not None:
            self._split_vfx.release()
        self._split_plan = None
        if self.surface_layer is not None:
            self.surface_layer.release()
        self._poses = self._start_poses.copy()
        self._draw(self._poses, as_visual_snapshot(self._snapshot).active_cube_id)
        self._progress = 0.0

    def _notify(self, status, error=None):
        self._audio_call('finish',status is Status.COMPLETED)
        self._audio_track=None
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
        self._audio_call('pause')
        return True

    def resume(self):
        self._check()
        if not self.is_busy or not self._timeline.resume():
            return False
        self._status = Status.PLAYING
        self._audio_call('resume')
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
        if self._audio is not None:self._audio.stop_session_audio(self._snapshot.session_id)
        try:
            if self.is_busy:
                self._restore_before()
                self._notify(Status.CANCELLED)
            self.renderer.show_snapshot(as_visual_snapshot(snapshot))
            self._draw(poses, as_visual_snapshot(snapshot).active_cube_id, support_snapshot=snapshot)
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
        if self._audio is not None:self._audio.stop_session_audio(self._snapshot.session_id)
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
                if self._split_vfx is not None:
                    self._split_vfx.dispose()
                self._split_plan = None
                if self._rig is not None:
                    self._rig.dispose()
                self._disposed = True
                self._barrier = False
