import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_PASS


class TestPassingDoesNotConsumeActionSlot(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_pass_grants_resources_and_does_not_advance_action_slot(self):
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 0

        self.env.step(self.env._main_action_base + MAIN_PASS)

        self.assertEqual(int(self.env.players[0].resources), 3)
        self.assertEqual(int(self.env.card_action_slot), 0)


if __name__ == "__main__":
    unittest.main()
