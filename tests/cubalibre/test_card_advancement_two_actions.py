import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_PASS


class TestCardAdvancementTwoActions(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_next_card_after_two_completed_actions(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])
        original_id = self.env.current_card.id

        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.update_turn_pointer()

        # Passing does not consume an action slot. To advance to the next card,
        # complete two executing-faction actions (here: take two illegal actions).
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(int(self.env.card_action_slot), 0)

        # Force an illegal action to consume a slot.
        illegal = self.env._event_side_base
        self.env.step(illegal)
        self.assertEqual(int(self.env.card_action_slot), 1)

        self.env.step(illegal)
        self.assertNotEqual(self.env.current_card.id, original_id)
        self.assertEqual(int(self.env.card_action_slot), 0)


if __name__ == "__main__":
    unittest.main()
