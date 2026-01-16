import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestExplicitCardActors(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_first_and_second_actor_are_recorded_in_order(self):
        # Order: DR, Govt, Syndicate, M26
        order = [2, 0, 3, 1]
        self.env.current_card = Card(999, "Test Card", order, "u", "s")

        for p in self.env.players:
            p.eligible = True

        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.card_first_actor = None
        self.env.card_second_actor = None

        self.env.update_turn_pointer()
        self.assertEqual(self.env.card_first_actor, 2)
        self.assertEqual(self.env.current_player_num, 2)

        # Simulate completion of first actor
        self.env.players[2].eligible = False
        self.env.card_action_slot = 1
        self.env.update_turn_pointer()
        self.assertEqual(self.env.card_second_actor, 0)
        self.assertEqual(self.env.current_player_num, 0)


if __name__ == "__main__":
    unittest.main()
