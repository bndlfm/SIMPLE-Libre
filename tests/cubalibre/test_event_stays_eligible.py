import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_EVENT, EVENT_UNSHADED


class TestEventStaysEligible(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _make_next_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        return Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    @unittest.skip("Covered by tests/cubalibre/test_card_19_sierra_maestra_manifesto.py")
    def test_manifesto_unshaded_executing_faction_stays_eligible(self):
        # Card 19: Sierra Maestra Manifesto (unshaded says executing faction stays eligible)
        self._set_current_card(19)

        # Force current player to Govt for determinism.
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Choose MAIN_EVENT, then choose EVENT_UNSHADED.
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.assertEqual(self.env.phase, 1)

        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Acting faction is ineligible for the remainder of the current card.
        self.assertFalse(self.env.players[0].eligible)

        # Acting faction is ineligible for the remainder of the current card, but should be
        # eligible on the next card due to stay-eligible text.
        self.assertNotIn(0, self.env.ineligible_next_card)

        # Force the next drawn card and check eligibility application.
        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()
        self.assertTrue(self.env.players[0].eligible)

    @unittest.skip("Covered by tests/cubalibre/test_card_18_pact_of_caracas.py")
    def test_pact_of_caracas_unshaded_executing_faction_stays_eligible(self):
        # Card 18: Pact of Caracas (unshaded says executing faction stays eligible for next card)
        self._set_current_card(18)

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        # Choose the first legal event-side for this card (avoid hardcoding unshaded/shaded).
        mask = self.env.legal_actions
        legal = [i for i, x in enumerate(mask) if x == 1]
        self.assertTrue(len(legal) > 0)
        self.env.step(legal[0])

        self.assertNotIn(0, self.env.ineligible_next_card)

        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()
        self.assertTrue(self.env.players[0].eligible)

    def test_normal_event_makes_actor_ineligible(self):
        # Use a simple event without stay-eligible text and without additional targeting phases.
        # Card 48 (Santo Trafficante, Jr) unshaded is immediate.
        self._set_current_card(48)

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Normal events make the executing faction ineligible on the NEXT card.
        self.assertIn(0, self.env.ineligible_next_card)
        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()
        self.assertFalse(self.env.players[0].eligible)


if __name__ == "__main__":
    unittest.main()
