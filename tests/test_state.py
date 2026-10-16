import inspect
import unittest
from dataclasses import FrozenInstanceError

from src.core.state import BloxorzState, Orientation


class StateTests(unittest.TestCase):
    def test_orientation_values_are_stable(self):
        self.assertEqual([(o.name, o.value) for o in Orientation], [
            ('STANDING', 0), ('HORIZONTAL', 1), ('VERTICAL', 2),
        ])

    def test_constructor_keeps_positional_and_keyword_api(self):
        self.assertEqual(list(inspect.signature(BloxorzState).parameters),
                         ['r', 'c', 'orientation', 'bridges_state'])
        first = BloxorzState(3, 4, Orientation.HORIZONTAL, (True, False))
        second = BloxorzState(r=3, c=4, orientation=Orientation.HORIZONTAL,
                              bridges_state=(True, False))
        self.assertEqual(first, second)
        self.assertEqual(BloxorzState(3, 4, Orientation.STANDING).bridges_state, ())

    def test_standing_occupies_anchor_only(self):
        state = BloxorzState(3, 4, Orientation.STANDING)
        self.assertEqual(state.get_occupied_cells(), [(3, 4)])
        self.assertTrue(state.is_standing())

    def test_horizontal_anchor_is_left_cell(self):
        state = BloxorzState(3, 4, Orientation.HORIZONTAL)
        self.assertEqual(state.get_occupied_cells(), [(3, 4), (3, 5)])
        self.assertFalse(state.is_standing())

    def test_vertical_anchor_is_top_cell_and_is_not_standing(self):
        state = BloxorzState(3, 4, Orientation.VERTICAL)
        self.assertEqual(state.get_occupied_cells(), [(3, 4), (4, 4)])
        self.assertFalse(state.is_standing())

    def test_equal_states_have_equal_hashes_and_dictionary_lookup(self):
        first = BloxorzState(3, 4, Orientation.HORIZONTAL, (True, False))
        second = BloxorzState(3, 4, Orientation.HORIZONTAL, (True, False))
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertEqual(len({first, second}), 1)
        self.assertEqual({first: 'path'}[second], 'path')

    def test_different_coordinates_or_orientation_are_distinct(self):
        state = BloxorzState(3, 4, Orientation.STANDING)
        for other in (
            BloxorzState(2, 4, Orientation.STANDING),
            BloxorzState(3, 5, Orientation.STANDING),
            BloxorzState(3, 4, Orientation.VERTICAL),
        ):
            with self.subTest(other=other):
                self.assertNotEqual(state, other)

    def test_bridge_flags_participate_in_identity(self):
        states = [BloxorzState(3, 4, Orientation.STANDING, flags)
                  for flags in ((), (True,), (False,), (False, True))]
        self.assertEqual(len(set(states)), 4)

    def test_state_is_not_equal_to_an_unrelated_object(self):
        self.assertNotEqual(BloxorzState(3, 4, Orientation.STANDING), (3, 4, 0))

    def test_identity_fields_cannot_be_reassigned_or_deleted(self):
        state = BloxorzState(3, 4, Orientation.STANDING, (True,))
        original_hash = hash(state)
        visited = {state}
        for field, value in (('r', 5), ('c', 6),
                             ('orientation', Orientation.VERTICAL),
                             ('bridges_state', (False,))):
            with self.subTest(field=field):
                with self.assertRaises(FrozenInstanceError):
                    setattr(state, field, value)
                with self.assertRaises(FrozenInstanceError):
                    delattr(state, field)
        self.assertEqual(hash(state), original_hash)
        self.assertIn(state, visited)

    def test_occupied_cells_result_cannot_mutate_the_state(self):
        state = BloxorzState(3, 4, Orientation.HORIZONTAL)
        cells = state.get_occupied_cells()
        cells.clear()
        self.assertEqual(state.get_occupied_cells(), [(3, 4), (3, 5)])

    def test_coordinates_must_be_integers(self):
        for r, c in ((1.5, 0), (0, '1'), (True, 0), (0, None)):
            with self.subTest(r=r, c=c):
                with self.assertRaisesRegex(TypeError, 'coordinates'):
                    BloxorzState(r, c, Orientation.STANDING)

    def test_negative_coordinates_are_representable(self):
        state = BloxorzState(-1, -2, Orientation.STANDING)
        self.assertEqual(state.get_occupied_cells(), [(-1, -2)])

    def test_unsupported_orientation_is_rejected(self):
        for orientation in (0, 3, 'STANDING', None):
            with self.subTest(orientation=orientation):
                with self.assertRaisesRegex(ValueError, 'Orientation'):
                    BloxorzState(1, 1, orientation)

    def test_bridge_flags_must_be_an_immutable_tuple_of_booleans(self):
        for flags in ([True], (1,), ('open',), None):
            with self.subTest(flags=flags):
                with self.assertRaisesRegex(TypeError, 'tuple of booleans'):
                    BloxorzState(1, 1, Orientation.STANDING, flags)

    def test_repr_includes_debug_identity(self):
        self.assertEqual(repr(BloxorzState(1, 2, Orientation.STANDING)),
                         'State(1, 2, STANDING)')
        self.assertIn('bridges_state=(True, False)', repr(
            BloxorzState(1, 2, Orientation.VERTICAL, (True, False))))


if __name__ == '__main__':
    unittest.main()
