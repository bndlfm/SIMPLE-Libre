import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_EVENT, MAIN_OPS, MAIN_PASS


class TestLimitedEventSecondActor(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_second_actor_cannot_choose_event(self):
        # Use a known event card with a deterministic order.
        d = EVENT_DECK_DATA[8]  # General Strike
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        for p in self.env.players:
            p.eligible = True

        # Advance to first actor.
        self.env.factions_acted_this_card = 0
        self.env._card_order_index = 0
        self.env.update_turn_pointer()
        first_actor = self.env.current_player_num

        # Simulate first actor already acted.
        self.env.players[first_actor].eligible = False
        self.env.card_action_slot = 1
        self.env.card_first_action = "EVENT"
        self.env.phase = PHASE_CHOOSE_MAIN

        # Advance to the second actor so masking is computed for the correct current player.
        self.env.update_turn_pointer()

        enter_event = self.env._main_action_base + MAIN_EVENT
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(self.env.legal_actions[enter_event], 0)
        self.assertEqual(self.env.legal_actions[enter_ops], 0)
        self.assertEqual(self.env.legal_actions[self.env._limited_main_action_id], 1)
        self.assertEqual(self.env.legal_actions[self.env._main_action_base + MAIN_PASS], 1)


if __name__ == "__main__":
    unittest.main()
