import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_EVENT, MAIN_OPS


class TestSecondActorAfterIllegalAction(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_second_actor_fallback_allows_limited_ops(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        for p in self.env.players:
            p.eligible = True

        # Force an illegal action in main phase.
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 0
        self.env.players[0].eligible = True

        illegal_action = self.env._ops_action_base  # Not legal in main phase
        self.env.step(illegal_action)

        self.assertEqual(self.env.card_action_slot, 1)
        self.assertEqual(self.env.card_first_action, "ILLEGAL")

        # Advance to the next eligible actor for slot 1.
        self.env.update_turn_pointer()
        self.env.phase = PHASE_CHOOSE_MAIN

        mask = self.env.legal_actions
        self.assertEqual(mask[self.env._limited_main_action_id], 0)
        self.assertEqual(mask[self.env._main_action_base + MAIN_EVENT], 1)
        self.assertEqual(mask[self.env._main_action_base + MAIN_OPS], 1)


if __name__ == "__main__":
    unittest.main()
