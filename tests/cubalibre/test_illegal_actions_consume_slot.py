import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestIllegalActionsConsumeSlot(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_illegal_action_increments_slot(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.card_action_slot = 0
        self.env.phase = 0

        # Choose an action that is definitely illegal in PHASE_CHOOSE_MAIN
        # (event-side action IDs are illegal in main phase).
        illegal_action = self.env._event_side_base
        self.assertEqual(self.env.legal_actions[illegal_action], 0)

        old_slot = self.env.card_action_slot
        self.env.step(illegal_action)
        self.assertEqual(self.env.card_action_slot, old_slot + 1)

    def test_two_illegal_actions_advance_to_next_card(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])
        original_id = self.env.current_card.id

        self.env.card_action_slot = 0
        self.env.phase = 0
        for p in self.env.players:
            p.eligible = True

        illegal_action = self.env._event_side_base
        self.assertEqual(self.env.legal_actions[illegal_action], 0)

        self.env.step(illegal_action)
        self.env.step(illegal_action)

        # After two actions consumed, card should advance.
        self.assertNotEqual(self.env.current_card.id, original_id)
        self.assertEqual(self.env.card_action_slot, 0)


if __name__ == "__main__":
    unittest.main()
