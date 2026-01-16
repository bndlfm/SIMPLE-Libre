import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_MAIN,
)


class TestToEligibleAffectsSecondActor(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_echeverria_unshaded_makes_dr_eligible_for_second_action(self):
        # Card 27 order is DGSM (DR, Syndicate, Govt, M26).
        # If GOVT acts first, the next actor is the next eligible AFTER GOVT in order (M26),
        # so "DR to Eligible" should not change who acts second on this card.
        # Instead, it should make DR eligible immediately and clear any next-card ineligibility markers.
        d = EVENT_DECK_DATA[27]
        self.env.current_card = Card(27, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Slot 0: Govt acts.
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        # Force DR ineligible before the event, so without the 'to Eligible' effect
        # they could not be selected as the second actor.
        self.env.players[2].eligible = False
        self.env.players[2].available_forces[0] = 2
        self.env.ineligible_next_card.add(2)
        self.env.ineligible_through_next_card.add(2)

        # Play Echeverría unshaded.
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Complete the multi-step placements (place 2 DR Guerrillas anywhere).
        # Use non-Pinar spaces for determinism.
        place_a = 9   # Oriente
        place_b = 11  # Sierra Maestra
        self.env.step(self.env._target_space_action_base + place_a)
        self.env.step(self.env._target_space_action_base + place_b)

        # DR should now be eligible (even though they will not be the second actor due to order).
        self.assertTrue(self.env.players[2].eligible)
        self.assertNotIn(2, self.env.ineligible_next_card)
        self.assertNotIn(2, self.env.ineligible_through_next_card)

        # Slot should now be 1 and Govt is ineligible for the current card.
        self.assertEqual(self.env.card_action_slot, 1)
        self.assertFalse(self.env.players[0].eligible)

        # step() already advances the turn pointer once; the next actor should be DR (index 2)
        # because DGSM starts with DR and the event made them eligible.
        self.assertEqual(self.env.current_player_num, 2)


if __name__ == "__main__":
    unittest.main()
