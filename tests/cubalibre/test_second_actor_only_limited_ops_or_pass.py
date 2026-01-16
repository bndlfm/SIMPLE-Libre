import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_OPS, MAIN_EVENT, MAIN_PASS


class TestSecondActorOnlyLimitedOpsOrPass(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_second_actor_main_menu_mask(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.current_player_num = 0
        self.env.players[0].eligible = True

        self.assertEqual(self.env.legal_actions[self.env._main_action_base + MAIN_EVENT], 1)
        self.assertEqual(self.env.legal_actions[self.env._main_action_base + MAIN_OPS], 0)
        self.assertEqual(self.env.legal_actions[self.env._main_action_base + MAIN_PASS], 1)
        self.assertEqual(self.env.legal_actions[self.env._limited_main_action_id], 1)


if __name__ == "__main__":
    unittest.main()
