import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


@unittest.skip("Covered by tests/cubalibre/test_card_27_echeverria.py")
class TestEcheverriaUnshadedTargetSelection(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    def test_echeverria_unshaded_allows_target_selection_and_sets_havana_neutral(self):
        d = EVENT_DECK_DATA[27]
        self.env.current_card = Card(27, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        havana = self.env.board.spaces[3]
        havana.alignment = 1
        havana.support_active = True

        self.env.players[2].available_forces[0] = 2
        self.env.players[2].eligible = False
        self.env.ineligible_next_card.add(2)
        self.env.ineligible_through_next_card.add(2)

        target_a = 1
        target_b = 5

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_a = self.env._target_space_action_base + target_a
        pick_b = self.env._target_space_action_base + target_b
        self.assertEqual(self.env.legal_actions[pick_a], 1)
        self.assertEqual(self.env.legal_actions[pick_b], 1)

        self.env.step(pick_a)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(pick_b)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        self.assertEqual(self.env.board.spaces[target_a].pieces[5], 1)
        self.assertEqual(self.env.board.spaces[target_b].pieces[5], 1)
        self.assertEqual(havana.alignment, 0)
        self.assertFalse(havana.support_active)
        self.assertTrue(self.env.players[2].eligible)
        self.assertNotIn(2, self.env.ineligible_next_card)
        self.assertNotIn(2, self.env.ineligible_through_next_card)


if __name__ == "__main__":
    unittest.main()
