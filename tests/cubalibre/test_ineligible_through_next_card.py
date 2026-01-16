import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, EVENT_SHADED, EVENT_UNSHADED, MAIN_EVENT


class TestIneligibleThroughNextCard(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.card_first_actor = None
        self.env.card_second_actor = None
        self.env.phase = 0

    def _make_next_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        return Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def test_pact_of_miami_unshaded_makes_govt_ineligible_through_next_card(self):
        self._set_current_card(47)
        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        # Play unshaded event.
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertIn(0, self.env.ineligible_through_next_card)

        # Force the next drawn card.
        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()

        self.assertFalse(self.env.players[0].eligible)
        self.assertEqual(len(self.env.ineligible_through_next_card), 0)

    def test_pact_of_miami_shaded_makes_m26_and_dr_ineligible_through_next_card(self):
        self._set_current_card(47)
        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertIn(1, self.env.ineligible_through_next_card)
        self.assertIn(2, self.env.ineligible_through_next_card)

        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()

        self.assertFalse(self.env.players[1].eligible)
        self.assertFalse(self.env.players[2].eligible)
        self.assertEqual(len(self.env.ineligible_through_next_card), 0)

    def test_alberto_bayo_shaded_makes_m26_ineligible_through_next_card(self):
        self._set_current_card(17)
        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertIn(1, self.env.ineligible_through_next_card)

        self.env.deck.cards = [self._make_next_card(8)]
        self.env.draw_next_card()

        self.assertFalse(self.env.players[1].eligible)
        self.assertEqual(len(self.env.ineligible_through_next_card), 0)


if __name__ == "__main__":
    unittest.main()
