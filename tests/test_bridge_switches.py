"""Public transition regressions for bridge IDs and switch target aliases."""
import json
import tempfile
import unittest
from pathlib import Path

from src.core.board import Board


class BridgeSwitchRegressionTests(unittest.TestCase):
    def make_board(self, bridge_ids, target_fields):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'level.json'
        bridges = []
        for index, bridge_id in enumerate(bridge_ids):
            bridge = {'cells': [[2, index]], 'initial_state': False}
            if bridge_id is not None:
                bridge['id'] = bridge_id
            bridges.append(bridge)
        path.write_text(json.dumps({
            'grid': [[1] * 8 for _ in range(3)],
            'start': [1, 0], 'goal': [1, 7],
            'bridges': bridges,
            'switches': [{
                'cell': [1, 3], 'type': 'soft', 'action': 'open',
                **target_fields,
            }],
        }), encoding='utf-8')
        return Board(str(path))

    def activate(self, bridge_ids, target_fields):
        board = self.make_board(bridge_ids, target_fields)
        initial = board.get_initial_state()
        first = board.transition(initial, 'R')
        self.assertIsNotNone(first)
        result = board.transition(first, 'R')
        self.assertIsNotNone(result)
        self.assertEqual(initial.bridges_state, (False,) * len(bridge_ids))
        return board, result

    def test_zero_id_works_for_all_target_aliases_and_forms(self):
        for key in ('targets', 'bridges', 'target'):
            for value in (0, '0', [0], ['0']):
                with self.subTest(key=key, value=value):
                    board, result = self.activate([0, 'other'], {key: value})
                    self.assertEqual(result.bridges_state, (True, False))
                    self.assertTrue(board.is_valid_cell(2, 0, result.bridges_state))
                    self.assertFalse(board.is_valid_cell(2, 1, result.bridges_state))

    def test_none_target_fields_fall_back(self):
        _, result = self.activate([0], {
            'targets': None, 'bridges': None, 'target': 0,
        })
        self.assertEqual(result.bridges_state, (True,))

    def test_first_non_none_target_field_has_priority(self):
        _, result = self.activate([0, 'other'], {'targets': 0, 'bridges': 'other'})
        self.assertEqual(result.bridges_state, (True, False))

    def test_explicit_empty_targets_do_not_fall_back(self):
        _, result = self.activate([0, 'other'], {'targets': [], 'target': 'other'})
        self.assertEqual(result.bridges_state, (False, False))

    def test_missing_or_none_targets_leave_bridges_unchanged(self):
        for fields in ({}, {'targets': None, 'bridges': None, 'target': None}):
            with self.subTest(fields=fields):
                _, result = self.activate([0], fields)
                self.assertEqual(result.bridges_state, (False,))

    def test_target_list_opens_all_selected_bridges(self):
        _, result = self.activate([0, 'other', 'unused'], {'targets': [0, 'other']})
        self.assertEqual(result.bridges_state, (True, True, False))

    def test_explicit_numeric_ids_win_over_indices_in_either_order(self):
        for bridge_ids in ([1, 2], [2, 1], ['1', '2'], ['2', '1']):
            for target in (1, '1'):
                with self.subTest(bridge_ids=bridge_ids, target=target):
                    board, result = self.activate(bridge_ids, {'targets': [target]})
                    expected_index = next(i for i, value in enumerate(bridge_ids)
                                          if str(value) == '1')
                    self.assertEqual(result.bridges_state,
                                     tuple(i == expected_index for i in range(2)))
                    self.assertTrue(board.is_valid_cell(2, expected_index,
                                                       result.bridges_state))

    def test_non_conflicting_index_aliases_still_work(self):
        for bridge_ids in (['left', 'right'], [None, None]):
            for target in (1, '1'):
                with self.subTest(bridge_ids=bridge_ids, target=target):
                    _, result = self.activate(bridge_ids, {'target': target})
                    self.assertEqual(result.bridges_state, (False, True))

    def test_duplicate_or_equivalent_explicit_ids_are_rejected(self):
        for bridge_ids in ([1, 1], [1, '1'], ['same', 'same']):
            with self.subTest(bridge_ids=bridge_ids):
                with self.assertRaisesRegex(ValueError, 'Duplicate bridge ID'):
                    self.make_board(bridge_ids, {'target': 1})


if __name__ == '__main__':
    unittest.main()
