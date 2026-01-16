import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestFactionOrderTurnPointer(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_update_turn_pointer_respects_card_faction_order(self):
        # Custom order: DR, Govt, Syndicate, M26
        order = [2, 0, 3, 1]
        self.env.current_card = Card(999, "Test Card", order, "u", "s")

        for p in self.env.players:
            p.eligible = True

        self.env._card_order_index = 0
        self.env.card_action_slot = 0
        self.env.update_turn_pointer()
        self.assertEqual(self.env.current_player_num, 2)

        # First actor acts/passes -> becomes ineligible.
        self.env.players[2].eligible = False
        self.env.update_turn_pointer()
        self.assertEqual(self.env.current_player_num, 0)

        # Next actor in order.
        self.env.players[0].eligible = False
        self.env.update_turn_pointer()
        self.assertEqual(self.env.current_player_num, 3)

        # Skip ineligible; should still follow order.
        self.env.players[3].eligible = False
        self.env.update_turn_pointer()
        self.assertEqual(self.env.current_player_num, 1)


if __name__ == "__main__":
    unittest.main()
