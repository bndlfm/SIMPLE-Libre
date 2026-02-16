import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard27Echeverria(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded, acting_player=0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_places_two_dr_guerrillas_anywhere_sets_havana_neutral_and_dr_eligible(self):
        # Card 27 (Echeverría, Un): Place 2 DR Guerrillas anywhere. Havana to Neutral. DR to Eligible.
        self._set_card(27)

        havana = self.env.board.spaces[3]
        havana.alignment = 1
        havana.support_active = True

        self.env.players[2].available_forces[0] = 2
        self.env.players[2].eligible = False
        self.env.ineligible_next_card.add(2)
        self.env.ineligible_through_next_card.add(2)

        target_a = 1
        target_b = 5

        self._start_event(shaded=False, acting_player=0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + target_a]), 1)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + target_b]), 1)

        self.env.step(self.env._target_space_action_base + target_a)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + target_b)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        self.assertEqual(int(self.env.board.spaces[target_a].pieces[5]), 1)
        self.assertEqual(int(self.env.board.spaces[target_b].pieces[5]), 1)
        self.assertEqual(int(havana.alignment), 0)
        self.assertFalse(havana.support_active)
        self.assertTrue(self.env.players[2].eligible)
        self.assertNotIn(2, self.env.ineligible_next_card)
        self.assertNotIn(2, self.env.ineligible_through_next_card)

    def test_shaded_removes_two_dr_pieces_closest_to_havana_and_dr_resources_minus_3(self):
        # Card 27 (Echeverría, Sh): Remove the 2 DR pieces closest to Havana. DR Resources –3.
        self._set_card(27)

        # Havana id=3. Space 1 is distance 1, space 0 is distance 2 from Havana.
        self.env.board.spaces[0].pieces[5] = 1
        self.env.board.spaces[1].pieces[5] = 1
        self.env.players[2].resources = 10

        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(int(self.env.players[2].resources), 7)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        self.assertEqual(int(self.env.board.spaces[0].pieces[5]), 0)
        self.assertEqual(int(self.env.board.spaces[1].pieces[5]), 0)


if __name__ == "__main__":
    unittest.main()
