"""Pure event consistency and timeline policy, including Basic schema 1 input."""
from dataclasses import replace, FrozenInstanceError
import subprocess
import sys
import unittest
from src.gui.animation_contracts import *
from src.gui.animation_fixtures import *
from src.gui.animation_timeline import AnimationTimeline


class AnimationContractTests(unittest.TestCase):
    def test_all_explicit_fixture_requests_validate(self):
        for name in SCENARIOS:
            fixture = get_animation_fixture(name)
            self.assertIn('NOT AUTHORITATIVE GAMEPLAY', fixture.provenance)
            for request in fixture.requests:
                validate_request(request, fixture.board)

    def test_deep_immutable_and_no_engine_imports(self):
        request = get_animation_fixture('fragile').requests[0]
        with self.assertRaises(FrozenInstanceError):
            request.request_id = 'x'
        with self.assertRaises(TypeError):
            replace(request, events=list(request.events))
        result = subprocess.run([sys.executable, '-B', '-c',
            'import sys; import src.gui.animation_fixtures; '
            'assert not any(n.startswith(("panda3d", "direct.", "src.core")) for n in sys.modules)'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_request_schema_ids_duration_direction(self):
        request = get_animation_fixture('basic-roll').requests[0]
        for fields in ({'schema_version': 2}, {'schema_version': True}, {'request_id': ' '},
                       {'duration': 0}, {'duration': float('inf')}, {'direction': None}):
            with self.assertRaises((ValueError, TypeError)):
                replace(request, **fields)

    def test_request_identity_properties(self):
        request = get_animation_fixture('basic-roll').requests[0]
        self.assertEqual(request.from_state_revision, 0)
        self.assertEqual(request.to_state_revision, 1)
        self.assertEqual(request.session_id, request.before_snapshot.session_id)
        self.assertEqual(request.board_revision, request.before_snapshot.board_revision)

    def test_after_cannot_change_session_board_schema_or_stale_revision(self):
        r = get_animation_fixture('basic-roll').requests[0]
        for fields in ({'session_id': 'other'}, {'board_revision': 'other'}, {'state_revision': 0}):
            with self.assertRaises(ValueError):
                replace(r, after_snapshot=replace(r.after_snapshot, **fields))
        with self.assertRaises(ValueError):
            replace(r, after_snapshot=as_visual_snapshot(r.after_snapshot))

    def test_typed_event_payloads_and_order(self):
        for args in ({'kind': 'FALL'}, {'kind': Event.FRAGILE_BREAK},
                     {'kind': Event.BRIDGE_PRESENT}, {'kind': Event.SPLIT, 'cube_ids': ('a', 'a')},
                     {'kind': Event.FALL, 'cell': (0, 0)}, {'kind': Event.FALL, 'target_id': 'x'},
                     {'kind': Event.FALL, 'start': .8, 'end': .2}):
            with self.assertRaises((TypeError, ValueError)):
                AnimationEvent(**args)
        r = get_animation_fixture('switches').requests[0]
        with self.assertRaises(ValueError):
            replace(r, events=tuple(reversed(r.events)))

    def test_unknown_event_references_and_missing_events_reject(self):
        f = get_animation_fixture('fragile')
        for events in ((AnimationEvent(Event.FRAGILE_BREAK, cell=(0, 0)),),
                       (AnimationEvent(Event.BRIDGE_PRESENT, target_id='unknown'),),
                       (AnimationEvent(Event.SWITCH_ACTIVATE, target_id='unknown'),)):
            with self.assertRaises(ValueError):
                validate_request(replace(f.requests[0], events=events), f.board)
        f = get_animation_fixture('combined')
        r = f.requests[1]
        with self.assertRaises(ValueError):
            validate_request(replace(r, events=r.events[:1]), f.board)

    def test_split_and_merge_require_explicit_correspondence(self):
        for name in ('split', 'merge'):
            f = get_animation_fixture(name)
            event = replace(f.requests[0].events[0], cube_ids=('a', 'unknown'))
            with self.assertRaises(ValueError):
                validate_request(replace(f.requests[0], events=(event,)), f.board)

    def test_implicit_actor_move_and_mode_change_rejected(self):
        f = get_animation_fixture('fragile')
        r = f.requests[0]
        with self.assertRaises(ValueError):
            validate_request(replace(r, after_snapshot=replace(r.after_snapshot,
                whole_pose=Whole(Orientation.STANDING, (2, 4)))), f.board)
        f = get_animation_fixture('split')
        with self.assertRaises(ValueError):
            validate_request(replace(f.requests[0], kind=Kind.ROLL, direction=Direction.RIGHT), f.board)

    def test_terminal_outcome_needs_explicit_matching_event_and_no_after(self):
        f = get_animation_fixture('fall')
        r = f.requests[0]
        self.assertIsNone(r.after_snapshot)
        with self.assertRaises(ValueError):
            replace(r, after_snapshot=r.before_snapshot)
        with self.assertRaises(ValueError):
            replace(r, events=())
        with self.assertRaises(ValueError):
            replace(r, terminal=TerminalVisualOutcome(Event.GOAL_COMPLETE))

    def test_goal_requires_supplied_goal_pose_not_inferred_win(self):
        f = get_animation_fixture('goal')
        r = f.requests[0]
        with self.assertRaises(ValueError):
            validate_request(replace(r, before_snapshot=replace(r.before_snapshot,
                whole_pose=Whole(Orientation.STANDING, (3, 4)))), f.board)

    def test_duplicate_targets_and_unsupported_event_combinations_rejected(self):
        f = get_animation_fixture('fragile')
        r = f.requests[0]
        with self.assertRaises(ValueError):
            validate_request(replace(r, events=r.events*2), f.board)
        with self.assertRaises(ValueError):
            validate_request(replace(r, events=(AnimationEvent(Event.FALL),)), f.board)

    def test_result_only_reports_committed_revision_or_explicit_terminal(self):
        result = AnimationResult('r', 's', 'b', 0, 1, AnimationStatus.COMPLETED)
        for fields in ({'status': AnimationStatus.PLAYING}, {'to_state_revision': 0},
                       {'to_state_revision': None}, {'status': AnimationStatus.CANCELLED},
                       {'error': 'not a failure'}):
            with self.assertRaises(ValueError):
                replace(result, **fields)
        AnimationResult('r', 's', 'b', 0, None, AnimationStatus.CANCELLED)
        AnimationResult('r', 's', 'b', 0, None, AnimationStatus.FAILED, error='draw error')


class TimelineTests(unittest.TestCase):
    def test_frame_rates_reach_identical_elapsed_pose(self):
        for fps in (30, 60, 120):
            t = AnimationTimeline(1)
            for _ in range(fps//2):
                t.advance(1/fps)
            self.assertAlmostEqual(t.progress, .5)
            for _ in range(fps//2):
                t.advance(1/fps)
            self.assertEqual(t.status, AnimationStatus.COMPLETED)

    def test_pause_resume_and_speed_do_not_jump(self):
        t = AnimationTimeline(1)
        t.advance(.25)
        self.assertTrue(t.pause())
        self.assertFalse(t.pause())
        t.advance(10)
        self.assertEqual(t.progress, .25)
        t.set_playback_rate(4)
        self.assertEqual(t.progress, .25)
        t.resume(); t.advance(.125)
        self.assertEqual(t.progress, .75)

    def test_rate_bounds_and_invalid_delta(self):
        t = AnimationTimeline(1)
        for rate in (0, -1, True, float('nan'), float('inf'), 9):
            with self.assertRaises(ValueError):
                t.set_playback_rate(rate)
        for dt in (-1, True, float('nan')):
            with self.assertRaises(ValueError):
                t.advance(dt)
