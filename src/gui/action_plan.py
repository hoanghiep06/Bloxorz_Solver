"""One authoritative Core action -> explicit, cancellable visual phases."""
from dataclasses import dataclass, replace
from src.gui.game_adapter import CUBE_IDS, build_game_snapshot
from src.gui.animation_math import RollDirection
from src.gui.animation_contracts import (
    AnimationEvent as Event, EventKind as E, AnimationKind as K,
    AnimationRequest, TerminalVisualOutcome,
)

DIRECTIONS = dict(zip(('U', 'D', 'L', 'R'),
                     (RollDirection.UP, RollDirection.DOWN, RollDirection.LEFT, RollDirection.RIGHT)))


def surface_events(before, after):
    events = []
    old = {state.bridge_id: state.present for state in before.bridge_states}
    for state in after.bridge_states:
        if old[state.bridge_id] != state.present:
            events.append(Event(E.BRIDGE_PRESENT if state.present else E.BRIDGE_ABSENT,
                                target_id=state.bridge_id))
    for key in sorted(set(before.activated_switch_ids) ^ set(after.activated_switch_ids)):
        events.append(Event(E.SWITCH_ACTIVATE if key in after.activated_switch_ids else E.SWITCH_DEACTIVATE,
                            target_id=key))
    for cell in sorted(set(after.broken_fragile_cells) - set(before.broken_fragile_cells)):
        events.append(Event(E.FRAGILE_BREAK, cell=cell))
    return events


@dataclass(frozen=True)
class ActionPlan:
    next_state: object
    requests: tuple
    failure: bool = False


def plan_action(board, state, board_data, before, action, next_id,
                *, move_duration=.35, effect_duration=.22, terminal_duration=.9):
    outcome = board.describe_transition(state, action)
    if outcome.failure_reason == 'blocked':
        return ActionPlan(None, ())
    current, requests = before, []
    def snapshot(core_state, **kwargs):
        return build_game_snapshot(core_state, board_data=board_data,
            session_id=before.session_id, state_revision=current.state_revision + 1,
            broken_fragile_cells=current.broken_fragile_cells, **kwargs)
    def append(kind, after, events=(), **kwargs):
        nonlocal current
        request = AnimationRequest(1, next_id(), current, after, kind,
            terminal_duration if kind is K.TERMINAL else move_duration if kind is K.ROLL else effect_duration,
            events=tuple(events), **kwargs)
        requests.append(request)
        if after is not None:
            current = after
    actor = CUBE_IDS[state.active_cube] if state.is_split() else None
    if action in DIRECTIONS:
        try:
            motion = snapshot(outcome.motion_state)
        except ValueError:
            # An off-board destination cannot be an in-bounds visual snapshot.
            if outcome.next_state is not None:
                raise
            append(K.TERMINAL, None, (Event(E.FALL),), terminal=TerminalVisualOutcome(
                E.FALL, actor_id=actor, roll_direction=DIRECTIONS[action]))
            return ActionPlan(None, tuple(requests), True)
        append(K.ROLL, motion, surface_events(current, motion),
               direction=DIRECTIONS[action], actor_id=actor)
    target_state = outcome.next_state or outcome.attempted_state
    target = snapshot(target_state)
    events = surface_events(current, target)
    if current.block_mode != target.block_mode:
        events.append(Event(E.SPLIT if target_state.is_split() else E.MERGE,
            cube_ids=CUBE_IDS, active_cube_id=target.active_cube_id if target_state.is_split() else None))
    elif current.active_cube_id != target.active_cube_id:
        events.append(Event(E.ACTIVE_CUBE_CHANGE, active_cube_id=target.active_cube_id))
    if events:
        append(K.EFFECTS, target, events)
    if outcome.next_state is None:
        if outcome.failure_reason == 'fragile':
            cell = (target_state.r, target_state.c)
            broken = replace(current, state_revision=current.state_revision + 1,
                broken_fragile_cells=tuple(sorted({*current.broken_fragile_cells, cell})))
            append(K.EFFECTS, broken, (Event(E.FRAGILE_BREAK, cell=cell),))
        failed_actor = (CUBE_IDS[outcome.failed_cube if outcome.failed_cube is not None
                                 else target_state.active_cube]
                        if target_state.is_split() else None)
        append(K.TERMINAL, None, (Event(E.FALL),),
               terminal=TerminalVisualOutcome(E.FALL, actor_id=failed_actor))
    return ActionPlan(outcome.next_state, tuple(requests), outcome.next_state is None)
